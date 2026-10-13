"""Pin issued checklist definitions; legacy labels use a documented fallback."""
import sqlalchemy as sa
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("jobs") as batch:
        batch.add_column(sa.Column("checklist_snapshot", sa.JSON(), nullable=True))
    bind = op.get_bind()
    jobs = sa.table("jobs", sa.column("id", sa.Uuid()), sa.column("service"),
                    sa.column("status"), sa.column("checklist_snapshot", sa.JSON()))
    definitions = sa.table("checklist_items", sa.column("service"), sa.column("key"),
                           sa.column("label"), sa.column("active"), sa.column("sort_order"))
    progress = sa.table("job_checklist_progress", sa.column("job_id", sa.Uuid()),
                        sa.column("item_key"))
    # Frozen literals: migration behavior must not change with future seed edits.
    fallback = {
        "Cleaning-External": [("body", "Exterior body cleaned"),
                              ("glass", "Glass cleaned"), ("wheels", "Wheels cleaned"),
                              ("tyres", "Tyres dressed"), ("inspection", "Final inspection completed")],
        "Cleaning-Internal": [("seats", "Seats and mats vacuumed"),
                              ("dashboard", "Dashboard and panels wiped"),
                              ("glass", "Interior glass cleaned"),
                              ("inspection", "Final inspection completed")],
        "Deep Spa": [("body", "Exterior body cleaned"), ("vacuum", "Interior vacuumed"),
                     ("dashboard", "Dashboard and panels wiped"), ("glass", "Glass cleaned"),
                     ("wheels", "Wheels cleaned"), ("inspection", "Final inspection completed")],
    }
    for job in bind.execute(sa.select(jobs.c.id, jobs.c.service, jobs.c.status)).all():
        rows = bind.execute(sa.select(definitions).where(
            definitions.c.service == job.service).order_by(
                definitions.c.sort_order, definitions.c.key)).all()
        labels = {r.key: r.label for r in rows}
        ticks = list(bind.scalars(sa.select(progress.c.item_key).where(
            progress.c.job_id == job.id)))
        active = [(r.key, r.label) for r in rows if r.active] if rows else fallback.get(job.service, [])
        if job.status == "Completed" and ticks:
            # Don't introduce today's newly added items into an old completed job.
            ordered = [k for k, _ in active if k in ticks]
            ordered += sorted(set(ticks) - set(ordered))
            items = [{"key": k, "label": labels.get(k, dict(fallback.get(job.service, [])).get(k, k))}
                     for k in ordered]
        else:
            items = [{"key": k, "label": label} for k, label in active]
            items += [{"key": k, "label": labels.get(k, k)}
                      for k in sorted(set(ticks) - {i["key"] for i in items})]
        bind.execute(jobs.update().where(jobs.c.id == job.id).values(
            checklist_snapshot={"legacy": True, "items": items}))


def downgrade():
    if op.get_bind().scalar(sa.text(
        "SELECT COUNT(*) FROM jobs WHERE checklist_snapshot IS NOT NULL"
    )):
        raise RuntimeError("Issued checklist snapshots exist; downgrade would discard history.")
    with op.batch_alter_table("jobs") as batch:
        batch.drop_column("checklist_snapshot")
