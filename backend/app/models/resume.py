from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Resume:
    """Minimal Resume model required by backend/app/services/nlp_service.py."""

    filepath: str = ""
    raw_text: str = ""
    cleaned_text: str = ""

    name: str = ""
    emails: List[str] = field(default_factory=list)
    phones: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)

    education: List[Dict[str, Any]] = field(default_factory=list)
    experience: List[Dict[str, Any]] = field(default_factory=list)

    organizations: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)

    parsed: bool = False
    error: Optional[str] = None

    def compute_features(self) -> None:
        # Called by NLPService.parse_file(); safe no-op for tests.
        return
