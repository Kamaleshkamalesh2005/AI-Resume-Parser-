"""
Celery application factory.

Usage::

    # In a worker process:
    celery_app = make_celery()

    # CLI:
    celery -A app.celery_app:celery_app worker --loglevel=info
"""

from __future__ import annotations

import logging

from celery import Celery, Task

logger = logging.getLogger(__name__)

celery_app = Celery("resume_matcher")


def make_celery(app=None) -> Celery:
    """Configure the Celery app from Flask config (if available)."""
    if app is not None:
        celery_app.conf.update(
            broker_url=app.config.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
            result_backend=app.config.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
            task_serializer="json",
            result_serializer="json",
            accept_content=["json"],
            timezone="UTC",
            task_track_started=True,
            result_expires=3600,
        )

        class ContextTask(Task):
            """Ensure every task runs inside the Flask application context."""
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery_app.Task = ContextTask  # type: ignore[assignment]

    logger.info("Celery configured (broker=%s)", celery_app.conf.broker_url)
    return celery_app
