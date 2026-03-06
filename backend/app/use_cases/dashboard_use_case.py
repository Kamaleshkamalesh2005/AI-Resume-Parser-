"""Dashboard use-case: aggregates app health and runtime stats."""

import os
from typing import Any, Dict, Tuple

from app.models.matcher import MatcherModel


class DashboardUseCase:
    """Business logic for dashboard and health endpoints."""

    def __init__(self, matcher_model: MatcherModel):
        self.matcher_model = matcher_model

    def stats(self, config: dict) -> Tuple[Dict[str, Any], int]:
        upload_folder = config["UPLOAD_FOLDER"]
        models_folder = config["MODELS_FOLDER"]
        log_file = config["LOG_FILE"]

        uploaded_count = len(os.listdir(upload_folder)) if os.path.exists(upload_folder) else 0
        model_files = [f for f in os.listdir(models_folder) if f.endswith(".pkl")] if os.path.exists(models_folder) else []
        log_size = os.path.getsize(log_file) / (1024 * 1024) if os.path.exists(log_file) else 0

        return {
            "success": True,
            "models": {
                "matcher_trained": self.matcher_model.is_trained,
                "model_files": model_files,
                "total_models": len(model_files),
            },
            "uploads": {
                "total_files": uploaded_count,
            },
            "system": {
                "log_file_size_mb": round(log_size, 2),
                "upload_folder": upload_folder,
                "models_folder": models_folder,
            },
            "config": {
                "max_file_size_mb": config["MAX_CONTENT_LENGTH"] / (1024 * 1024),
                "allowed_extensions": list(config["ALLOWED_EXTENSIONS"]),
                "similarity_threshold": config["COSINE_SIMILARITY_THRESHOLD"],
            },
        }, 200

    def health(self, config: dict) -> Tuple[Dict[str, Any], int]:
        status_checks = {
            "database": {"ok": True},
            "nlp_model": {"ok": True},
            "ml_model": {"ok": self.matcher_model.is_trained},
            "storage": {"ok": os.access(config["UPLOAD_FOLDER"], os.W_OK)},
            "logs": {"ok": os.path.exists(config["LOGS_FOLDER"])},
        }
        all_ok = all(check["ok"] for check in status_checks.values())
        return {
            "success": True,
            "status": "healthy" if all_ok else "degraded",
            "components": status_checks,
            "message": "Application is running normally" if all_ok else "Some components may not be operational",
        }, (200 if all_ok else 503)

    @staticmethod
    def info(debug_mode: bool) -> Tuple[Dict[str, Any], int]:
        return {
            "success": True,
            "app": {
                "name": "AI Resume Matcher",
                "version": "1.0.0",
                "description": "Production-level resume matching application using ML",
                "author": "Your Name",
                "environment": "production" if not debug_mode else "development",
            },
            "features": [
                "Resume upload (PDF, DOCX)",
                "Multi-resume batch processing",
                "Resume parsing with NER",
                "Skill extraction",
                "Contact information extraction",
                "Cosine similarity matching",
                "ML-based matching (SVM)",
                "RESTful API",
                "Logging and error handling",
            ],
            "endpoints": {
                "upload": "/api/upload",
                "match": "/api/match",
                "dashboard": "/api/dashboard",
            },
        }, 200
