"""
API Blueprint – all JSON REST endpoints under ``/api``.

Sub-routes:
    /api/upload/resume          POST   single resume upload
    /api/upload/batch           POST   batch resume upload
    /api/upload/validate        POST   file validation only
    /api/upload/job-description POST   job description upload
    /api/match/similarity       POST   resume ↔ job similarity
    /api/match/batch            POST   one resume vs N jobs
    /api/match/predict          POST   ML prediction
    /api/match/model-info       GET    model status
    /api/dashboard/stats        GET    system statistics
    /api/dashboard/health       GET    health check
    /api/dashboard/info         GET    application info
"""

from __future__ import annotations

import logging
import os
from typing import Any

from flask import Blueprint, current_app, jsonify, request
from werkzeug.datastructures import FileStorage

from app.services.file_service import FileParseError, FileService
from app.services.ml_service import MLService

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__)


# ── helpers ──────────────────────────────────────────────────────────
def _ml() -> MLService | None:
    """Return the ML service attached to the current app (may be ``None``)."""
    return getattr(current_app, "ml_service", None)


def _json_response(payload: dict[str, Any], status: int = 200):
    return jsonify(payload), status


def _validate_file(f: FileStorage) -> tuple[bool, str | None]:
    """Validate an uploaded file using FileService.validate."""
    if not f or not f.filename:
        return False, "No file selected"
    try:
        FileService.validate(f)
    except FileParseError as exc:
        return False, str(exc)
    return True, None


# =====================================================================
# UPLOAD endpoints
# =====================================================================
@api_bp.route("/upload/resume", methods=["POST"])
def upload_resume():
    """Upload and parse a single resume using Universal Parser."""
    if "file" not in request.files:
        return _json_response({"success": False, "error": "No file provided"}, 400)

    f = request.files["file"]
    ok, err = _validate_file(f)
    if not ok:
        return _json_response({"success": False, "error": err}, 400)

    try:
        from app.services.universal_parser_service import get_parser_service

        saved_path = FileService.save_upload(f, current_app.config["UPLOAD_FOLDER"])
        parser_service = get_parser_service()
        result = parser_service.parse_file(saved_path)

        success = bool(result.get("success"))
        return _json_response(
            {
                "success": success,
                "data": result.get("data"),
                "error": result.get("error"),
                "message": "Resume parsed successfully" if success else "Parsing failed",
            },
            200 if success else 400,
        )

    except Exception as exc:
        logger.error("Resume upload error: %s", exc, exc_info=True)
        return _json_response(
            {"success": False, "error": "Server error", "message": str(exc)},
            500,
        )


@api_bp.route("/upload/batch", methods=["POST"])
def upload_batch():
    """Upload and parse multiple resumes using Universal Parser."""
    from app.services.universal_parser_service import get_parser_service

    files: list[FileStorage] = request.files.getlist("files")
    if not files:
        return _json_response({"success": False, "error": "No files provided"}, 400)

    results: list[dict[str, Any]] = []
    failed: list[dict[str, str]] = []
    parser_service = get_parser_service()

    for f in files:
        ok, err = _validate_file(f)
        if not ok:
            failed.append({"filename": f.filename or "unknown", "error": err or "invalid"})
            continue

        try:
            saved_path = FileService.save_upload(f, current_app.config["UPLOAD_FOLDER"])
            parsed = parser_service.parse_file(saved_path)

            if parsed.get("success"):
                data = parsed.get("data")
                if data is not None:
                    results.append(data)
            else:
                failed.append(
                    {
                        "filename": f.filename or "unknown",
                        "error": parsed.get("error", "parse error"),
                    }
                )
        except Exception as exc:
            logger.error("Batch processing failed for %s: %s", f.filename, exc, exc_info=True)
            failed.append({"filename": f.filename or "unknown", "error": str(exc)})

    return _json_response(
        {
            "success": len(results) > 0,
            "data": results,
            "failed": failed,
            "summary": {
                "total": len(files),
                "successful": len(results),
                "failed": len(failed),
            },
        }
    )


