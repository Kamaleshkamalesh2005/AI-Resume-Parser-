"""
MatchResult – structured output of the ML matching pipeline.

Contains the final score, letter grade, matched / missing skills,
per-category subscores, and a human-readable explanation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


def _grade(score: float) -> str:
    """Map a 0-100 score to a letter grade.
    
    Score ≥ 85 → Grade A
    Score ≥ 70 → Grade B
    Score ≥ 60 → Grade C
    Score ≥ 50 → Grade D
    Score < 50 → Grade F
    """
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    if score >= 50:
        return "D"
    return "F"


@dataclass
class MatchResult:
    """Result of matching a resume against a job description.

    Attributes:
        score:           Overall match percentage (0-100).
        grade:           Letter grade derived from *score*.
        matched_skills:  Skills found in both resume and JD.
        missing_skills:  Top skills from JD not found in resume.
        subscores:       Per-category breakdown
                         (semantic, keyword, tfidf, structural).
        explanation:     One-paragraph human-readable summary.
        ats_score:       ATS-friendliness score (0-100).
        ats_details:     Full ATS simulation breakdown.
        candidate_name:  Name/identifier of the candidate.
        similarity_score: Semantic similarity score (0-100).
        ml_probability:  ML-based match probability (0-100).
    """

    score: float = 0.0
    grade: str = "F"
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    subscores: Dict[str, float] = field(default_factory=dict)
    explanation: str = ""
    ats_score: float = 0.0
    ats_details: Dict[str, Any] = field(default_factory=dict)
    candidate_name: str = ""
    similarity_score: float = 0.0
    ml_probability: float = 0.0

    def __post_init__(self) -> None:
        self.score = round(max(0.0, min(100.0, self.score)), 1)
        self.grade = _grade(self.score)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a JSON-friendly dictionary."""
        d: Dict[str, Any] = {
            "candidate_name": self.candidate_name,
            "similarity_score": self.similarity_score,
            "ml_probability": self.ml_probability,
            "score": self.score,
            "grade": self.grade,
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "subscores": self.subscores,
            "explanation": self.explanation,
        }
        if self.ats_details:
            d["ats_score"] = self.ats_score
            d["ats_details"] = self.ats_details
        return d
