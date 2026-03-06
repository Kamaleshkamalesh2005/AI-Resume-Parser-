"""
Logging Configuration Module
Sets up centralized logging for the application with file and console output.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from app.utils.config import Config
from flask import has_request_context, request


class RequestContextFilter(logging.Filter):
    """Inject request context fields into log records."""

    def filter(self, record):
        if has_request_context():
            record.remote_addr = request.headers.get('X-Forwarded-For', request.remote_addr)
            record.request_path = request.path
        else:
            record.remote_addr = '-'
            record.request_path = '-'
        return True


def setup_logger(app):
    """
    Initialize application-wide logging
    Creates both file and console handlers with appropriate formatting.
    
    Args:
        app: Flask application instance
    """
    
    # Ensure logs directory exists
    os.makedirs(app.config['LOGS_FOLDER'], exist_ok=True)
    
    # Create logger
    logger = logging.getLogger('resume_matcher')
    logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))
    logger.propagate = False
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Format for log messages
    log_format = logging.Formatter(app.config['LOG_FORMAT'])
    context_filter = RequestContextFilter()
    
    # File Handler - Rotating to prevent massive log files
    file_handler = RotatingFileHandler(
        app.config['LOG_FILE'],
        maxBytes=10485760,  # 10 MB
        backupCount=10      # Keep 10 backup files
    )
    file_handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
    file_handler.setFormatter(log_format)
    file_handler.addFilter(context_filter)
    logger.addHandler(file_handler)
    
    # Console Handler - For development visibility
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
    console_handler.setFormatter(log_format)
    console_handler.addFilter(context_filter)
    logger.addHandler(console_handler)
    
    # Suppress third-party library logging noise
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('spacy').setLevel(logging.WARNING)
    
    logger.info("=" * 60)
    logger.info("Resume Matcher Application Logger Initialized")
    logger.info(f"Log Level: {app.config['LOG_LEVEL']}")
    logger.info(f"Log File: {app.config['LOG_FILE']}")
    logger.info("=" * 60)
    
    return logger


def get_logger(name):
    """
    Get or create a logger instance for a specific module
    
    Args:
        name: Module name for the logger
    
    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)
