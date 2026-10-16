"""A unique, readable ID for each plan (PLN-0001) and add-on (ADN-0001).

Existing rows get sequential IDs in their list order. Subscriptions and add-on
bookings already point at plans and add-ons by their internal ID, so nothing
else needs relinking.
"""
import sqlalchemy as sa
from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None

_TABLES = (("plans", "PLN", "uq_plans_code"), ("addon_catalogue", "ADN", "uq_addon_catalogue_code"))


def upgrade():
    db = op.get_bind()
    for table, prefix, constraint in _TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("code", sa.String(16), nullable=True))
        t = sa.Table(table, sa.MetaData(), autoload_with=db)
        rows = db.execute(sa.select(t.c.id).order_by(t.c.sort_order, t.c.name)).all()
        for n, (row_id,) in enumerate(rows, start=1):
            db.execute(t.update().where(t.c.id == row_id).values(code=f"{prefix}-{n:04d}"))
        with op.batch_alter_table(table) as batch:
            batch.alter_column("code", existing_type=sa.String(16), nullable=False)
            batch.create_unique_constraint(constraint, ["code"])


def downgrade():
    for table, _prefix, constraint in reversed(_TABLES):
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(constraint, type_="unique")
            batch.drop_column("code")
