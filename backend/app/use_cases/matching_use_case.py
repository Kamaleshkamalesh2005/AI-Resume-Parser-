"""Matching use-case: orchestrates similarity and model prediction business rules."""

from typing import Any, Dict, List, Tuple

from app.services.ml_inference_service import MLInferenceService
from app.utils.validators import validate_text_length


class MatchingUseCase:
    """Business logic for matching operations."""

    def __init__(self, similarity_threshold: float = 0.5):
        self.ml_service = MLInferenceService()
        self.similarity_threshold = similarity_threshold

    @staticmethod
    def _require_text(field_name: str, value: str) -> str | None:
        if not value or not value.strip():
            return f"{field_name} is required"
        return None

    def calculate_similarity(
        self, 
        resume_text: str, 
        job_description: str
    ) -> Tuple[Dict[str, Any], int]:
        """Calculate similarity between resume and job description"""
        resume_error = self._require_text("Resume text", resume_text)
        if resume_error:
            return {"success": False, "error": resume_error}, 400

        job_error = self._require_text("Job description", job_description)
        if job_error:
            return {"success": False, "error": job_error}, 400

        is_valid, error = validate_text_length(resume_text, min_length=50)
        if not is_valid:
            return {"success": False, "error": error}, 400

        is_valid, error = validate_text_length(job_description, min_length=50)
        if not is_valid:
            return {"success": False, "error": error}, 400

        # Check model status
        if not self.ml_service.is_ready:
            return {
                "success": False,
                "error": self.ml_service.get_status_message()
            }, 503

        # Compute scores
        scores, error = self.ml_service.compute_final_score(
            resume_text.strip(),
            job_description.strip()
        )
        
        if error:
            return {"success": False, "error": error}, 400

        return {
            "success": True,
            "similarity_score": scores['similarity'],
            "ml_probability": scores['probability'],
            "final_score": scores['final_score'],
            "percentage": scores['percentage'],
            "is_match": scores['percentage'] >= (self.similarity_threshold * 100),
            "threshold": self.similarity_threshold * 100,
        }, 200

    def batch_similarity(
        self, 
        resume_text: str, 
        job_descriptions: List[str]
    ) -> Tuple[Dict[str, Any], int]:
        """Match resume against multiple job descriptions"""
        resume_error = self._require_text("Resume text", resume_text)
        if resume_error:
            return {"success": False, "error": resume_error}, 400

        if not isinstance(job_descriptions, list) or not job_descriptions:
            return {"success": False, "error": "Job descriptions list required"}, 400

        # Check model status
        if not self.ml_service.is_ready:
            return {
                "success": False,
                "error": self.ml_service.get_status_message()
            }, 503

        # Batch score
        results, error = self.ml_service.batch_score(
            resume_text.strip(),
            job_descriptions
        )
        
        if error:
            return {"success": False, "error": error}, 400

        # Sort by final score descending
        results.sort(key=lambda x: x['final_score'], reverse=True)

        matches = []
        for result in results:
            match = {
                "job_description": result['job_text'],
                "similarity_score": result['similarity'],
                "ml_probability": result['probability'],
                "final_score": result['final_score'],
                "percentage": result['percentage'],
                "is_match": result['percentage'] >= (self.similarity_threshold * 100),
            }
            matches.append(match)

        return {
            "success": True,
            "matches": matches,
            "total_jobs": len(job_descriptions),
            "matched_count": sum(1 for m in matches if m["is_match"]),
        }, 200

    def predict(self, features: Any) -> Tuple[Dict[str, Any], int]:
        """Predict match using features (legacy endpoint)"""
        if not features:
            return {"success": False, "error": "Features required"}, 400

        # Check model status
        if not self.ml_service.is_ready:
            return {
                "success": False,
                "model_status": self.ml_service.get_status_message()
            }, 503

        return {
            "success": True,
            "prediction": {
                "match": False,
                "probability": 0.0
            },
            "model_status": self.ml_service.get_status_message()
        }, 200

    def model_info(self, config: dict) -> Tuple[Dict[str, Any], int]:
        """Get model information"""
        status = self.ml_service.check_model_status()
        
        return {
            "success": True,
            "model": {
                "type": "ML Inference Pipeline",
                "status": self.ml_service.get_status_message(),
                "components": status,
                "weights": {
                    "similarity": 0.7,
                    "probability": 0.3
                }
            },
            "similarity_threshold": config.get("COSINE_SIMILARITY_THRESHOLD", 0.5),
        }, 200

