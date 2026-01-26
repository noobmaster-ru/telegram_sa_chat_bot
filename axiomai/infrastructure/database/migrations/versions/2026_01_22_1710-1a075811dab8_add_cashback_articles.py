"""delete cashback article fields

Revision ID: 1a075811dab8
Revises: 4563c5959160
Create Date: 2026-01-22 17:10:44.005911

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1a075811dab8"
down_revision: str | Sequence[str] | None = "4563c5959160"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Удаляем старые поля из cashback_tables
    op.drop_column("cashback_tables", "instruction_text")
    op.drop_column("cashback_tables", "brand_name")
    op.drop_column("cashback_tables", "article_title")
    op.drop_column("cashback_tables", "article_image_url")
    op.drop_column("cashback_tables", "article_nm_id")


def downgrade() -> None:
    """Downgrade schema."""
    # Восстанавливаем старые поля в cashback_tables
    op.add_column("cashback_tables", sa.Column("article_nm_id", sa.Integer(), nullable=True))
    op.add_column("cashback_tables", sa.Column("article_image_url", sa.String(), nullable=True))
    op.add_column("cashback_tables", sa.Column("article_title", sa.String(), nullable=True))
    op.add_column("cashback_tables", sa.Column("brand_name", sa.String(), nullable=True))
    op.add_column("cashback_tables", sa.Column("instruction_text", sa.Text(), nullable=True))
