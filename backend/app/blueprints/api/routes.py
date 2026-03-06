"""
API v1 routes – ``/api/v1/…``

Endpoints
---------
POST   /api/v1/match          Match a resume against a job description.
POST   /api/v1/match/batch    Rank multiple resumes against one JD (paginated).
GET    /api/v1/health         Health check with service status.
POST   /api/v1/extract        Extract text from PDF/DOCX file upload.
POST   /api/v1/parse          Parse a resume and return a ResumeProfile.
GET    /api/v1/skills         Return the full skills taxonomy.
POST   /api/v1/feedback       Accept a user score correction for future retraining.

Cross-cutting:
    - Rate limiting: 10 req/min per IP (Flask-Limiter).
    - Input validation: Marshmallow schemas.
    - Standardised response envelope:
        ``{"success": bool, "data": …, "errors": [], "meta": {"latency_ms": …}}``
    - OpenAPI docs via flask-smorest (Swagger UI at ``/api/v1/docs``).
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import hashlib
import json
import requests
from flask import current_app, request
from flask.views import MethodView
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_smorest import Blueprint

from app.blueprints.api.schemas import (
    BatchMatchRequestSchema,
    FeedbackRequestSchema,
    MatchRequestSchema,
    ParseRequestSchema,
    ScrapeRequestSchema,
)
from app.services.file_service import FileService, FileParseError
from app.services.ml_service import MLService
from app.services.nlp_service import NLPService
from app.utils.skills_dict import SKILLS_DICT

# Prometheus metrics (optional – NoOp if not available)
try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

    REQUEST_LATENCY = Histogram(
        "match_request_latency_ms",
        "Match endpoint latency in milliseconds",
        buckets=[50, 100, 200, 300, 500, 1000, 2000, 5000],
    )
    MATCH_SCORE = Histogram(
        "match_score",
        "Distribution of match scores",
        buckets=[10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
    )
    CACHE_HITS = Counter("nlp_cache_hits_total", "NLP cache hits")
    CACHE_MISSES = Counter("nlp_cache_misses_total", "NLP cache misses")
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False

logger = logging.getLogger(__name__)

# ── Blueprint (flask-smorest) ────────────────────────────────────────
blp = Blueprint(
    "api_v1",
    __name__,
    url_prefix="/api/v1",
    description="Resume-matching API v1",
)

# ── Rate limiter (initialised per-app in init_app) ───────────────────
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["10/minute"],
)

# ── Singletons ───────────────────────────────────────────────────────
_nlp = NLPService()

# ── Feedback store path ──────────────────────────────────────────────
_FEEDBACK_DIR = Path("feedback")


def _ml() -> MLService | None:
    return getattr(current_app, "ml_service", None)


# ── Match-history persistence (best-effort) ──────────────────────────

def _save_match_history(resume_text: str, jd_text: str, result) -> None:
    """Persist a MatchResult to the database (non-blocking, best-effort)."""
    try:
        from app.extensions import db
        from app.models.db_models import MatchHistory

        record = MatchHistory(
            resume_hash=hashlib.sha256(resume_text.encode()).hexdigest(),
            jd_hash=hashlib.sha256(jd_text.encode()).hexdigest(),
            score=result.score,
            grade=result.grade,
            matched_skills=json.dumps(result.matched_skills),
            missing_skills=json.dumps(result.missing_skills),
            subscores=json.dumps(result.subscores),
            explanation=result.explanation,
        )
        db.session.add(record)
        db.session.commit()
    except Exception as exc:
        logger.debug("Match history save skipped: %s", exc)


# ── Response helpers ─────────────────────────────────────────────────

def _envelope(
    data: Any = None,
    *,
    errors: List[str] | None = None,
    latency_ms: float = 0.0,
    success: bool = True,
    status: int = 200,
):
    """Return the standard response envelope."""
    body = {
        "success": success,
        "data": data,
        "errors": errors or [],
        "meta": {"latency_ms": round(latency_ms, 2)},
    }
    return body, status


# =====================================================================
# POST /api/v1/match
# =====================================================================

@blp.route("/match")
class MatchResource(MethodView):
    decorators = [limiter.limit("10/minute")]

    @blp.arguments(MatchRequestSchema, location="json")
    @blp.response(200)
    def post(self, payload: dict):
        """Match a resume against a job description."""
        t0 = time.perf_counter()

        ml = _ml()
        if ml is None or not ml.is_ready:
            return _envelope(errors=["ML service unavailable"], success=False, status=503)

        result = ml.score(payload["resume_text"], payload["job_description"])
        dt = (time.perf_counter() - t0) * 1000

        # Record Prometheus metrics
        if _HAS_PROMETHEUS:
            REQUEST_LATENCY.observe(dt)
            MATCH_SCORE.observe(result.score)

        # Persist to match history (best-effort)
        _save_match_history(payload["resume_text"], payload["job_description"], result)

        return _envelope(data=result.to_dict(), latency_ms=dt)


# =====================================================================
# POST /api/v1/match/batch
# =====================================================================

@blp.route("/match/batch")
class BatchMatchResource(MethodView):
    decorators = [limiter.limit("10/minute")]

    @blp.arguments(BatchMatchRequestSchema, location="json")
    @blp.response(200)
    def post(self, payload: dict):
        """Rank multiple resumes against one job description.

        When the number of resumes exceeds ``CELERY_BATCH_THRESHOLD``
        (default 5), the work is dispatched to a Celery worker and a
        ``job_id`` is returned immediately for polling.
        """
        t0 = time.perf_counter()

        ml = _ml()
        if ml is None or not ml.is_ready:
            return _envelope(errors=["ML service unavailable"], success=False, status=503)

        job_desc: str = payload["job_description"]
        resumes: List[str] = payload["resume_texts"]
        filenames: List[str] = payload.get("resume_filenames") or []
        threshold = current_app.config.get("CELERY_BATCH_THRESHOLD", 5)

        # ── Async path (Celery) ──────────────────────────────────
        if len(resumes) > threshold:
            try:
                from app.tasks import batch_match_task

                task = batch_match_task.delay(resumes, job_desc, filenames)
                return _envelope(
                    data={"job_id": task.id, "async": True, "total": len(resumes)},
                    latency_ms=(time.perf_counter() - t0) * 1000,
                    status=202,
                )
            except Exception as exc:
                logger.warning("Celery dispatch failed (%s) – falling back to sync", exc)

        # ── Sync path ────────────────────────────────────────────
        all_results = []
        for idx, resume in enumerate(resumes, start=1):
            # Use provided filename or generate candidate name
            if filenames and idx <= len(filenames):
                candidate_name = filenames[idx - 1]
            else:
                candidate_name = f"Candidate {idx}"
            
            result = ml.score(resume, job_desc, candidate_name=candidate_name)
            all_results.append(result.to_dict())
        
        all_results.sort(key=lambda r: r["score"], reverse=True)
        
        # Add rank numbers after sorting
        for rank, row in enumerate(all_results, start=1):
            row["rank"] = rank

        # Pagination
        page: int = payload.get("page", 1)
        per_page: int = payload.get("per_page", 20)
        total = len(all_results)
        start = (page - 1) * per_page
        end = start + per_page
        page_items = all_results[start:end]

        dt = (time.perf_counter() - t0) * 1000
        if _HAS_PROMETHEUS:
            REQUEST_LATENCY.observe(dt)

        return _envelope(
            data={
                "results": page_items,
                "page": page,
                "per_page": per_page,
                "total": total,
            },
            latency_ms=dt,
        )


# =====================================================================
# GET /api/v1/health
# =====================================================================

@blp.route("/health")
class HealthResource(MethodView):

    @blp.response(200)
    def get(self):
        """Health check with service status."""
        t0 = time.perf_counter()
        ml = _ml()
        cfg = current_app.config
        checks = {
            "nlp_model": {"ok": NLPService._nlp is not None},
            "ml_service": {"ok": ml.is_ready if ml else False},
            "storage": {"ok": os.access(cfg.get("UPLOAD_FOLDER", "uploads"), os.W_OK)},
        }
        all_ok = all(c["ok"] for c in checks.values())
        dt = (time.perf_counter() - t0) * 1000
        return _envelope(
            data={"status": "healthy" if all_ok else "degraded", **checks},
            latency_ms=dt,
            status=200 if all_ok else 503,
        )


# =====================================================================
# POST /api/v1/extract
# =====================================================================

@blp.route("/extract")
class ExtractResource(MethodView):
    decorators = [limiter.limit("200/minute")]

    def post(self):
        """Extract text from an uploaded PDF or DOCX file (optimized for batch).
        
        Returns the extracted text that can be used for parsing/matching.
        For batch operations, sections are skipped to improve performance.
        """
        t0 = time.perf_counter()
        
        # Check if file is in request
        if 'file' not in request.files:
            return _envelope(
                success=False,
                errors=["No file provided"],
                data=None,
                latency_ms=(time.perf_counter() - t0) * 1000,
                status=400
            )
        
        file = request.files['file']
        
        if file.filename == '':
            return _envelope(
                success=False,
                errors=["No file selected"],
                data=None,
                latency_ms=(time.perf_counter() - t0) * 1000,
                status=400
            )
        
        # Check file extension
        allowed_extensions = {'pdf', 'docx', 'doc', 'txt'}
        if '.' not in file.filename:
            return _envelope(
                success=False,
                errors=["No file extension"],
                data=None,
                latency_ms=(time.perf_counter() - t0) * 1000,
                status=400
            )
        
        ext = file.filename.rsplit('.', 1)[1].lower()
        if ext not in allowed_extensions:
            return _envelope(
                success=False,
                errors=[f"Unsupported file type: .{ext}. Allowed: {', '.join(allowed_extensions)}"],
                data=None,
                latency_ms=(time.perf_counter() - t0) * 1000,
                status=400
            )
        
        # Check file size (5 MB max)
        max_size = 5 * 1024 * 1024
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Seek back to start
        
        if file_size > max_size:
            return _envelope(
                success=False,
                errors=["File too large (max 5 MB)"],
                data=None,
                latency_ms=(time.perf_counter() - t0) * 1000,
                status=400
            )
        
        try:
            import tempfile
            # Save file to temp location
            with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as tmp:
                file.save(tmp.name)
                tmp_path = tmp.name
            
            # Extract text (fast path - skip section detection)
            try:
                # For text files, just read directly
                if ext == 'txt':
                    with open(tmp_path, 'r', encoding='utf-8', errors='ignore') as f:
                        text = f.read()
                    
                    return _envelope(
                        data={
                            "text": text,
                            "file_type": "txt",
                            "page_count": 1,
                        },
                        latency_ms=(time.perf_counter() - t0) * 1000,
                        status=200
                    )
                else:
                    # For PDF/DOCX, use FileService
                    resume_doc = FileService.extract_fast(tmp_path)
                    
                    return _envelope(
                        data={
                            "text": resume_doc.raw_text,
                            "file_type": resume_doc.file_type,
                            "page_count": resume_doc.page_count,
                        },
                        latency_ms=(time.perf_counter() - t0) * 1000,
                        status=200
                    )
            finally:
                # Clean up temp file
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        
        except FileParseError as e:
            return _envelope(
                success=False,
                errors=[f"Failed to extract text: {str(e)}"],
                data=None,
                latency_ms=(time.perf_counter() - t0) * 1000,
                status=400
            )
        except Exception as e:
            logger.error(f"File extraction error: {e}", exc_info=True)
            return _envelope(
                success=False,
                errors=[f"Error processing file: {str(e)}"],
                data=None,
                latency_ms=(time.perf_counter() - t0) * 1000,
                status=500
            )


# =====================================================================
# POST /api/v1/parse
# =====================================================================

@blp.route("/parse")
class ParseResource(MethodView):
    decorators = [limiter.limit("10/minute")]

    @blp.arguments(ParseRequestSchema, location="json")
    @blp.response(200)
    def post(self, payload: dict):
        """Parse a resume and return a structured ResumeProfile."""
        t0 = time.perf_counter()
        profile = _nlp.analyse(payload["resume_text"])
        dt = (time.perf_counter() - t0) * 1000
        return _envelope(data=profile.to_dict(), latency_ms=dt)


# =====================================================================
# GET /api/v1/skills
# =====================================================================

@blp.route("/skills")
class SkillsResource(MethodView):

    @blp.response(200)
    def get(self):
        """Return the full skills taxonomy as JSON."""
        t0 = time.perf_counter()
        categories: Dict[str, List[str]] = {}
        for skill_name, tokens in SKILLS_DICT.items():
            categories[skill_name] = tokens
        dt = (time.perf_counter() - t0) * 1000
        return _envelope(
            data={"skills": categories, "total": len(categories)},
            latency_ms=dt,
        )


# =====================================================================
# POST /api/v1/feedback
# =====================================================================

@blp.route("/feedback")
class FeedbackResource(MethodView):
    decorators = [limiter.limit("10/minute")]

    @blp.arguments(FeedbackRequestSchema, location="json")
    @blp.response(201)
    def post(self, payload: dict):
        """Accept a user score correction for ML retraining."""
        t0 = time.perf_counter()
        _FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)

        entry = {
            "resume_text": payload["resume_text"],
            "job_description": payload["job_description"],
            "corrected_score": payload["corrected_score"],
            "comment": payload.get("comment", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ip": request.remote_addr,
        }

        fname = f"fb_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}.json"
        filepath = _FEEDBACK_DIR / fname
        filepath.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")

        dt = (time.perf_counter() - t0) * 1000
        logger.info("Feedback saved: %s (score=%s)", fname, payload["corrected_score"])
        return _envelope(
            data={"id": fname, "message": "Feedback recorded"},
            latency_ms=dt,
            status=201,
        )


# =====================================================================
# GET /api/v1/jobs/<job_id>/status
# =====================================================================

@blp.route("/jobs/<job_id>/status")
class JobStatusResource(MethodView):

    @blp.response(200)
    def get(self, job_id: str):
        """Poll the status of an async batch-match job."""
        t0 = time.perf_counter()
        try:
            from app.celery_app import celery_app as _celery

            task = _celery.AsyncResult(job_id)
            state = task.state

            if state == "PROGRESS":
                meta = task.info or {}
                data = {
                    "job_id": job_id,
                    "state": "PROGRESS",
                    "progress": meta.get("progress", 0),
                    "current": meta.get("current", 0),
                    "total": meta.get("total", 0),
                }
            elif state == "SUCCESS":
                data = {
                    "job_id": job_id,
                    "state": "SUCCESS",
                    "progress": 100,
                    "result": task.result,
                }
            elif state == "FAILURE":
                data = {
                    "job_id": job_id,
                    "state": "FAILURE",
                    "error": str(task.info),
                }
            else:
                data = {"job_id": job_id, "state": state, "progress": 0}

            dt = (time.perf_counter() - t0) * 1000
            return _envelope(data=data, latency_ms=dt)
        except Exception as exc:
            return _envelope(
                errors=[f"Could not retrieve job status: {exc}"],
                success=False,
                status=503,
            )


# =====================================================================
# GET /api/v1/history
# =====================================================================

@blp.route("/history")
class MatchHistoryResource(MethodView):

    @blp.response(200)
    def get(self):
        """Return recent match history (paginated)."""
        t0 = time.perf_counter()
        try:
            from app.models.db_models import MatchHistory

            page = request.args.get("page", 1, type=int)
            per_page = request.args.get("per_page", 20, type=int)
            per_page = min(per_page, 100)

            query = MatchHistory.query.order_by(MatchHistory.created_at.desc())
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)

            items = [
                {
                    "id": m.id,
                    "score": m.score,
                    "grade": m.grade,
                    "matched_skills": m.matched_skills,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in pagination.items
            ]
            dt = (time.perf_counter() - t0) * 1000
            return _envelope(
                data={
                    "results": items,
                    "page": page,
                    "per_page": per_page,
                    "total": pagination.total,
                },
                latency_ms=dt,
            )
        except Exception as exc:
            return _envelope(
                errors=[f"History unavailable: {exc}"],
                success=False,
                status=503,
            )


# =====================================================================
# POST /api/v1/scrape
# =====================================================================

@blp.route("/scrape")
class ScrapeResource(MethodView):
    decorators = [limiter.limit("5/minute")]

    @blp.arguments(ScrapeRequestSchema, location="json")
    @blp.response(200)
    def post(self, payload: dict):
        """Scrape a LinkedIn or Indeed job URL and return structured data."""
        t0 = time.perf_counter()
        try:
            from app.services.job_scraper_service import scrape_job

            result = scrape_job(payload["url"])
            dt = (time.perf_counter() - t0) * 1000
            return _envelope(data=result, latency_ms=dt)
        except ValueError as exc:
            return _envelope(
                errors=[str(exc)], success=False, status=400,
            )
        except PermissionError as exc:
            return _envelope(
                errors=[str(exc)], success=False, status=403,
            )
        except requests.RequestException as exc:
            logger.warning("Scrape failed for %s: %s", payload["url"], exc)
            return _envelope(
                errors=[f"Failed to fetch URL: {exc}"],
                success=False,
                status=502,
            )


# =====================================================================
# GET /api/v1/metrics  (Prometheus)
# =====================================================================

@blp.route("/metrics")
class MetricsResource(MethodView):

    @blp.response(200)
    def get(self):
        """Expose Prometheus metrics."""
        if not _HAS_PROMETHEUS:
            return _envelope(
                errors=["prometheus_client not installed"],
                success=False,
                status=503,
            )
        from flask import Response

        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
