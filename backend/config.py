"""
Application Configuration
Environment-aware settings for development, production, and testing.
"""

from __future__ import annotations

import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _list(name: str, default: str = "*") -> str | list[str]:
    val = os.environ.get(name, default)
    if val.strip() == "*":
        return "*"
    return [s.strip() for s in val.split(",") if s.strip()]


class Config:
    """Base configuration shared by all environments."""

    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    DEBUG: bool = False
    TESTING: bool = False

    # ---------- paths ----------
    BASE_DIR: str = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER: str = os.environ.get(
        "UPLOAD_FOLDER", os.path.join(BASE_DIR, "uploads")
    )
    MODELS_FOLDER: str = os.environ.get(
        "MODELS_FOLDER", os.path.join(BASE_DIR, "models")
    )
    LOGS_FOLDER: str = os.environ.get(
        "LOGS_FOLDER", os.path.join(BASE_DIR, "logs")
    )
    LOG_FILE: str = os.environ.get(
        "LOG_FILE", os.path.join(LOGS_FOLDER, "app.log")
    )

    # ---------- uploads ----------
    MAX_UPLOAD_SIZE_MB: int = _int("MAX_UPLOAD_SIZE_MB", 50)
    MAX_CONTENT_LENGTH: int = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    ALLOWED_EXTENSIONS: set[str] = {
        e.strip().lower()
        for e in os.environ.get("ALLOWED_EXTENSIONS", "pdf,docx,doc,txt").split(",")
        if e.strip()
    }

    # ---------- NLP / ML ----------
    SPACY_MODEL: str = os.environ.get("SPACY_MODEL", "en_core_web_sm")
    TFIDF_MAX_FEATURES: int = _int("TFIDF_MAX_FEATURES", 5000)
    SVD_N_COMPONENTS: int = _int("SVD_N_COMPONENTS", 100)
    SVM_KERNEL: str = os.environ.get("SVM_KERNEL", "rbf")
    SIMILARITY_THRESHOLD: float = float(
        os.environ.get("SIMILARITY_THRESHOLD", "0.3")
    )

    # ---------- session / cookies ----------
    PERMANENT_SESSION_LIFETIME: timedelta = timedelta(
        hours=_int("SESSION_LIFETIME_HOURS", 24)
    )
    SESSION_COOKIE_SECURE: bool = _bool("SESSION_COOKIE_SECURE", True)
    SESSION_COOKIE_HTTPONLY: bool = _bool("SESSION_COOKIE_HTTPONLY", True)
    SESSION_COOKIE_SAMESITE: str = os.environ.get(
        "SESSION_COOKIE_SAMESITE", "Lax"
    )

    # ---------- CORS ----------
    CORS_ORIGINS: str | list[str] = _list("CORS_ORIGINS", "*")

    # ---------- Redis ----------
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # ---------- rate limiting ----------
    RATELIMIT_STORAGE_URI: str = os.environ.get(
        "RATELIMIT_STORAGE_URI", "memory://"
    )

    # ---------- Celery ----------
    CELERY_BROKER_URL: str = os.environ.get(
        "CELERY_BROKER_URL", REDIS_URL
    )
    CELERY_RESULT_BACKEND: str = os.environ.get(
        "CELERY_RESULT_BACKEND", REDIS_URL
    )
    CELERY_BATCH_THRESHOLD: int = _int("CELERY_BATCH_THRESHOLD", 5)

    # ---------- SQLAlchemy ----------
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "resume_matcher.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # ---------- caching ----------
    NLP_CACHE_TTL: int = _int("NLP_CACHE_TTL", 3600)  # seconds

    # ---------- model optimisation ----------
    SBERT_QUANTIZED: bool = _bool("SBERT_QUANTIZED", False)
    PREWARM_MODELS: bool = _bool("PREWARM_MODELS", True)

    # ---------- logging ----------
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO").upper()
    LOG_FORMAT: str = (
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )


class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "WARNING").upper()
    SECRET_KEY = os.environ.get("SECRET_KEY", "")

    @staticmethod
    def validate_required() -> None:
        if not os.environ.get("SECRET_KEY"):
            raise ValueError("SECRET_KEY must be set in production")


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    UPLOAD_FOLDER = os.path.join(Config.BASE_DIR, "test_uploads")
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    REDIS_URL = ""
    CELERY_BROKER_URL = "memory://"
    CELERY_RESULT_BACKEND = "cache+memory://"
    PREWARM_MODELS = False
    NLP_CACHE_TTL = 0


#: convenience mapping used by the app factory
config_by_name: dict[str, type[Config]] = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
