"""Add the three missing check-in categories to existing databases (CHK-03).

Data only. A database that already has check-in categories got the first three
when it was seeded. This adds the other three owner categories and replaces the
first description where the admin has not edited it.

Revision ID: 0018
Revises: 0010
"""
import uuid

import sqlalchemy as sa
from alembic import op

from app.support.defaults import CHECKIN_CATEGORIES, OLD_CHECKIN_DESCRIPTIONS

revision = "0018"
down_revision = "0015"
branch_labels = None
depends_on = None

_KIND = "checkin_category"


def upgrade() -> None:
    bind = op.get_bind()
    table = sa.table(
        "support_options", sa.column("id", sa.Uuid), sa.column("kind", sa.String),
        sa.column("name", sa.String), sa.column("description", sa.String),
        sa.column("sort_order", sa.Integer), sa.column("active", sa.Boolean))
    rows = bind.execute(sa.select(table.c.name, table.c.description)
                        .where(table.c.kind == _KIND)).all()
    if not rows:
        return  # Not seeded yet: the service seeds all six on first use.
    existing = {name: description for name, description in rows}
    for order, (name, description) in enumerate(CHECKIN_CATEGORIES):
        if name not in existing:
            bind.execute(table.insert().values(
                id=uuid.uuid4(), kind=_KIND, name=name, description=description,
                sort_order=order, active=True))
        elif existing[name] == OLD_CHECKIN_DESCRIPTIONS.get(name):
            bind.execute(table.update()
                         .where(table.c.kind == _KIND, table.c.name == name)
                         .values(description=description))


def downgrade() -> None:
    """Data only: nothing to undo."""
