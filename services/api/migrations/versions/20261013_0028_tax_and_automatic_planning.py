"""Immutable GST snapshots, automatic draft run ledger and approved samples."""
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("invoices") as batch:
        batch.add_column(sa.Column("tax_details", sa.JSON(), nullable=True))
    op.create_table("automatic_planning_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("society_id", sa.Uuid(), sa.ForeignKey("societies.id"), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("schedule_id", sa.Uuid(), sa.ForeignKey("schedules.id")),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error", sa.String(160), nullable=False),
        sa.UniqueConstraint("society_id", "start_date", name="auto_planning_once"))
    # Update only untouched old samples. Issued job snapshots and admin edits survive.
    db = op.get_bind()
    items = sa.Table("checklist_items", sa.MetaData(), autoload_with=db)
    internal = list(db.execute(sa.select(items).where(items.c.service == "Cleaning-Internal")
                             .order_by(items.c.sort_order)).mappings())
    original_internal = [("seats", "Seats and mats vacuumed"), ("dashboard", "Dashboard and panels wiped"),
                         ("glass", "Interior glass cleaned"), ("inspection", "Final inspection completed")]
    if [(r["key"], r["label"]) for r in internal] == original_internal and all(
        r["active"] and r["sort_order"] == i for i, r in enumerate(internal)):
        db.execute(items.update().where(items.c.id == internal[-1]["id"]).values(sort_order=4))
        item_id = uuid.uuid4()
        db.execute(items.insert().values(id=item_id.hex if db.dialect.name == "sqlite" else item_id,
            service="Cleaning-Internal", key="touchpoints",
            label="Door handles and touchpoints cleaned", sort_order=3, active=True))
    spa = list(db.execute(sa.select(items).where(items.c.service == "Deep Spa")
                         .order_by(items.c.sort_order)).mappings())
    original_spa = [("body", "Exterior body cleaned"), ("vacuum", "Interior vacuumed"),
        ("dashboard", "Dashboard and panels wiped"), ("glass", "Glass cleaned"),
        ("wheels", "Wheels cleaned"), ("inspection", "Final inspection completed")]
    if [(r["key"], r["label"]) for r in spa] == original_spa and all(
        r["active"] and r["sort_order"] == i for i, r in enumerate(spa)):
        db.execute(items.update().where(items.c.id == spa[3]["id"]).values(label="Glass and wheels cleaned"))
        db.execute(items.update().where(items.c.id == spa[4]["id"]).values(active=False))
        db.execute(items.update().where(items.c.id == spa[5]["id"]).values(sort_order=4))


def downgrade():
    db = op.get_bind()
    if db.scalar(sa.text("SELECT count(*) FROM automatic_planning_runs")) or db.scalar(
        sa.text("SELECT count(*) FROM invoices WHERE tax_details IS NOT NULL")):
        raise RuntimeError("Cannot discard automatic run history or issued GST snapshots.")
    op.drop_table("automatic_planning_runs")
    with op.batch_alter_table("invoices") as batch:
        batch.drop_column("tax_details")
    # Sample edits are deliberately not reversed; that would erase later admin changes.
