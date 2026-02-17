"""telegram_id value to BigInteger

Revision ID: e131fdd7ee2c
Revises: 1a003e315edf
Create Date: 2026-02-16 15:19:23.406517

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e131fdd7ee2c"
down_revision: str | Sequence[str] | None = "1a003e315edf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("superbanking", "telegram_id",
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_comment="Telegram ID пользователя",
               existing_nullable=False)
    op.alter_column("superbanking", "nm_ids",
               existing_type=postgresql.ARRAY(sa.INTEGER()),
               type_=sa.ARRAY(sa.BigInteger()),
               existing_comment="Список артикулов товаров",
               existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("superbanking", "nm_ids",
               existing_type=sa.ARRAY(sa.BigInteger()),
               type_=postgresql.ARRAY(sa.INTEGER()),
               existing_comment="Список артикулов товаров",
               existing_nullable=False)
    op.alter_column("superbanking", "telegram_id",
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_comment="Telegram ID пользователя",
               existing_nullable=False)
