"""
Flask Application Factory
"""

from __future__ import annotations

import logging
import os
from typing import Type

from flask import Flask, jsonify
from flask_cors import CORS
from flask_smorest import Api

from config import Config, ProductionConfig, config_by_name


def create_app(config_class: Type[Config] = Config) -> Flask:
    """Create and configure the Flask application."""

    app = Flask(__name__)
    app.config.from_object(config_class)

    # flask-smorest / OpenAPI settings
    app.config.setdefault("API_TITLE", "AI Resume Matcher")
    app.config.setdefault("API_VERSION", "v1")
    app.config.setdefault("OPENAPI_VERSION", "3.0.3")
    app.config.setdefault("OPENAPI_URL_PREFIX", "/api/v1/docs")
    app.config.setdefault("OPENAPI_SWAGGER_UI_PATH", "/")
    app.config.setdefault(
        "OPENAPI_SWAGGER_UI_URL",
        "https://cdn.jsdelivr.net/npm/swagger-ui-dist/",
    )

    # CORS for API routes
    CORS(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})

    # Logging
    _setup_logging(app)
    logger = logging.getLogger(__name__)

    # ── SQLAlchemy + Migrate ─────────────────────────────────────
    from app.extensions import db, migrate
    db.init_app(app)
    migrate.init_app(app, db)

    # Import models so Alembic sees them
    with app.app_context():
        from app.models import db_models  # noqa: F401
        db.create_all()

    # ── Redis cache ──────────────────────────────────────────────
    from app.cache import init_cache
    init_cache(app.config.get("REDIS_URL", ""))

    # ── Celery ───────────────────────────────────────────────────
    from app.celery_app import make_celery
    make_celery(app)

    # ── Flask-SocketIO ───────────────────────────────────────────
    try:
        from app.socketio_ext import init_socketio
        init_socketio(app)
    except Exception as exc:
        logger.info("SocketIO not initialised: %s", exc)

    # ML service – loaded once at startup, cached on app
    app.ml_service = None  # type: ignore[attr-defined]
    try:
        from app.services.ml_service import MLService

        app.ml_service = MLService(  # type: ignore[attr-defined]
            models_dir=app.config.get("MODELS_FOLDER", "models")
        )
        logger.info("ML service initialised")
    except Exception as exc:  # noqa: BLE001
        logger.warning("ML service unavailable: %s", exc)

    # ── Model pre-warming (background thread) ────────────────────
    if app.config.get("PREWARM_MODELS", False):
        from app.services.ml_service import prewarm_models
        prewarm_models(quantized=app.config.get("SBERT_QUANTIZED", False))

    # flask-smorest Api + v1 blueprint
    api = Api(app)
    from app.blueprints.api.routes import blp as api_v1_blp, limiter as v1_limiter
    v1_limiter.init_app(app)
    api.register_blueprint(api_v1_blp)

    # Legacy blueprints
    _register_blueprints(app)

    # Error handlers
    _register_error_handlers(app)

    # Ensure directories
    for d in (app.config["UPLOAD_FOLDER"], app.config["MODELS_FOLDER"], app.config["LOGS_FOLDER"]):
        os.makedirs(d, exist_ok=True)

    logger.info("Flask application ready")
    return app


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _setup_logging(app: Flask) -> None:
    from logging.handlers import RotatingFileHandler

    log_dir = app.config.get("LOGS_FOLDER", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = app.config.get("LOG_FILE", os.path.join(log_dir, "app.log"))

    fmt = logging.Formatter(app.config.get("LOG_FORMAT", "%(asctime)s | %(levelname)s | %(message)s"))
    level = getattr(logging, app.config.get("LOG_LEVEL", "INFO"))

    fh = RotatingFileHandler(log_file, maxBytes=10_485_760, backupCount=10)
    fh.setLevel(level)
    fh.setFormatter(fmt)

    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        root.addHandler(fh)
        root.addHandler(ch)


def _register_blueprints(app: Flask) -> None:
    # API blueprint (JSON endpoints)
    from app.blueprints.api import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    # UI blueprint (HTML pages)
    from app.blueprints.ui import ui_bp
    app.register_blueprint(ui_bp)


def _register_error_handlers(app: Flask) -> None:

    @app.errorhandler(400)
    def bad_request(error):  # type: ignore[no-untyped-def]
        return jsonify({"success": False, "error": "Bad Request", "message": str(error)}), 400

    @app.errorhandler(404)
    def not_found(error):  # type: ignore[no-untyped-def]
        return jsonify({"success": False, "error": "Not Found", "message": "The requested resource was not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):  # type: ignore[no-untyped-def]
        return jsonify({"success": False, "error": "Method Not Allowed", "message": str(error)}), 405

    @app.errorhandler(413)
    def payload_too_large(error):  # type: ignore[no-untyped-def]
        return jsonify({"success": False, "error": "Payload Too Large", "message": "File exceeds maximum allowed size"}), 413

    @app.errorhandler(500)
    def internal_error(error):  # type: ignore[no-untyped-def]
        logging.getLogger(__name__).error("Internal Server Error: %s", error)
        return jsonify({"success": False, "error": "Internal Server Error", "message": "An unexpected error occurred"}), 500

    @app.errorhandler(Exception)
    def handle_exception(error):  # type: ignore[no-untyped-def]
        """Catch-all error handler to ensure JSON response for all errors."""
        logging.getLogger(__name__).error("Unhandled exception: %s", error, exc_info=True)
        return jsonify({
            "success": False,
            "error": "Server Error",
            "message": "An unexpected error occurred. Please try again.",
            "errors": [str(error)]
        }), 500


def _resolve_config_class() -> Type[Config]:
    env = os.environ.get("FLASK_ENV", "development")
    config_class = config_by_name.get(env, config_by_name["development"])
    if env == "production":
        ProductionConfig.validate_required()
    return config_class


# Gunicorn compatibility: supports both `gunicorn app:app` and `gunicorn run:app`.
app = create_app(config_class=_resolve_config_class())
