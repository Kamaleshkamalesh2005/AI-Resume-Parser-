"""
Flask-SocketIO extension singleton.

Initialised in the app factory; used by Celery tasks to emit real-time
batch-progress events to connected clients.
"""

from __future__ import annotations

import logging

from flask_socketio import SocketIO

logger = logging.getLogger(__name__)

socketio = SocketIO()


def init_socketio(app) -> SocketIO:
    """Attach SocketIO to the Flask *app*."""
    socketio.init_app(
        app,
        cors_allowed_origins=app.config.get("CORS_ORIGINS", "*"),
        async_mode="eventlet",
        message_queue=app.config.get("REDIS_URL") or None,
        logger=False,
        engineio_logger=False,
    )
    logger.info("Flask-SocketIO initialised")
    return socketio
