"""add rework fields to submissions

Revision ID: 003
Revises: 002
Create Date: 2026-03-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("submissions", sa.Column("rework_comment", sa.Text(), nullable=True))
    op.add_column("submissions", sa.Column("parent_submission_id", sa.Integer(), sa.ForeignKey("submissions.id"), nullable=True))
    op.create_index("ix_submissions_parent_submission_id", "submissions", ["parent_submission_id"])


def downgrade() -> None:
    op.drop_index("ix_submissions_parent_submission_id", table_name="submissions")
    op.drop_column("submissions", "parent_submission_id")
    op.drop_column("submissions", "rework_comment")
