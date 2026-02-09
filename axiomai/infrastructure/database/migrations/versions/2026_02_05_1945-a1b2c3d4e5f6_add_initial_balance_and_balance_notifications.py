"""add initial_balance to cabinets and balance_notifications table

Revision ID: a1b2c3d4e5f6
Revises: 4a7805eae24d
Create Date: 2026-02-05 19:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "141fa016b430"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "cabinets",
        sa.Column(
            "initial_balance",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Баланс после последнего пополнения (для расчёта порогов уведомлений)",
        ),
    )

    op.create_table(
        "balance_notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cabinet_id", sa.Integer(), nullable=False),
        sa.Column("initial_balance", sa.Integer(), nullable=False, comment="Баланс на момент пополнения"),
        sa.Column(
            "threshold",
            sa.Numeric(precision=3, scale=2),
            nullable=False,
            comment="Порог уведомления (0.50, 0.10, 0.01)",
        ),
        sa.Column(
            "sent_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Время отправки уведомления",
        ),
        sa.ForeignKeyConstraint(
            ["cabinet_id"], ["cabinets.id"], name=op.f("fk_balance_notifications_cabinet_id_cabinets")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_balance_notifications")),
    )
    op.create_index(op.f("ix_balance_notifications_cabinet_id"), "balance_notifications", ["cabinet_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_balance_notifications_cabinet_id"), table_name="balance_notifications")
    op.drop_table("balance_notifications")
    op.drop_column("cabinets", "initial_balance")