@api_bp.route("/upload/validate", methods=["POST"])
def validate_upload():
    """Validate a file without processing it."""
    if "file" not in request.files:
        return _json_response({"success": False, "error": "No file provided"}, 400)

    ok, err = _validate_file(request.files["file"])
    return _json_response({"success": ok, "error": err})


@api_bp.route("/upload/job-description", methods=["POST"])
def upload_job_description():
    """Save job description from text input or uploaded file."""
    from app.services.universal_parser_service import get_parser_service

    try:
        text = (request.form.get("text") or "").strip()
        file_obj = request.files.get("file")

        # Extract text from file if provided
        if file_obj:
            ok, err = _validate_file(file_obj)
            if not ok:
                return _json_response({"success": False, "error": err}, 400)

            try:
                from app.core import UniversalResumeParser

                saved_path = FileService.save_upload(file_obj, current_app.config["UPLOAD_FOLDER"])
                parser = UniversalResumeParser()
                raw_text = parser.text_extractor.extract(saved_path)
                text = parser.text_extractor.clean_text(raw_text)
            except Exception as exc:
                return _json_response(
                    {"success": False, "error": f"File extraction failed: {exc}"},
                    400,
                )

        # Validate text
        if not text or len(text) < 50:
            return _json_response(
                {"success": False, "error": "Job description too short (minimum 50 characters)"},
                400,
            )

        # Parse job description using skill extraction
        parser_service = get_parser_service()
        skills = parser_service.parser.skill_extractor.extract_skills(text)

        return _json_response(
            {
                "success": True,
                "data": {
                    "text": text[:1000],  # Store first 1000 chars
                    "skills_detected": skills,
                    "text_length": len(text),
                },
                "message": "Job description processed",
            }
        )

    except Exception as exc:
        logger.error("Job description upload error: %s", exc, exc_info=True)
        return _json_response(
            {"success": False, "error": "Server error", "message": str(exc)},
            500,
        )


# =====================================================================
# MATCH endpoints
# =====================================================================
@api_bp.route("/match/similarity", methods=["POST"])
def match_similarity():
    """Compute similarity between resume text and job description."""
    data = request.get_json(silent=True)
    if not data:
        return _json_response({"success": False, "error": "JSON body required"}, 400)

    resume_text = (data.get("resume_text") or "").strip()
    job_desc = (data.get("job_description") or "").strip()

    if not resume_text:
        return _json_response({"success": False, "error": "resume_text is required"}, 400)
    if not job_desc:
        return _json_response({"success": False, "error": "job_description is required"}, 400)
    if len(resume_text) < 50:
        return _json_response({"success": False, "error": "resume_text too short (min 50 chars)"}, 400)
    if len(job_desc) < 50:
        return _json_response({"success": False, "error": "job_description too short (min 50 chars)"}, 400)

    ml = _ml()
    if ml is None or not ml.is_ready:
        return _json_response({"success": False, "error": "ML models not available"}, 503)

    result = ml.score(resume_text, job_desc)
    threshold = current_app.config.get("SIMILARITY_THRESHOLD", 0.3) * 100
    return _json_response(
        {
            "success": True,
            **result.to_dict(),
            "is_match": result.score >= threshold,
            "threshold": threshold,
        }
    )


@api_bp.route("/match/batch", methods=["POST"])
def match_batch():
    """Match one resume against multiple job descriptions."""
    data = request.get_json(silent=True)
    if not data:
        return _json_response({"success": False, "error": "JSON body required"}, 400)

    resume_text = (data.get("resume_text") or "").strip()
    job_descriptions = data.get("job_descriptions", [])

    if not resume_text:
        return _json_response({"success": False, "error": "resume_text is required"}, 400)
    if not isinstance(job_descriptions, list) or not job_descriptions:
        return _json_response({"success": False, "error": "job_descriptions list required"}, 400)

    ml = _ml()
    if ml is None or not ml.is_ready:
        return _json_response({"success": False, "error": "ML models not available"}, 503)

    results = ml.batch_score(resume_text, job_descriptions)
    threshold = current_app.config.get("SIMILARITY_THRESHOLD", 0.3) * 100

    matches: list[dict[str, Any]] = []
    for r in results:
        d = r.to_dict()
        d["is_match"] = r.score >= threshold
        matches.append(d)

    matches.sort(key=lambda m: m["score"], reverse=True)
    return _json_response(
        {
            "success": True,
            "matches": matches,
            "total_jobs": len(job_descriptions),
            "matched_count": sum(1 for m in matches if m["is_match"]),
        }
    )


