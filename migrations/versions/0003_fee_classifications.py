"""Add versioned fee annotations without modifying accepted financial records."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "statement_fee_classifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entry_id", sa.Integer(), sa.ForeignKey("statement_entries.id"), nullable=False),
        sa.Column("subtype", sa.String(30), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("entry_id", "version", name="uq_statement_fee_version"),
        sa.CheckConstraint(
            "subtype IN ('listing','processing','transaction_item',"
            "'transaction_shipping','shop_setup','unclassified')",
            name="ck_statement_fee_subtype",
        ),
    )
    op.create_index(
        "ix_statement_fee_classifications_entry_id", "statement_fee_classifications", ["entry_id"]
    )


def downgrade() -> None:
    op.drop_table("statement_fee_classifications")
