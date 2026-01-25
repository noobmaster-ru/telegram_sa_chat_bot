"""remove nm_id_name

Revision ID: dca733b08ac0
Revises: dbccd4e11e05
Create Date: 2026-01-20 18:12:41.737300

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "dca733b08ac0"
down_revision: Union[str, Sequence[str], None] = "dbccd4e11e05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("cabinets", "nm_id_name")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "cabinets",
        sa.Column("nm_id_name", sa.VARCHAR(length=128), autoincrement=False, nullable=False, comment="Артикул"),
    )
