"""add leads_balance to cabinets

Revision ID: 4a7805eae24d
Revises: b63097b3783c
Create Date: 2025-12-03 16:16:21.656049

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a7805eae24d'
down_revision: Union[str, Sequence[str], None] = 'b63097b3783c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
    # опционально: убираем server_default после заполнения
    # op.alter_column("cabinets", "leads_balance", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("cabinets", "leads_balance")
