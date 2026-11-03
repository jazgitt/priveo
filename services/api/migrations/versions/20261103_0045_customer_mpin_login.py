"""Customers sign in with their mobile number and an MPIN.

The same mobile number can be a customer and a crew member, so a login is
unique by role and login ID. `must_change_mpin` marks a customer who still has
the MPIN the admin gave. Existing customers are moved to the new sign-in by
`scripts/convert_customer_logins.py`, run by hand, never by this migration.

Revision ID: 0045
Revises: 0044
"""
import sqlalchemy as sa
from alembic import op

revision = "0045"
down_revision = "0044"
branch_labels = None
depends_on = None

NAMING = {"uq": "uq_%(table_name)s_%(column_0_name)s"}


def upgrade() -> None:
    old_unique = next(
        (c["name"] for c in sa.inspect(op.get_bind()).get_unique_constraints("logins")
         if c["column_names"] == ["login_id"]),
        None,
    )
    with op.batch_alter_table("logins", naming_convention=NAMING) as b:
        b.add_column(sa.Column("must_change_mpin", sa.Boolean(), nullable=False,
                               server_default=sa.false()))
        b.drop_constraint(old_unique or "uq_logins_login_id", type_="unique")
        b.create_unique_constraint("uq_logins_role_login_id", ["role", "login_id"])


def downgrade() -> None:
    with op.batch_alter_table("logins", naming_convention=NAMING) as b:
        b.drop_constraint("uq_logins_role_login_id", type_="unique")
        b.create_unique_constraint("uq_logins_login_id", ["login_id"])
        b.drop_column("must_change_mpin")
