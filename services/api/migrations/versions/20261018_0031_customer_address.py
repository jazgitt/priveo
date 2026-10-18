"""A customer's optional address lines, shown on the admin Account details tab."""
import sqlalchemy as sa
from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade():
    for name in ("address_line1", "address_line2"):
        op.add_column(
            "customers", sa.Column(name, sa.String(120), nullable=False, server_default="")
        )


def downgrade():
    for name in ("address_line2", "address_line1"):
        op.drop_column("customers", name)
