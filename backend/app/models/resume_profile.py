"""
Structured data classes for parsed resume content.

These dataclasses are populated by :class:`~app.services.nlp_service.NLPService`
and consumed by the API layer and tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ContactInfo:
    """Contact details extracted from a resume.

    Parameters
    ----------
    emails:
        List of email addresses found in the text.
    phones:
        List of phone numbers found in the text.
    linkedin:
        LinkedIn profile URL or handle, if present.
    """

    emails: List[str] = field(default_factory=list)
    phones: List[str] = field(default_factory=list)
    linkedin: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "emails": list(self.emails),
            "phones": list(self.phones),
            "linkedin": self.linkedin,
        }


@dataclass
class Education:
    """A single education entry extracted from a resume.

    Parameters
    ----------
    degree:
        Degree or qualification title (e.g. "Bachelor of Science").
    institution:
        Name of the academic institution.
    year:
        Graduation or attendance year as a string.
    """

    degree: str = ""
    institution: str = ""
    year: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "degree": self.degree,
            "institution": self.institution,
            "year": self.year,
        }


@dataclass
class WorkExperience:
    """A single work-experience entry extracted from a resume.

    Parameters
    ----------
    title:
        Job title or role name.
    company:
        Employer or organisation name.
    duration:
        Human-readable duration string (e.g. "2019 - 2023").
    years:
        Numeric duration in years (may be approximate).
    responsibilities:
        Free-text description of duties / achievements.
    """

    title: str = ""
    company: str = ""
    duration: str = ""
    years: float = 0.0
    responsibilities: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "company": self.company,
            "duration": self.duration,
            "years": self.years,
            "responsibilities": self.responsibilities,
        }


# ── Completeness weights ─────────────────────────────────────────────
# The weights below sum to 100 and match the test expectations:
#   name(10) + email(10) + phone(5) + linkedin(5)
#   + skills(20) + education(15) + experience(25) + certifications(10) = 100
_WEIGHT_NAME = 10
_WEIGHT_EMAIL = 10
_WEIGHT_PHONE = 5
_WEIGHT_LINKEDIN = 5
_WEIGHT_SKILLS = 20
_WEIGHT_EDUCATION = 15
_WEIGHT_EXPERIENCE = 25
_WEIGHT_CERTIFICATIONS = 10


@dataclass
class ResumeProfile:
    """Fully structured representation of a parsed resume.

    Instances are created by :meth:`~app.services.nlp_service.NLPService._analyse`
    and cached via :func:`~app.services.nlp_service._cached_analyse`.

    Parameters
    ----------
    name:
        Candidate full name.
    contact:
        Extracted contact information.
    skills:
        List of recognised skill names.
    education:
        List of education entries.
    experience:
        List of work-experience entries.
    certifications:
        List of certification strings.
    organizations:
        List of organisation names detected via NER.
    cleaned_text:
        Normalised resume text (output of
        :meth:`~app.services.nlp_service.NLPService.clean_text`).
    career_timeline:
        Career-timeline analysis payload from
        :func:`~app.services.career_analyzer.analyse_career_timeline`.
    """

    name: str = ""
    contact: ContactInfo = field(default_factory=ContactInfo)
    skills: List[str] = field(default_factory=list)
    education: List[Education] = field(default_factory=list)
    experience: List[WorkExperience] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    organizations: List[str] = field(default_factory=list)
    cleaned_text: str = ""
    career_timeline: Dict[str, Any] = field(default_factory=dict)

    @property
    def completeness_score(self) -> int:
        """Estimate how complete the resume is (0-100).

        Each section is awarded a fixed weight only if it contains
        meaningful data.  The weights sum to 100.
        """
        score = 0
        if self.name:
            score += _WEIGHT_NAME
        if self.contact.emails:
            score += _WEIGHT_EMAIL
        if self.contact.phones:
            score += _WEIGHT_PHONE
        if self.contact.linkedin:
            score += _WEIGHT_LINKEDIN
        if self.skills:
            score += _WEIGHT_SKILLS
        if self.education:
            score += _WEIGHT_EDUCATION
        if self.experience:
            score += _WEIGHT_EXPERIENCE
        if self.certifications:
            score += _WEIGHT_CERTIFICATIONS
        return int(min(100, score))

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary suitable for caching or JSON output."""
        return {
            "name": self.name,
            "contact": self.contact.to_dict(),
            "skills": list(self.skills),
            "education": [e.to_dict() for e in self.education],
            "experience": [x.to_dict() for x in self.experience],
            "certifications": list(self.certifications),
            "organizations": list(self.organizations),
            "cleaned_text": self.cleaned_text,
            "career_timeline": self.career_timeline,
            "completeness_score": self.completeness_score,
        }
