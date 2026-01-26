"""update articles columns

Revision ID: 4e60c8539d34
Revises: 1a075811dab8
Create Date: 2026-01-26 22:38:49.968460

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4e60c8539d34"
down_revision: str | Sequence[str] | None = "1a075811dab8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("articles", sa.Column("image_url", sa.String(), nullable=False))
    op.add_column("articles", sa.Column("brand_name", sa.String(), nullable=False))
    op.add_column("articles", sa.Column("instruction_text", sa.String(), nullable=False))
    op.alter_column("articles", "article", new_column_name="nm_id")
    op.alter_column("articles", "nm_id_name", new_column_name="title")
    op.drop_column("articles", "photo_file_id")


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("articles", "nm_id", new_column_name="article")
    op.alter_column("articles", "title", new_column_name="nm_id_name")
    op.add_column("articles", sa.Column("photo_file_id", sa.VARCHAR(length=256), autoincrement=False, nullable=True))
    op.drop_column("articles", "instruction_text")
    op.drop_column("articles", "brand_name")
    op.drop_column("articles", "image_url")
    op.drop_column("articles", "title")
    op.drop_column("articles", "nm_id")
