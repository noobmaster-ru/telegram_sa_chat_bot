"""add superbanking table

Revision ID: 9f1b2c3d4e5f
Revises: a1b2c3d4e5f6
Create Date: 2026-02-06 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f1b2c3d4e5f"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "superbanking",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("nm_id", sa.Integer(), nullable=False, comment="Артикул товара"),
        sa.Column("phone_number", sa.String(length=32), nullable=False, comment="Номер телефона для выплаты"),
        sa.Column("bank", sa.String(length=128), nullable=False, comment="Название банка"),
        sa.Column("amount", sa.Integer(), nullable=False, comment="Сумма кешбека в рублях"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["buyer_id"], ["buyers.id"], name=op.f("fk_superbanking_buyer_id_buyers")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_superbanking")),
    )
    op.create_index(op.f("ix_superbanking_buyer_id"), "superbanking", ["buyer_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_superbanking_buyer_id"), table_name="superbanking")
    op.drop_table("superbanking")
