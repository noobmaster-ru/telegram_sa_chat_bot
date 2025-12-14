"""add live config columns to cashback_tables

Revision ID: 23d1363dc937
Revises: 139329c632be
Create Date: 2025-12-09 10:46:55.132343

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '23d1363dc937'
down_revision: Union[str, Sequence[str], None] = '139329c632be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add live config columns to cashback_tables."""
    op.add_column(
        "cashback_tables",
        sa.Column("article_nm_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "cashback_tables",
        sa.Column("article_image_url", sa.String(), nullable=True),
    )
    op.add_column(
        "cashback_tables",
        sa.Column("article_title", sa.String(), nullable=True),
    )
    op.add_column(
        "cashback_tables",
        sa.Column("brand_name", sa.String(), nullable=True),
    )
    op.add_column(
        "cashback_tables",
        sa.Column("instruction_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "cashback_tables",
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
    )



def downgrade() -> None:
    """Downgrade schema: remove live config columns from cashback_tables."""
    # В обратном порядке, чтобы не было зависимостей
    op.drop_column("cashback_tables", "last_synced_at")
    op.drop_column("cashback_tables", "instruction_text")
    op.drop_column("cashback_tables", "brand_name")
    op.drop_column("cashback_tables", "article_title")
    op.drop_column("cashback_tables", "article_image_url")
    op.drop_column("cashback_tables", "article_nm_id")
