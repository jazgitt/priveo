"""Which catalogue add-on a booking is for, so several add-ons can be sold."""
import sqlalchemy as sa
from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("addon_bookings", sa.Column(
        "addon_code", sa.String(16), nullable=False, server_default=""))
    op.add_column("addon_bookings", sa.Column(
        "addon_name", sa.String(80), nullable=False, server_default=""))


def downgrade():
    op.drop_column("addon_bookings", "addon_name")
    op.drop_column("addon_bookings", "addon_code")
