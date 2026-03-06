"""
Data model classes for the Resume Parser backend.
"""

from __future__ import annotations

from app.models.match_result import MatchResult, _grade
from app.models.resume import Resume
from app.models.resume_profile import (
    ContactInfo,
    Education,
    ResumeProfile,
    WorkExperience,
)

__all__ = [
    "ContactInfo",
    "Education",
    "MatchResult",
    "Resume",
    "ResumeProfile",
    "WorkExperience",
    "_grade",
]