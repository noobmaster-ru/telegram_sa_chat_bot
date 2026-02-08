"""add order number to superbanking

Revision ID: 1c2d3e4f5a6b
Revises: 9f1b2c3d4e5f
Create Date: 2026-02-07 10:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1c2d3e4f5a6b"
down_revision: str | Sequence[str] | None = "9f1b2c3d4e5f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "superbanking",
        sa.Column(
            "order_number",
            sa.String(length=64),
            nullable=True,
            comment="Уникальный номер перевода для идемпотентности",
        ),
    )
    op.execute(sa.text("UPDATE superbanking SET order_number = 'payment-' || id WHERE order_number IS NULL"))
    op.alter_column("superbanking", "order_number", nullable=False)
    op.create_index(op.f("ix_superbanking_order_number"), "superbanking", ["order_number"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_superbanking_order_number"), table_name="superbanking")
    op.drop_column("superbanking", "order_number")
