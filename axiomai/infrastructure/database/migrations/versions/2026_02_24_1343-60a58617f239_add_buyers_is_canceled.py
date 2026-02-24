"""add buyers.is_canceled

Revision ID: 60a58617f239
Revises: 9a62febe53d3
Create Date: 2026-02-24 13:43:39.856685

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "60a58617f239"
down_revision: str | Sequence[str] | None = "9a62febe53d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("buyers", sa.Column("is_canceled", sa.Boolean(), nullable=False, server_default="false", comment="Заявка отменена покупателем"))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("buyers", "is_canceled")
