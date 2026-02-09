"""add leads_balance to cabinets

Revision ID: 4a7805eae24d
Revises: b63097b3783c
Create Date: 2025-12-03 16:16:21.656049

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4a7805eae24d"
down_revision: str | Sequence[str] | None = "b63097b3783c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "cabinets",
        sa.Column(
            "leads_balance",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("cabinets", "leads_balance")
