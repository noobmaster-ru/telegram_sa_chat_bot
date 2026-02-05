"""add cabinets.balance, cabinets.is_suberbanking_connect

Revision ID: 141fa016b430
Revises: 3b30b39e9e4e
Create Date: 2026-02-04 19:09:59.242330

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "141fa016b430"
down_revision: str | Sequence[str] | None = "3b30b39e9e4e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("cabinets", sa.Column("balance", sa.Integer(), nullable=False, comment="Текущий баланс кабинета в рублях", server_default="0"))
    op.add_column("cabinets", sa.Column("is_superbanking_connect", sa.Boolean(), nullable=False, comment="Включена ли выплата через Superbanking для этого кабинета", server_default="false"))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("cabinets", "is_superbanking_connect")
    op.drop_column("cabinets", "balance")
