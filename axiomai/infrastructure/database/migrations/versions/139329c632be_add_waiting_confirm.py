"""add waiting_confirm

Revision ID: 139329c632be
Revises: 4a7805eae24d
Create Date: 2025-12-03 17:52:59.982444

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '139329c632be'
down_revision: Union[str, Sequence[str], None] = '4a7805eae24d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE payment_status ADD VALUE IF NOT EXISTS 'WAITING_CONFIRM'")



def downgrade() -> None:
    """Downgrade schema."""
    pass
