"""set_is_paid_manually_for_superbanking_buyers

Revision ID: 9a62febe53d3
Revises: e131fdd7ee2c
Create Date: 2026-02-16 19:01:19.998717

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a62febe53d3'
down_revision: Union[str, Sequence[str], None] = 'e131fdd7ee2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        sa.text("UPDATE buyers SET is_paid_manually = true WHERE is_superbanking_paid = true")
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        sa.text("UPDATE buyers SET is_paid_manually = false WHERE is_superbanking_paid = true AND is_superbanking_paid = false")
    )
