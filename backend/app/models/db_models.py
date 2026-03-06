"""
SQLAlchemy database models for the Resume Parser backend.

Defines ORM models that are persisted to the configured relational database.
These are imported by the app factory so that Flask-Migrate / Alembic can
detect schema changes.
"""
from __future__ import annotations

import datetime
from typing import Optional

from app.extensions import db


class MatchHistory(db.Model):  # type: ignore[name-defined]
    """Persisted record of a resume-to-job-description match.

    Attributes
    ----------
    id:
        Auto-incremented primary key.
    resume_hash:
        SHA-256 hex digest of the resume text (for deduplication).
    jd_hash:
        SHA-256 hex digest of the job-description text.
    score:
        Numeric match score (0–100).
    grade:
        Letter grade derived from *score* (A/B/C/D/F).
    matched_skills:
        JSON-encoded list of matched skill names.
    missing_skills:
        JSON-encoded list of missing skill names.
    subscores:
        JSON-encoded dict of per-component scores.
    explanation:
        Human-readable match explanation.
    created_at:
        UTC timestamp when the record was created.
    """

    __tablename__ = "match_history"

    id: int = db.Column(db.Integer, primary_key=True)
    resume_hash: str = db.Column(db.String(64), nullable=False, index=True)
    jd_hash: str = db.Column(db.String(64), nullable=False, index=True)
    score: float = db.Column(db.Float, nullable=False)
    grade: str = db.Column(db.String(2), nullable=False)
    matched_skills: str = db.Column(db.Text, nullable=False, default="[]")
    missing_skills: str = db.Column(db.Text, nullable=False, default="[]")
    subscores: str = db.Column(db.Text, nullable=False, default="{}")
    explanation: str = db.Column(db.Text, nullable=False, default="")
    created_at: Optional[datetime.datetime] = db.Column(
        db.DateTime,
        nullable=True,
        default=datetime.datetime.utcnow,
    )

    def __repr__(self) -> str:
        return f"<MatchHistory id={self.id} score={self.score} grade={self.grade}>"
