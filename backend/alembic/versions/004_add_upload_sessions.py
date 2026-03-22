"""add upload_sessions table for chunked uploads

Revision ID: 004
Revises: 003
Create Date: 2026-03-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "upload_sessions",
        sa.Column("upload_id", sa.String(36), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("total_size", sa.Integer(), nullable=False),
        sa.Column("total_chunks", sa.Integer(), nullable=False),
        sa.Column("chunk_size", sa.Integer(), nullable=False),
        sa.Column("pseudonym", sa.String(255), nullable=True),
        sa.Column("parent_submission_id", sa.Integer(), nullable=True),
        sa.Column("submitter_ip", sa.String(45), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("upload_id"),
    )
    op.create_index("ix_upload_sessions_upload_id", "upload_sessions", ["upload_id"])
    op.create_index("ix_upload_sessions_expires_at", "upload_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_upload_sessions_expires_at", table_name="upload_sessions")
    op.drop_index("ix_upload_sessions_upload_id", table_name="upload_sessions")
    op.drop_table("upload_sessions")
