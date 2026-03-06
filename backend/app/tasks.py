"""
Celery tasks for async batch matching.

Batch requests with more than ``CELERY_BATCH_THRESHOLD`` resumes are
dispatched here, returning a ``job_id`` immediately.  Progress is
emitted via Flask-SocketIO so connected clients see real-time updates.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="batch_match")
def batch_match_task(
    self,
    resume_texts: List[str],
    job_description: str,
    resume_filenames: List[str] = None,
) -> Dict[str, Any]:
    """Score *resume_texts* against *job_description* asynchronously.

    Updates task meta with ``progress`` (0-100) so callers can poll.
    
    Parameters
    ----------
    resume_texts : List[str]
        List of resume texts to score
    job_description : str
        Job description to match against
    resume_filenames : List[str], optional
        Optional list of filenames for candidate identification
    """
    from app.services.ml_service import MLService

    t0 = time.perf_counter()
    total = len(resume_texts)
    results: List[Dict[str, Any]] = []
    filenames = resume_filenames or []

    # Use a fresh MLService for the worker process
    ml = MLService(models_dir="models")

    for idx, resume in enumerate(resume_texts):
        # Use provided filename or generate candidate name
        if filenames and idx < len(filenames):
            candidate_name = filenames[idx]
        else:
            candidate_name = f"Candidate {idx + 1}"
        
        result = ml.score(resume, job_description, candidate_name=candidate_name)
        results.append(result.to_dict())

        progress = int((idx + 1) / total * 100)
        self.update_state(
            state="PROGRESS",
            meta={"current": idx + 1, "total": total, "progress": progress},
        )

        # Emit SocketIO event (best-effort, non-blocking)
        try:
            from app.socketio_ext import socketio

            socketio.emit(
                "batch_progress",
                {
                    "job_id": self.request.id,
                    "current": idx + 1,
                    "total": total,
                    "progress": progress,
                },
                namespace="/jobs",
            )
        except Exception:
            pass  # SocketIO may not be available in worker

    # Sort by score descending
    results.sort(key=lambda r: r["score"], reverse=True)
    
    # Add rank numbers after sorting
    for rank, row in enumerate(results, start=1):
        row["rank"] = rank
    
    dt = (time.perf_counter() - t0) * 1000

    return {
        "results": results,
        "total": total,
        "latency_ms": round(dt, 2),
    }
