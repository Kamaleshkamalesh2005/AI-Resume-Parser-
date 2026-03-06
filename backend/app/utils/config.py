"""
Configuration Management Module
Defines application settings for different environments (dev/prod/test)
"""

import os
from datetime import timedelta
from dotenv import load_dotenv


load_dotenv()


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_list(name: str, default: str = "*"):
    value = os.environ.get(name, default)
    if value.strip() == "*":
        return "*"
    return [item.strip() for item in value.split(",") if item.strip()]


class Config:
    """Base Configuration - Common settings for all environments"""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = _get_bool('DEBUG', False)
    TESTING = _get_bool('TESTING', False)
    ENV = os.environ.get('FLASK_ENV', 'development')
    
    # Upload Configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'uploads'))
    MODELS_FOLDER = os.environ.get('MODELS_FOLDER', os.path.join(os.getcwd(), 'models'))
    LOGS_FOLDER = os.environ.get('LOGS_FOLDER', os.path.join(os.getcwd(), 'logs'))
    
    # File Upload Limits
    MAX_UPLOAD_SIZE_MB = _get_int('MAX_UPLOAD_SIZE_MB', 50)
    MAX_CONTENT_LENGTH = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    ALLOWED_EXTENSIONS = {
        ext.strip().lower()
        for ext in os.environ.get('ALLOWED_EXTENSIONS', 'pdf,docx,txt,doc').split(',')
        if ext.strip()
    }
    
    # NLP Model Settings
    SPACY_MODEL = os.environ.get('SPACY_MODEL', 'en_core_web_sm')
    
    # ML Model Settings
    TF_IDF_MAX_FEATURES = _get_int('TF_IDF_MAX_FEATURES', 5000)
    SVD_N_COMPONENTS = _get_int('SVD_N_COMPONENTS', 100)
    SVM_KERNEL = os.environ.get('SVM_KERNEL', 'rbf')
    COSINE_SIMILARITY_THRESHOLD = float(os.environ.get('SIMILARITY_THRESHOLD', 0.3))
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=_get_int('SESSION_LIFETIME_HOURS', 24))
    SESSION_COOKIE_SECURE = _get_bool('SESSION_COOKIE_SECURE', True)
    SESSION_COOKIE_HTTPONLY = _get_bool('SESSION_COOKIE_HTTPONLY', True)
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    
    # CORS Configuration
    CORS_ORIGINS = _get_list('CORS_ORIGINS', '*')
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
    LOG_FORMAT = (
        '%(asctime)s | %(levelname)s | %(name)s | %(process)d | %(threadName)s '
        '| %(remote_addr)s | %(request_path)s | %(message)s'
    )
    LOG_FILE = os.environ.get('LOG_FILE', os.path.join(LOGS_FOLDER, 'app.log'))

    # Rate limiting
    RATELIMIT_ENABLED = _get_bool('RATELIMIT_ENABLED', True)
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '200 per day,50 per hour')
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')


class DevelopmentConfig(Config):
    """Development Environment Configuration"""
    DEBUG = True
    TESTING = False
    LOG_LEVEL = 'DEBUG'
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production Environment Configuration"""
    DEBUG = False
    TESTING = False
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
    SECRET_KEY = os.environ.get('SECRET_KEY', '')

    @staticmethod
    def validate_required():
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("SECRET_KEY environment variable must be set in production")


class TestingConfig(Config):
    """Testing Environment Configuration"""
    TESTING = True
    DEBUG = True
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'test_uploads')
    SESSION_COOKIE_SECURE = False
