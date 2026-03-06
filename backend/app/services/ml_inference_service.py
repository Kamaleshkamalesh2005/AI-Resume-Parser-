"""
ML Inference Service - Production Scoring Pipeline

COMPLETE INFERENCE PIPELINE:
1. Load vectorizer (already fitted with training data vocabulary)
2. Transform resume + JD text
3. Apply fitted SVD transformation  
4. Apply fitted scaler normalization
5. Compute cosine similarity between vectors
6. Predict probability using SVM.predict_proba()
7. Compute final_score = 0.7 * similarity + 0.3 * probability
8. Convert to percentage (0-100)

FEATURES:
- Model status checking (verifies all models trained)
- Zero vector prevention (detects empty text)
- Percentage formatting (rounds properly)
- Production-ready error handling
"""

import logging
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# Configuration
MODELS_DIR = Path('models')
SVD_N_COMPONENTS = 100

# Weight factors for final score
SIMILARITY_WEIGHT = 0.7
PROBABILITY_WEIGHT = 0.3


class MLInferenceService:
    """
    Production ML Inference Service
    
    Provides:
    - Model loading and status checking
    - Text vectorization (TF-IDF -> SVD -> Scale)
    - Similarity computation
    - SVM probability prediction
    - Combined scoring
    - Percentage formatting
    """
    
    def __init__(self, models_dir: str = 'models'):
        """Initialize inference service and load models"""
        self.models_dir = Path(models_dir)
        
        # Model storage
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.svd: Optional[TruncatedSVD] = None
        self.scaler: Optional[StandardScaler] = None
        self.svm: Optional[SVC] = None
        
        # Status
        self.is_ready = False
        self.error_message = None
        
        # Load all models
        self._load_models()
    
    def _load_models(self):
        """Load all trained models from disk"""
        try:
            logger.info(f"Loading models from {self.models_dir}...")
            
            # Load TF-IDF Vectorizer
            tfidf_path = self.models_dir / 'tfidf_vectorizer.pkl'
            with open(tfidf_path, 'rb') as f:
                self.vectorizer = pickle.load(f)
            logger.debug(f"Loaded TF-IDF vectorizer: {len(self.vectorizer.vocabulary_)} features")
            
            # Load SVD Transformer
            svd_path = self.models_dir / 'svd_transformer.pkl'
            with open(svd_path, 'rb') as f:
                self.svd = pickle.load(f)
            logger.debug(f"Loaded SVD: {self.svd.components_.shape}")
            
            # Load StandardScaler
            scaler_path = self.models_dir / 'scaler.pkl'
            with open(scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
            logger.debug(f"Loaded Scaler: {self.scaler.mean_.shape}")
            
            # Load SVM Classifier
            svm_path = self.models_dir / 'svm_classifier.pkl'
            with open(svm_path, 'rb') as f:
                self.svm = pickle.load(f)
            logger.debug(f"Loaded SVM: {self.svm.support_vectors_.shape}")
            
            self.is_ready = True
            logger.info("✓ All models loaded successfully")
        
        except FileNotFoundError as e:
            self.error_message = f"Model files not found: {str(e)}"
            self.is_ready = False
            logger.error(self.error_message)
        
        except Exception as e:
            self.error_message = f"Failed to load models: {str(e)}"
            self.is_ready = False
            logger.error(self.error_message, exc_info=True)
    
    def check_model_status(self) -> Dict[str, bool]:
        """
        Check if all models are properly trained and loaded
        
        Returns:
            dict with status of each model component
        """
        status = {
            'vectorizer_ready': (
                self.vectorizer is not None and 
                hasattr(self.vectorizer, 'vocabulary_') and 
                len(self.vectorizer.vocabulary_) > 0
            ),
            'svd_ready': (
                self.svd is not None and 
                hasattr(self.svd, 'components_') and 
                self.svd.components_ is not None
            ),
            'scaler_ready': (
                self.scaler is not None and 
                hasattr(self.scaler, 'mean_') and 
                self.scaler.mean_ is not None
            ),
            'svm_ready': (
                self.svm is not None and 
                hasattr(self.svm, 'support_vectors_') and 
                len(self.svm.support_vectors_) > 0
            ),
            'all_ready': self.is_ready
        }
        
        return status
    
    def get_status_message(self) -> str:
        """Get human-readable model status message"""
        if not self.is_ready:
            return "⚠️  Model Not Trained - Run: python train_ml_pipeline.py"
        
        status = self.check_model_status()
        if all(status.values()):
            return "✓ Model Trained and Ready"
        else:
            missing = [k for k, v in status.items() if not v and k != 'all_ready']
            return f"⚠️  Incomplete: {', '.join(missing)}"
    
    def _vectorize_text(self, text: str) -> Optional[np.ndarray]:
        """
        Transform text to scaled SVD-reduced vector
        
        Pipeline:
        1. TF-IDF vectorization
        2. SVD dimensionality reduction
        3. StandardScaler normalization
        
        Args:
            text: Input text
        
        Returns:
            Scaled vector (100 dims) or None if fails
        """
        if not self.is_ready:
            logger.warning("Models not ready for vectorization")
            return None
        
        if not text or not isinstance(text, str) or len(text.strip()) == 0:
            logger.warning("Empty or invalid text for vectorization")
            return None
        
        try:
            # Step 1: TF-IDF vectorization
            tfidf_vec = self.vectorizer.transform([text])
            
            # Step 2: Check for zero vector
            if tfidf_vec.nnz == 0:  # nnz = number of non-zero elements
                logger.warning("Text produced zero TF-IDF vector")
                return None
            
            # Step 3: SVD transformation
            svd_vec = self.svd.transform(tfidf_vec)
            
            # Step 4: StandardScaler normalization
            scaled_vec = self.scaler.transform(svd_vec)
            
            # Return 1D array
            return scaled_vec[0]
        
        except Exception as e:
            logger.error(f"Vectorization failed: {str(e)}")
            return None
    
    def compute_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors
        
        Args:
            vec1: First vector
            vec2: Second vector
        
        Returns:
            Similarity score (0-1)
        """
        if vec1 is None or vec2 is None:
            return 0.0
        
        try:
            # Reshape for cosine_similarity
            v1 = vec1.reshape(1, -1) if vec1.ndim == 1 else vec1
            v2 = vec2.reshape(1, -1) if vec2.ndim == 1 else vec2
            
            # Compute similarity
            sim = cosine_similarity(v1, v2)[0][0]
            
            # Normalize to [0, 1] (cosine is in [-1, 1] but usually positive)
            return float(max(0.0, min(1.0, sim)))
        
        except Exception as e:
            logger.error(f"Similarity computation failed: {str(e)}")
            return 0.0
    
    def compute_svm_probability(self, vec: np.ndarray) -> float:
        """
        Get SVM probability estimate for positive class
        
        Args:
            vec: Input feature vector
        
        Returns:
            Probability (0-1)
        """
        if vec is None or not self.is_ready:
            return 0.0
        
        try:
            # Reshape if needed
            if vec.ndim == 1:
                vec = vec.reshape(1, -1)
            
            # Get probability for positive class (1)
            proba = self.svm.predict_proba(vec)
            
            # proba shape: (n_samples, n_classes)
            # We want probability of class 1 (match)
            prob = float(proba[0][1])  # Index 1 = positive class
            
            return max(0.0, min(1.0, prob))
        
        except Exception as e:
            logger.error(f"SVM probability computation failed: {str(e)}")
            return 0.0
    
    def compute_final_score(
        self, 
        resume_text: str, 
        job_text: str
    ) -> Tuple[Dict[str, float], Optional[str]]:
        """
        Complete scoring pipeline: compute similarity and probability, combine them
        
        FORMULA:
        final_score = 0.7 * cosine_similarity + 0.3 * svm_probability
        
        Args:
            resume_text: Resume content
            job_text: Job description content
        
        Returns:
            (scores dict, error message)
            scores = {
                'similarity': float (0-1),
                'probability': float (0-1),
                'final_score': float (0-1),
                'percentage': int (0-100)
            }
        """
        if not self.is_ready:
            return {}, "Model Not Trained"
        
        # Validate inputs
        if not resume_text or not job_text:
            return {}, "Resume and job description required"
        
        # Vectorize texts
        resume_vec = self._vectorize_text(resume_text)
        job_vec = self._vectorize_text(job_text)
        
        # Check for zero vectors
        if resume_vec is None:
            return {}, "Resume text too short or contains no valid words"
        if job_vec is None:
            return {}, "Job description text too short or contains no valid words"
        
        # Step 1: Compute cosine similarity
        similarity = self.compute_similarity(resume_vec, job_vec)
        
        # Step 2: Compute SVM probability
        probability = self.compute_svm_probability(resume_vec)
        
        # Step 3: Combine scores
        final_score = (
            SIMILARITY_WEIGHT * similarity + 
            PROBABILITY_WEIGHT * probability
        )
        
        # Step 4: Convert to percentage
        percentage = self._to_percentage(final_score)
        
        result = {
            'similarity': float(similarity),
            'probability': float(probability),
            'final_score': float(final_score),
            'percentage': percentage
        }
        
        logger.debug(
            f"Score computed: similarity={similarity:.4f}, "
            f"probability={probability:.4f}, final={final_score:.4f}, "
            f"percentage={percentage}%"
        )
        
        return result, None
    
    def batch_score(
        self, 
        resume_text: str, 
        job_descriptions: list
    ) -> Tuple[list, Optional[str]]:
        """
        Score one resume against multiple job descriptions
        
        Args:
            resume_text: Resume content
            job_descriptions: List of job description texts
        
        Returns:
            (results list, error message)
            results = [
                {
                    'job_text': str (first 100 chars),
                    'similarity': float,
                    'probability': float,
                    'final_score': float,
                    'percentage': int
                },
                ...
            ]
        """
        if not self.is_ready:
            return [], "Model Not Trained"
        
        if not isinstance(job_descriptions, list) or len(job_descriptions) == 0:
            return [], "Job descriptions list required"
        
        results = []
        
        # Vectorize resume once
        resume_vec = self._vectorize_text(resume_text)
        if resume_vec is None:
            return [], "Resume vectorization failed"
        
        # Score against each job
        for job_text in job_descriptions:
            job_vec = self._vectorize_text(job_text)
            
            if job_vec is None:
                continue  # Skip invalid job descriptions
            
            # Compute scores
            similarity = self.compute_similarity(resume_vec, job_vec)
            probability = self.compute_svm_probability(resume_vec)
            final_score = (
                SIMILARITY_WEIGHT * similarity + 
                PROBABILITY_WEIGHT * probability
            )
            percentage = self._to_percentage(final_score)
            
            results.append({
                'job_text': job_text[:100] + '...' if len(job_text) > 100 else job_text,
                'similarity': float(similarity),
                'probability': float(probability),
                'final_score': float(final_score),
                'percentage': percentage
            })
        
        return results, None
    
    @staticmethod
    def _to_percentage(score: float) -> int:
        """
        Convert decimal score (0-1) to percentage (0-100)
        
        Args:
            score: Float between 0 and 1
        
        Returns:
            Integer percentage (0-100) with proper rounding
        """
        if not isinstance(score, (int, float)):
            return 0
        
        # Clamp to [0, 1]
        clamped = max(0.0, min(1.0, score))
        
        # Convert to percentage with proper rounding
        percentage = round(clamped * 100)
        
        # Final clamp (handles rounding edge cases)
        return max(0, min(100, percentage))
    
    @staticmethod
    def percentage_to_icon(percentage: int) -> str:
        """
        Get visual indicator for percentage score
        
        Args:
            percentage: Score 0-100
        
        Returns:
            Emoji/badge string
        """
        if percentage >= 85:
            return "🟢 Excellent"
        elif percentage >= 70:
            return "🟡 Good"
        elif percentage >= 50:
            return "🟠 Fair"
        else:
            return "🔴 Poor"


# ============================================================================
# UTILITY FUNCTION
# ============================================================================

def create_inference_service(models_dir: str = 'models') -> MLInferenceService:
    """
    Factory function to create and initialize inference service
    
    Args:
        models_dir: Path to models directory
    
    Returns:
        MLInferenceService instance
    """
    return MLInferenceService(models_dir)
