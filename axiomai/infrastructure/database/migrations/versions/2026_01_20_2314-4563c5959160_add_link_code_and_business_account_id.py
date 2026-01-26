"""add_link_code_and_business_account_id

Revision ID: 4563c5959160
Revises: d098e9136ce1
Create Date: 2026-01-20 23:14:17.173115

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4563c5959160"
down_revision: str | Sequence[str] | None = "d098e9136ce1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "cabinets",
        sa.Column("business_account_id", sa.BigInteger(), nullable=True, comment="Telegram ID бизнес-аккаунта"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("cabinets", "business_account_id")
