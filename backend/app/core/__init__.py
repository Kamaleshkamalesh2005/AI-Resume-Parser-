"""
Core Resume Parsing Module

Universal Resume Parser with 9-step production pipeline.
"""

from .extractor import UniversalResumeParser, get_parser
from .skill_dict import get_all_skills, is_skill
from .section_aliases import SECTION_ALIASES

__all__ = [
    "UniversalResumeParser",
    "get_parser",
    "get_all_skills",
    "is_skill",
    "SECTION_ALIASES",
]
