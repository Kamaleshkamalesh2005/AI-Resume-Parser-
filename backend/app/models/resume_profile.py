from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ContactInfo:
    emails: List[str] = field(default_factory=list)
    phones: List[str] = field(default_factory=list)
    linkedin: str = ""


@dataclass
class Education:
    degree: str = ""
    institution: str = ""
    year: str = ""


@dataclass
class WorkExperience:
    title: str = ""
    company: str = ""
    duration: str = ""
    years: float = 0.0
    responsibilities: str = ""


@dataclass
class ResumeProfile:
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
    def completeness_score(self) -> float:
        score = 0.0
        if self.name:
            score += 10.0
        if self.contact.emails:
            score += 10.0
        if self.contact.phones:
            score += 10.0
        if self.skills:
            score += 20.0
        if self.education:
            score += 20.0
        if self.experience:
            score += 20.0
        if self.certifications:
            score += 10.0
        return min(100.0, score)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "contact": {
                "emails": list(self.contact.emails),
                "phones": list(self.contact.phones),
                "linkedin": self.contact.linkedin,
            },
            "skills": list(self.skills),
            "education": [
                {"degree": e.degree, "institution": e.institution, "year": e.year}
                for e in self.education
            ],
            "experience": [
                {
                    "title": x.title,
                    "company": x.company,
                    "duration": x.duration,
                    "years": x.years,
                    "responsibilities": x.responsibilities,
                }
                for x in self.experience
            ],
            "certifications": list(self.certifications),
            "organizations": list(self.organizations),
            "cleaned_text": self.cleaned_text,
            "career_timeline": dict(self.career_timeline),
            "completeness_score": self.completeness_score,
        }
