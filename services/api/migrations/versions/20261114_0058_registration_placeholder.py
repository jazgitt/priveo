"""A vehicle registration of 0000 may repeat (ONB-10). 0000 means the real number is not
known yet. Every other registration stays unique, now by a partial unique index.

Revision ID: 0058
Revises: 0057
"""
import sqlalchemy as sa
from alembic import op

revision = "0058"
down_revision = "0057"
branch_labels = None
depends_on = None

_WHERE = sa.text("registration <> '0000'")


def upgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        # The inline unique constraint has no name there, so the batch gives it one to drop.
        with op.batch_alter_table(
            "vehicles", naming_convention={"uq": "uq_%(table_name)s_%(column_0_name)s"}
        ) as batch:
            batch.drop_constraint("uq_vehicles_registration", type_="unique")
    else:
        op.drop_constraint("vehicles_registration_key", "vehicles", type_="unique")
    op.create_index("ux_vehicles_registration", "vehicles", ["registration"], unique=True,
                    postgresql_where=_WHERE, sqlite_where=_WHERE)


def downgrade() -> None:
    # Fails while two vehicles share 0000. Give them their real numbers first.
    op.drop_index("ux_vehicles_registration", table_name="vehicles")
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("vehicles") as batch:
            batch.create_unique_constraint("uq_vehicles_registration", ["registration"])
    else:
        op.create_unique_constraint("vehicles_registration_key", "vehicles", ["registration"])
