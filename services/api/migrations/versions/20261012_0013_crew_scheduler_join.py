"""Crew joined to the scheduler: per-weekday hours on `scheduling_crew`, and a
`scheduling_crew` row for every existing crew member.

Revision ID: 0013
Revises: 0010
"""
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0010"
branch_labels = None
depends_on = None


def _minutes(text: str) -> int:
    hour, minute = text.split(":")
    return int(hour) * 60 + int(minute)


def _summary(hours: list) -> tuple[int, int]:
    working = [h for h in hours if h.get("working")]
    if not working:
        return 0, 0
    return (min(_minutes(h["start"]) for h in working),
            max(_minutes(h["end"]) for h in working))


def upgrade() -> None:
    op.add_column("scheduling_crew", sa.Column("working_hours", sa.JSON()))

    bind = op.get_bind()
    members = sa.table(
        "crew_members",
        sa.column("login_id", sa.Uuid), sa.column("society_id", sa.Uuid),
        sa.column("role", sa.String), sa.column("working_hours", sa.JSON))
    logins = sa.table("logins", sa.column("id", sa.Uuid), sa.column("active", sa.Boolean))
    crew = sa.table(
        "scheduling_crew",
        sa.column("id", sa.Uuid), sa.column("login_id", sa.Uuid),
        sa.column("society_id", sa.Uuid), sa.column("role", sa.String),
        sa.column("start_minute", sa.Integer), sa.column("end_minute", sa.Integer),
        sa.column("working_hours", sa.JSON), sa.column("active", sa.Boolean))

    existing = {row.login_id: row.id for row in bind.execute(
        sa.select(crew.c.login_id, crew.c.id))}
    rows = bind.execute(
        sa.select(members.c.login_id, members.c.society_id, members.c.role,
                  members.c.working_hours, logins.c.active)
        .join(logins, logins.c.id == members.c.login_id)).all()
    for login_id, society_id, role, hours, active in rows:
        start, end = _summary(hours or [])
        if login_id in existing:
            # The directory is the source of the hours, the role and the society.
            bind.execute(crew.update().where(crew.c.id == existing[login_id]).values(
                society_id=society_id, role=role, start_minute=start, end_minute=end,
                working_hours=hours, active=active))
        else:
            bind.execute(crew.insert().values(
                id=uuid.uuid4(), login_id=login_id, society_id=society_id, role=role,
                start_minute=start, end_minute=end, working_hours=hours, active=active))


def downgrade() -> None:
    op.drop_column("scheduling_crew", "working_hours")
