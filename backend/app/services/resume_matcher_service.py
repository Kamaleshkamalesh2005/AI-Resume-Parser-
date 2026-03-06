"""
Resume Matcher Service - Production ML Model Inference

Loads the trained resume-job match prediction pipeline and provides
a simple interface for match probability prediction.

Pipeline Architecture:
  TF-IDF Vectorizer -> TruncatedSVD (100 components) -> 
  StandardScaler -> SVM Classifier (RBF kernel)

The trained pipeline is loaded once at app startup and cached in memory
for efficient inference requests.

Usage:
    service = ResumeMatcherService()
    probability = service.predict_resume_match(
        skills="Python, Flask, Docker",
        experience="5 years as Backend Developer",
        education="BS Computer Science",
        job_role="Senior Python Developer"
    )
    # Returns: float between 0.0 and 1.0
"""

import logging
from pathlib import Path
from typing import Optional

import joblib

logger = logging.getLogger(__name__)


class ResumeMatcherService:
    """
    Resume-Job Match Prediction Service
    
    Loads and caches the trained ML pipeline for efficient inference.
    Combines candidate features into text format and returns match probability.
    
    Implements singleton pattern - model is loaded once on first instantiation
    and reused for all subsequent calls.
    """

    # Singleton instance (loaded once per app lifetime)
    _instance: Optional["ResumeMatcherService"] = None

    def __new__(cls, models_dir: str = "models"):
        """Implement singleton pattern - load model only once."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._do_init(models_dir)
        return cls._instance

    def _do_init(self, models_dir: str = "models") -> None:
        """
        Initialize the resume matcher service (called only once).
        
        Args:
            models_dir: Directory containing the trained pipeline artifact
        """
        self.models_dir = Path(models_dir)
        self.pipeline = None
        self.is_ready = False
        self.error_message = None

        self._load_pipeline()

    def _load_pipeline(self) -> None:
        """Load the trained ML pipeline from disk."""
        try:
            model_path = self.models_dir / "resume_matcher.pkl"

            if not model_path.exists():
                raise FileNotFoundError(
                    f"Resume matcher model not found: {model_path}\n"
                    f"Run 'python train_model.py' to train the model."
                )

            logger.info(f"Loading resume matcher pipeline from {model_path}...")
            self.pipeline = joblib.load(model_path)

            # Validate pipeline structure
            if not hasattr(self.pipeline, "predict_proba"):
                raise RuntimeError(
                    "Loaded model does not have predict_proba method. "
                    "Ensure it was trained with SVM(probability=True)."
                )

            self.is_ready = True
            logger.info("✓ Resume matcher pipeline loaded successfully")

        except FileNotFoundError as e:
            self.error_message = str(e)
            logger.error(f"✗ {self.error_message}")
            raise
        except Exception as e:
            self.error_message = f"Failed to load model: {str(e)}"
            logger.error(f"✗ {self.error_message}")
            raise RuntimeError(self.error_message) from e

    def predict_resume_match(
        self,
        skills: str,
        experience: str,
        education: str,
        job_role: str,
    ) -> float:
        """
        Predict resume-job match probability.
        
        Combines candidate features (skills, experience, education, job_role)
        into a single text input, vectorizes it through the trained pipeline,
        and returns the probability that it matches the job (class 1).
        
        Args:
            skills: Candidate's technical skills (comma-separated or paragraph)
            experience: Candidate's work experience description
            education: Candidate's education background
            job_role: Target job role or position title
            
        Returns:
            Match probability as float between 0.0 and 1.0
            - 0.0 = poor match (unlikely to succeed in role)
            - 1.0 = excellent match (very likely to succeed)
            
        Raises:
            RuntimeError: If model not ready or prediction fails
            ValueError: If input features are empty or invalid
        """
        if not self.is_ready:
            raise RuntimeError(
                f"Resume matcher service not ready. Error: {self.error_message}"
            )

        # Validate inputs
        if not any([skills, experience, education, job_role]):
            raise ValueError(
                "At least one of (skills, experience, education, job_role) required"
            )

        # Combine features in the same order as training
        # Skills + Work Experience + Education + Job Role
        combined_text = " ".join(
            [
                str(skills).strip(),
                str(experience).strip(),
                str(education).strip(),
                str(job_role).strip(),
            ]
        ).strip()

        # Replace multiple spaces with single space
        combined_text = " ".join(combined_text.split())

        if not combined_text:
            raise ValueError("Combined feature text is empty after processing")

        try:
            # Pipeline handles: TF-IDF -> SVD -> Scaler -> SVM
            # predict_proba returns [[prob_class_0, prob_class_1]]
            probabilities = self.pipeline.predict_proba([combined_text])

            # Return probability of class 1 (good match)
            match_probability = float(probabilities[0][1])

            logger.debug(
                f"Match prediction: {match_probability:.4f} for job_role={job_role}"
            )

            return match_probability

        except Exception as e:
            error_msg = f"Prediction failed: {str(e)}"
            logger.error(f"✗ {error_msg}")
            raise RuntimeError(error_msg) from e
