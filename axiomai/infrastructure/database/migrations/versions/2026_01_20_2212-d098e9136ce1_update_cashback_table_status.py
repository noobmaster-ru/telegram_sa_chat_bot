"""update cashback table status

Revision ID: d098e9136ce1
Revises: dca733b08ac0
Create Date: 2026-01-20 22:12:18.576842

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d098e9136ce1"
down_revision: str | Sequence[str] | None = "dca733b08ac0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "cashback_tables",
        "status",
        existing_type=sa.VARCHAR(length=8),
        type_=sa.Enum(
            "NEW",
            "WAITING_WRITE_PERMISSION",
            "VERIFIED",
            "PAID",
            "DISABLED",
            "EXPIRED",
            name="cashbacktablestatus",
            native_enum=False,
        ),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "cashback_tables",
        "status",
        existing_type=sa.Enum(
            "NEW",
            "WAITING_WRITE_PERMISSION",
            "VERIFIED",
            "PAID",
            "DISABLED",
            "EXPIRED",
            name="cashbacktablestatus",
            native_enum=False,
        ),
        type_=sa.VARCHAR(length=8),
        existing_nullable=False,
    )
