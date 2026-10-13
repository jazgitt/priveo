"""Retain the supplier details used when an invoice is issued."""
import sqlalchemy as sa
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("invoices") as batch:
        batch.add_column(sa.Column("seller_details", sa.JSON(), nullable=True))
    # Historical supplier details are unknown; do not backfill from today's settings.


def downgrade():
    if op.get_bind().scalar(sa.text(
        "SELECT COUNT(*) FROM invoices WHERE seller_details IS NOT NULL"
    )):
        raise RuntimeError("Invoice supplier snapshots exist; downgrade would discard them.")
    with op.batch_alter_table("invoices") as batch:
        batch.drop_column("seller_details")
