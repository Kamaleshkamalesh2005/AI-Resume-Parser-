"""
MatchResult dataclass and grading helpers.

Used by :mod:`app.services.ml_service` to return structured match results
from the resume-to-job-description scoring pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


def _grade(score: float) -> str:
    """Convert a numeric score (0-100) to a letter grade.

    Thresholds
    ----------
    A : >= 90
    B : >= 75
    C : >= 60
    D : >= 40
    F : < 40
    """
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


@dataclass
class MatchResult:
    """Structured result returned by :class:`~app.services.ml_service.MLService`.

    Parameters
    ----------
    score:
        Raw match score in the range 0-100 (clamped automatically).
    matched_skills:
        Skills present in both the resume and the job description.
    missing_skills:
        Skills required by the job description but absent from the resume.
    subscores:
        Breakdown of the score by component (semantic, keyword, tfidf,
        structural, skills, experience, education).
    explanation:
        Human-readable summary of the match.
    ats_score:
        ATS-simulation score (0-100).
    ats_details:
        Full ATS analysis payload.
    similarity_score:
        Raw SBERT cosine similarity scaled to 0-100.
    ml_probability:
        Keyword-overlap score scaled to 0-100.
    candidate_name:
        Optional candidate identifier.
    """

    score: float = 0.0
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    subscores: Dict[str, float] = field(default_factory=dict)
    explanation: str = ""
    ats_score: float = 0.0
    ats_details: Dict[str, Any] = field(default_factory=dict)
    similarity_score: float = 0.0
    ml_probability: float = 0.0
    candidate_name: str = ""

    def __post_init__(self) -> None:
        self.score = round(float(max(0.0, min(100.0, self.score))), 1)

    @property
    def grade(self) -> str:
        """Letter grade derived from :attr:`score`."""
        return _grade(self.score)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary.

        Only the fields relevant to the public API response are included;
        internal fields (ats_details, similarity_score, ml_probability,
        candidate_name) are intentionally omitted.
        """
        return {
            "score": self.score,
            "grade": self.grade,
            "matched_skills": list(self.matched_skills),
            "missing_skills": list(self.missing_skills),
            "subscores": dict(self.subscores),
            "explanation": self.explanation,
        }
