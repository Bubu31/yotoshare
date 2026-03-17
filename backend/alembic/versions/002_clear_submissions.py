"""clear all submissions data

Revision ID: 002
Revises: 001
Create Date: 2026-03-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Delete all existing submissions and their associated files
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM submissions"))


def downgrade() -> None:
    # Data deletion is not reversible
    pass
