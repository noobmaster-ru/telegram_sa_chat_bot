"""update superbanking_payout model

Revision ID: 1a003e315edf
Revises: 349d75644594
Create Date: 2026-02-16 11:14:13.670881

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1a003e315edf"
down_revision: str | Sequence[str] | None = "349d75644594"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("superbanking", sa.Column("telegram_id", sa.Integer(), nullable=True, comment="Telegram ID пользователя"))
    op.add_column("superbanking", sa.Column("nm_ids", sa.ARRAY(sa.Integer()), nullable=True, comment="Список артикулов товаров"))
    
    op.execute("""
        UPDATE superbanking s
        SET telegram_id = b.telegram_id,
            nm_ids = ARRAY[s.nm_id]
        FROM buyers b
        WHERE s.buyer_id = b.id
    """)
    
    op.alter_column("superbanking", "telegram_id", nullable=False)
    op.alter_column("superbanking", "nm_ids", nullable=False)
    
    op.drop_index(op.f("ix_superbanking_buyer_id"), table_name="superbanking")
    op.drop_index(op.f("ix_superbanking_order_number"), table_name="superbanking")
    op.create_unique_constraint(op.f("uq_superbanking_order_number"), "superbanking", ["order_number"])
    op.drop_constraint(op.f("fk_superbanking_buyer_id_buyers"), "superbanking", type_="foreignkey")
    op.drop_column("superbanking", "buyer_id")
    op.drop_column("superbanking", "nm_id")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("superbanking", sa.Column("nm_id", sa.INTEGER(), autoincrement=False, nullable=True, comment="Артикул товара"))
    op.add_column("superbanking", sa.Column("buyer_id", sa.INTEGER(), autoincrement=False, nullable=True))
    
    op.execute("""
        UPDATE superbanking s
        SET nm_id = s.nm_ids[1],
            buyer_id = b.id
        FROM buyers b
        WHERE s.telegram_id = b.telegram_id
    """)
    
    op.alter_column("superbanking", "nm_id", nullable=False)
    op.alter_column("superbanking", "buyer_id", nullable=False)
    
    op.create_foreign_key(op.f("fk_superbanking_buyer_id_buyers"), "superbanking", "buyers", ["buyer_id"], ["id"])
    op.drop_constraint(op.f("uq_superbanking_order_number"), "superbanking", type_="unique")
    op.create_index(op.f("ix_superbanking_order_number"), "superbanking", ["order_number"], unique=True)
    op.create_index(op.f("ix_superbanking_buyer_id"), "superbanking", ["buyer_id"], unique=False)
    op.drop_column("superbanking", "nm_ids")
    op.drop_column("superbanking", "telegram_id")
