"""update enum to non native, actualization comments

Revision ID: dbccd4e11e05
Revises: 23d1363dc937
Create Date: 2026-01-19 13:14:47.810656
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "dbccd4e11e05"
down_revision: str | Sequence[str] | None = "23d1363dc937"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "cabinets",
        "nm_id_name",
        existing_type=sa.VARCHAR(length=128),
        comment="Артикул",
        existing_comment="Название ИП / магазина, вводимое пользователем",
        existing_nullable=False,
    )
    op.alter_column(
        "cabinets",
        "organization_name",
        existing_type=sa.VARCHAR(length=128),
        comment="Название магазина/бренда на вб",
        existing_comment="Название ИП / магазина, вводимое пользователем",
        existing_nullable=False,
    )
    op.alter_column(
        "cabinets",
        "leads_balance",
        existing_type=sa.INTEGER(),
        comment="Текущий баланс лидов по кабинету",
        existing_nullable=False,
        existing_server_default=sa.text("0"),
    )
    op.alter_column(
        "cashback_tables",
        "status",
        existing_type=postgresql.ENUM("NEW", "PAID", "DISABLED", "EXPIRED", name="cashback_table_status"),
        type_=sa.Enum("NEW", "PAID", "DISABLED", "EXPIRED", name="cashbacktablestatus", native_enum=False),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "cashback_tables",
        "status",
        existing_type=sa.Enum("NEW", "PAID", "DISABLED", "EXPIRED", name="cashbacktablestatus", native_enum=False),
        type_=postgresql.ENUM("NEW", "PAID", "DISABLED", "EXPIRED", name="cashback_table_status"),
        existing_nullable=False,
    )
    op.alter_column(
        "cabinets",
        "leads_balance",
        existing_type=sa.INTEGER(),
        comment=None,
        existing_comment="Текущий баланс лидов по кабинету",
        existing_nullable=False,
        existing_server_default=sa.text("0"),
    )
    op.alter_column(
        "cabinets",
        "organization_name",
        existing_type=sa.VARCHAR(length=128),
        comment="Название ИП / магазина, вводимое пользователем",
        existing_comment="Название магазина/бренда на вб",
        existing_nullable=False,
    )
    op.alter_column(
        "cabinets",
        "nm_id_name",
        existing_type=sa.VARCHAR(length=128),
        comment="Название ИП / магазина, вводимое пользователем",
        existing_comment="Артикул",
        existing_nullable=False,
    )
