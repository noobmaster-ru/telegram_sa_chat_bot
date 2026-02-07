"""shrink superbanking order_number length

Revision ID: 2b3c4d5e6f70
Revises: 1c2d3e4f5a6b
Create Date: 2026-02-07 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2b3c4d5e6f70"
down_revision: str | Sequence[str] | None = "1c2d3e4f5a6b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "superbanking",
        "order_number",
        type_=sa.String(length=30),
        existing_type=sa.String(length=64),
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "superbanking",
        "order_number",
        type_=sa.String(length=64),
        existing_type=sa.String(length=30),
        nullable=False,
    )
