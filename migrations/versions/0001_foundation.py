"""Initial synthetic demo schema. Deliberately independent of mutable ORM metadata."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shops",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("timezone", sa.String(100), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
    )
    op.create_table(
        "demo_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shop_id", sa.String(100), sa.ForeignKey("shops.id"), nullable=False),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("ordered_at", sa.DateTime(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        *[
            sa.Column(name, sa.Integer(), nullable=False)
            for name in (
                "units",
                "item_sales_minor",
                "refunds_minor",
                "shipping_income_minor",
                "fees_minor",
                "postage_minor",
                "cogs_minor",
            )
        ],
        sa.UniqueConstraint("shop_id", "source_id", name="uq_demo_order_source"),
        sa.CheckConstraint("currency = 'USD'", name="ck_demo_currency"),
        sa.CheckConstraint("source = 'synthetic'", name="ck_demo_source"),
        sa.CheckConstraint("units > 0", name="ck_demo_units"),
        sa.CheckConstraint(
            "item_sales_minor >= 0 AND refunds_minor >= 0 AND shipping_income_minor >= 0 "
            "AND fees_minor >= 0 AND postage_minor >= 0 AND cogs_minor >= 0",
            name="ck_demo_amounts",
        ),
    )
    op.create_index("ix_demo_orders_shop_id", "demo_orders", ["shop_id"])
    op.create_index("ix_demo_orders_ordered_at", "demo_orders", ["ordered_at"])


def downgrade() -> None:
    op.drop_index("ix_demo_orders_ordered_at", table_name="demo_orders")
    op.drop_index("ix_demo_orders_shop_id", table_name="demo_orders")
    op.drop_table("demo_orders")
    op.drop_table("shops")
