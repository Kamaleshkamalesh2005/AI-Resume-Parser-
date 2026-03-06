"""
Resume domain object.

Provides a lightweight container that holds all structured data extracted
from a single resume file.  Populated by
:meth:`~app.services.nlp_service.NLPService.parse_file`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class Resume:
    """Container for structured resume data.

    Parameters
    ----------
    filepath:
        Absolute or relative path to the original resume file.
    """

    def __init__(self, filepath: str = "") -> None:
        self.filepath: str = filepath
        self.raw_text: str = ""
        self.cleaned_text: str = ""
        self.name: str = ""
        self.emails: List[str] = []
        self.phones: List[str] = []
        self.skills: List[str] = []
        self.education: List[Dict[str, Any]] = []
        self.experience: List[Dict[str, Any]] = []
        self.organizations: List[str] = []
        self.certifications: List[str] = []
        self.parsed: bool = False
        self.error: Optional[str] = None

        # Feature vector computed by compute_features()
        self.num_skills: int = 0
        self.num_education: int = 0
        self.num_experience: int = 0
        self.text_length: int = 0

    def compute_features(self) -> None:
        """Populate derived numeric features from the extracted fields."""
        self.num_skills = len(self.skills)
        self.num_education = len(self.education)
        self.num_experience = len(self.experience)
        self.text_length = len(self.cleaned_text)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary."""
        return {
            "filepath": self.filepath,
            "name": self.name,
            "emails": list(self.emails),
            "phones": list(self.phones),
            "skills": list(self.skills),
            "education": list(self.education),
            "experience": list(self.experience),
            "organizations": list(self.organizations),
            "certifications": list(self.certifications),
            "parsed": self.parsed,
            "error": self.error,
        }
