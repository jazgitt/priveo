"""S-08: the add-ons 'Extra interior cleaning' and 'Special exterior cleaning'.

Data only. Each row is inserted only if no add-on has that name, so existing
rows and admin edits are never touched. The owner has not decided the prices:
both rows are inactive at price 0 until the admin prices and activates them.
"""
import re
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None

_ROWS = (
    ("Extra interior cleaning", "Cleaning-Internal", 10,
     "An extra interior clean, on top of your plan.\n"
     "Interior vacuum and wipe-down\nPhoto proof of the finished work"),
    ("Special exterior cleaning", "Cleaning-External", 20,
     "A special exterior clean, on top of your plan.\n"
     "Exterior wash and wipe-down\nPhoto proof of the finished work"),
)


def _table(db):
    # The id is declared here: SQLite reflects it as CHAR(32), PostgreSQL as UUID.
    return sa.Table(
        "addon_catalogue", sa.MetaData(), sa.Column("id", sa.Uuid, primary_key=True), autoload_with=db,
        extend_existing=True)


def upgrade():
    db = op.get_bind()
    t = _table(db)
    rows = db.execute(sa.select(t.c.name, t.c.code)).all()
    if not rows:
        return  # A fresh database: the start-up seed adds all the add-ons, Deep Spa first.
    names = {n.lower() for n, _ in rows}
    highest = max(
        (int(m.group(1)) for _, c in rows if (m := re.fullmatch(r"ADN-(\d+)", c or ""))),
        default=0)
    for name, service, order, description in _ROWS:
        if name.lower() in names:
            continue
        highest += 1
        db.execute(t.insert().values(
            id=uuid.uuid4(), code=f"ADN-{highest:04d}", name=name,
            description=description, service=service, price_rupees=0,
            list_price_rupees=None, duration_minutes=20, active=False,
            sort_order=order))


def downgrade():
    """Removes the two rows only while unused and still the seeded ones."""
    db = op.get_bind()
    t = _table(db)
    used = sa.Table("addon_bookings", sa.MetaData(), autoload_with=db) \
        if sa.inspect(db).has_table("addon_bookings") else None
    for name, *_ in _ROWS:
        if used is not None and db.execute(
                sa.select(used.c.id).where(used.c.addon_name == name).limit(1)).first():
            continue
        db.execute(t.delete().where(t.c.name == name, t.c.price_rupees == 0))
