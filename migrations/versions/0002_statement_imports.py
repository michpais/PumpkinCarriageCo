"""Minimized, immutable monthly statement source facts; no demo data conversion."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "statement_imports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shop_id", sa.String(100), sa.ForeignKey("shops.id"), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("source_name", sa.String(80), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("parser_version", sa.String(40), nullable=False),
        sa.Column("classification_version", sa.String(40), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("retain_through", sa.Date(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("validation_json", sa.String(), nullable=False),
        sa.UniqueConstraint("shop_id", "period", name="uq_statement_month"),
        sa.UniqueConstraint("shop_id", "file_hash", name="uq_statement_file"),
        sa.CheckConstraint("currency = 'USD'", name="ck_statement_currency"),
    )
    op.create_index("ix_statement_imports_shop_id", "statement_imports", ["shop_id"])
    op.create_table(
        "statement_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("import_id", sa.Integer(), sa.ForeignKey("statement_imports.id"), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("occurrence", sa.Integer(), nullable=False),
        sa.Column("activity_date", sa.Date(), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        *[
            sa.Column(name, sa.String(40), nullable=False)
            for name in ("amount_text", "fees_text", "net_text")
        ],
        *[
            sa.Column(name, sa.Integer(), nullable=True)
            for name in ("amount_minor", "fees_minor", "net_minor", "deposit_minor")
        ],
        sa.UniqueConstraint("import_id", "source_row", name="uq_statement_source_row"),
        sa.UniqueConstraint(
            "import_id", "fingerprint", "occurrence", name="uq_statement_occurrence"
        ),
        sa.CheckConstraint("source_row >= 2 AND occurrence >= 1", name="ck_statement_row"),
        sa.CheckConstraint(
            "category IN ('sale','refund','fee','shipping','tax','deposit',"
            "'funding','marketing','buyer_fee','unclassified')",
            name="ck_statement_category",
        ),
    )
    op.create_index("ix_statement_entries_import_id", "statement_entries", ["import_id"])
    op.create_table(
        "statement_references",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entry_id", sa.Integer(), sa.ForeignKey("statement_entries.id"), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("source_id", sa.String(30), nullable=False),
        sa.UniqueConstraint("entry_id", "kind", "source_id", name="uq_statement_reference"),
        sa.CheckConstraint(
            "kind IN ('order','listing','label')", name="ck_statement_reference_kind"
        ),
    )
    op.create_index("ix_statement_references_entry_id", "statement_references", ["entry_id"])


def downgrade() -> None:
    op.drop_table("statement_references")
    op.drop_table("statement_entries")
    op.drop_table("statement_imports")
