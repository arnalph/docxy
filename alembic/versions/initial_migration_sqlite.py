"""add full_text to jobs

Revision ID: 2a3b4c5d6e7f
Revises: 889cb2cfdb5b
Create Date: 2026-03-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a3b4c5d6e7f'
down_revision: Union[str, Sequence[str], None] = '889cb2cfdb5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add full_text column to jobs table."""
    op.add_column('jobs', sa.Column('full_text', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove full_text column from jobs table."""
    op.drop_column('jobs', 'full_text')