@api_bp.route("/match/predict", methods=["POST"])
def match_predict():
    """Predict match (alias for similarity)."""
    return match_similarity()


@api_bp.route("/match/model-info", methods=["GET"])
def model_info():
    """Return model readiness info."""
    ml = _ml()
    if ml is None:
        return _json_response({"success": True, "model": {"status": "not loaded"}})

    return _json_response(
        {
            "success": True,
            "model": {
                "type": "TF-IDF + SBERT dual-vectorisation pipeline",
                "status": ml.status_message(),
                "components": ml.check_status(),
            },
        }
    )


# =====================================================================
# DASHBOARD endpoints
# =====================================================================
@api_bp.route("/dashboard/stats", methods=["GET"])
def dashboard_stats():
    """Return system statistics."""
    cfg = current_app.config
    upload_dir = cfg["UPLOAD_FOLDER"]
    models_dir = cfg["MODELS_FOLDER"]
    log_file = cfg.get("LOG_FILE", "")

    uploaded = len(os.listdir(upload_dir)) if os.path.isdir(upload_dir) else 0
    model_files = (
        [f for f in os.listdir(models_dir) if f.endswith(".pkl")] if os.path.isdir(models_dir) else []
    )
    log_mb = round(os.path.getsize(log_file) / (1024 * 1024), 2) if os.path.isfile(log_file) else 0

    ml = _ml()
    return _json_response(
        {
            "success": True,
            "models": {
                "ml_ready": ml.is_ready if ml else False,
                "model_files": model_files,
                "total_models": len(model_files),
            },
            "uploads": {"total_files": uploaded},
            "system": {"log_file_size_mb": log_mb},
            "config": {
                "max_file_size_mb": cfg["MAX_CONTENT_LENGTH"] / (1024 * 1024),
                "allowed_extensions": sorted(cfg["ALLOWED_EXTENSIONS"]),
                "similarity_threshold": cfg.get("SIMILARITY_THRESHOLD", 0.3),
            },
        }
    )


@api_bp.route("/dashboard/health", methods=["GET"])
def dashboard_health():
    """Health-check endpoint."""
    cfg = current_app.config
    ml = _ml()
    checks = {
        "ml_model": {"ok": bool(ml and ml.is_ready)},
        "storage": {"ok": os.access(cfg["UPLOAD_FOLDER"], os.W_OK)},
        "logs": {"ok": os.path.isdir(cfg["LOGS_FOLDER"])},
    }
    all_ok = all(c["ok"] for c in checks.values())
    return _json_response(
        {
            "success": True,
            "status": "healthy" if all_ok else "degraded",
            "components": checks,
        },
        200 if all_ok else 503,
    )


@api_bp.route("/dashboard/info", methods=["GET"])
def dashboard_info():
    """Application metadata."""
    return _json_response(
        {
            "success": True,
            "app": {
                "name": "AI Resume Matcher",
                "version": "2.0.0",
                "environment": "development" if current_app.debug else "production",
            },
            "features": [
                "Resume upload (PDF, DOCX, TXT)",
                "Batch processing",
                "NLP entity extraction (spaCy)",
                "Skill extraction",
                "TF-IDF + SBERT dual-vectorisation matching",
                "RESTful API with JSON responses",
            ],
            "endpoints": {
                "upload": "/api/upload",
                "match": "/api/match",
                "dashboard": "/api/dashboard",
            },
        }
    )
