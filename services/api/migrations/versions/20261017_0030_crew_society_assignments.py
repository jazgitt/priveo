"""A crew member's society becomes a dated record (ADM-CRW-13, ADM-CRW-22).

Every existing crew member gets one assignment: their current society from the
day they were onboarded. Later moves are added as new rows, so the past never
changes.
"""
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "crew_society_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("crew_id", sa.Uuid(), sa.ForeignKey("crew_members.id"), nullable=False),
        sa.Column("society_id", sa.Uuid(), sa.ForeignKey("societies.id"), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("paired_member_id", sa.Uuid(), sa.ForeignKey("crew_members.id")),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("logins.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("crew_id", "effective_from", name="uq_crew_society_from"),
    )
    op.create_index("ix_crew_society_assignments_crew_id", "crew_society_assignments", ["crew_id"])
    db = op.get_bind()
    crew = sa.Table("crew_members", sa.MetaData(), autoload_with=db)
    assignments = sa.Table("crew_society_assignments", sa.MetaData(), autoload_with=db)
    rows = db.execute(sa.select(crew.c.id, crew.c.society_id, crew.c.created_at)).all()
    for crew_id, society_id, created_at in rows:
        db.execute(assignments.insert().values(
            id=uuid.uuid4(), crew_id=crew_id, society_id=society_id,
            effective_from=created_at.date(), created_at=created_at))


def downgrade():
    op.drop_index("ix_crew_society_assignments_crew_id", table_name="crew_society_assignments")
    op.drop_table("crew_society_assignments")
