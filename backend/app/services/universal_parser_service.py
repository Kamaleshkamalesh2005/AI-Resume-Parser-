"""
Universal Resume Parser Service

Integration service for Flask app with the 9-step production parser.
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

from app.core import get_parser

logger = logging.getLogger(__name__)


class UniversalResumeParserService:
    """Service wrapper for Universal Resume Parser."""

    def __init__(self):
        """Initialize parser service."""
        self.parser = get_parser()

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse resume from file.
        
        Args:
            file_path: Path to resume file (PDF or DOCX)
        
        Returns:
            {
                "success": bool,
                "data": {
                    "name": str,
                    "email": str,
                    "phone": str,
                    "skills": [str],
                    "education": [{degree, institution, year_range}],
                    "experience": [{job_title, company, duration}],
                    "organizations": [str]
                },
                "error": str (if success is False)
            }
        """
        try:
            return self.parser.parse(file_path)
        except Exception as e:
            logger.error(f"Service parse_file failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def parse_text(self, text: str) -> Dict[str, Any]:
        """
        Parse resume from raw text.
        
        Args:
            text: Resume text content
        
        Returns:
            Same structure as parse_file
        """
        try:
            if not text or len(text) < 50:
                return {
                    "success": False,
                    "error": "Resume text too short (minimum 50 characters)"
                }
            
            return self.parser.parse_text(text)
        except Exception as e:
            logger.error(f"Service parse_text failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_supported_formats(self) -> Dict[str, str]:
        """Get supported file formats."""
        return {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        }


# Global service instance
_service_instance = None

def get_parser_service() -> UniversalResumeParserService:
    """Get global parser service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = UniversalResumeParserService()
        logger.info("Universal Parser Service initialized")
    return _service_instance
