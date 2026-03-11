"""
SQLAlchemy models for match history persistence.
"""

from __future__ import annotations

import datetime

from app.extensions import db


class MatchHistory(db.Model):  # type: ignore[name-defined]
    """Stores every match result for analytics and retrieval."""

    __tablename__ = "match_history"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(128), nullable=True, index=True)
    resume_hash = db.Column(db.String(64), nullable=False)
    jd_hash = db.Column(db.String(64), nullable=False)
    score = db.Column(db.Float, nullable=False)
    grade = db.Column(db.String(2), nullable=False)
    matched_skills = db.Column(db.Text, nullable=True)  # JSON string
    missing_skills = db.Column(db.Text, nullable=True)   # JSON string
    subscores = db.Column(db.Text, nullable=True)         # JSON string
    explanation = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        index=True,
    )

    def __repr__(self) -> str:
        return f"<MatchHistory id={self.id} score={self.score} grade={self.grade!r}>"
