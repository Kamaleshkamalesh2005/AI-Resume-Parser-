"""
Initial migration – create match_history table.

Revision ID: 001
Create Date: 2024-01-01
"""

from alembic import op
import sqlalchemy as sa

revision = "001_match_history"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "match_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(128), nullable=True),
        sa.Column("resume_hash", sa.String(64), nullable=False),
        sa.Column("jd_hash", sa.String(64), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("grade", sa.String(2), nullable=False),
        sa.Column("matched_skills", sa.Text(), nullable=True),
        sa.Column("missing_skills", sa.Text(), nullable=True),
        sa.Column("subscores", sa.Text(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_match_history_user_id", "match_history", ["user_id"])
    op.create_index("ix_match_history_created_at", "match_history", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_match_history_created_at", "match_history")
    op.drop_index("ix_match_history_user_id", "match_history")
    op.drop_table("match_history")
