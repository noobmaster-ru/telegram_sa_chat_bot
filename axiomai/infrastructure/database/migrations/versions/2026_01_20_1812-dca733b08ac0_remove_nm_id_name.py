"""remove nm_id_name

Revision ID: dca733b08ac0
Revises: dbccd4e11e05
Create Date: 2026-01-20 18:12:41.737300

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dca733b08ac0"
down_revision: str | Sequence[str] | None = "dbccd4e11e05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("cabinets", "nm_id_name")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "cabinets",
        sa.Column("nm_id_name", sa.VARCHAR(length=128), autoincrement=False, nullable=False, comment="Артикул"),
    )
