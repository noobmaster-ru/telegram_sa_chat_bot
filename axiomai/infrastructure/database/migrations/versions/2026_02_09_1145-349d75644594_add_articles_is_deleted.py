"""add articles.is_deleted

Revision ID: 349d75644594
Revises: 2b3c4d5e6f70
Create Date: 2026-02-09 11:45:29.299786

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "349d75644594"
down_revision: str | Sequence[str] | None = "a2265a0d2c6b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("articles", sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("articles", "is_deleted")
