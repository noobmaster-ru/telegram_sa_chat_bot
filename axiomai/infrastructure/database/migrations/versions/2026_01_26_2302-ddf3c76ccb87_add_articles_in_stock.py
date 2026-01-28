"""add articles.in_stock

Revision ID: ddf3c76ccb87
Revises: 4e60c8539d34
Create Date: 2026-01-26 23:02:23.511318

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ddf3c76ccb87"
down_revision: str | Sequence[str] | None = "4e60c8539d34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("articles", sa.Column("in_stock", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("articles", "in_stock")
