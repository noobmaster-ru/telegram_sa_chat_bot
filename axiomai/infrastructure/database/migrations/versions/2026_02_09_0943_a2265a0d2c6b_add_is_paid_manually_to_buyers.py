"""add is_paid_manually to buyers

Revision ID: a2265a0d2c6b
Revises: 23d1363dc937
Create Date: 2026-02-09 09:43:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2265a0d2c6b"
down_revision: str | Sequence[str] | None = "2b3c4d5e6f70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: add is_paid_manually to buyers."""
    op.add_column(
        "buyers",
        sa.Column(
            "is_paid_manually",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Выплата проставлена вручную в таблице",
        ),
    )


def downgrade() -> None:
    """Downgrade schema: remove is_paid_manually from buyers."""
    op.drop_column("buyers", "is_paid_manually")
