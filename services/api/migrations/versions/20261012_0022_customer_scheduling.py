"""Vehicle societies, account metadata, pending plans and separate add-on visits."""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("customers") as b:
        b.add_column(sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        "UPDATE customers SET email_verified_at = (SELECT MAX(verified_at) FROM email_codes "
        "WHERE email_codes.login_id = customers.login_id)"
    )
    with op.batch_alter_table("vehicles") as b:
        b.add_column(sa.Column("society_id", sa.Uuid(), nullable=True))
        b.add_column(sa.Column("photo_upload_id", sa.Uuid(), nullable=True))
        b.add_column(sa.Column("rc_upload_id", sa.Uuid(), nullable=True))
        b.add_column(sa.Column("rc_verified", sa.Boolean(), nullable=False, server_default="0"))
        b.create_foreign_key("fk_vehicle_society", "societies", ["society_id"], ["id"])
        b.create_foreign_key("fk_vehicle_photo", "media_uploads", ["photo_upload_id"], ["id"])
        b.create_foreign_key("fk_vehicle_rc", "media_uploads", ["rc_upload_id"], ["id"])
        b.create_index("ix_vehicles_society_id", ["society_id"])
    op.execute(
        "UPDATE vehicles SET society_id = "
        "(SELECT society_id FROM customers WHERE customers.id = vehicles.customer_id)"
    )
    with op.batch_alter_table("subscriptions") as b:
        b.add_column(sa.Column("pending_plan_id", sa.Uuid(), nullable=True))
        b.add_column(sa.Column("pending_from", sa.Date(), nullable=True))
        b.create_foreign_key("fk_subscription_pending_plan", "plans", ["pending_plan_id"], ["id"])
    with op.batch_alter_table("auth_sessions") as b:
        for name, size in (("device_name", 120), ("platform", 20), ("app_version", 40)):
            b.add_column(sa.Column(name, sa.String(size), nullable=False, server_default=""))
    with op.batch_alter_table("addon_bookings") as b:
        b.add_column(sa.Column("requested_date", sa.Date(), nullable=True))
        b.add_column(sa.Column("requested_finish_by", sa.Time(), nullable=True))
    naming = {"uq": "uq_%(table_name)s_%(column_0_name)s"}
    old_unique = next(
        c["name"]
        for c in sa.inspect(op.get_bind()).get_unique_constraints("visits")
        if c["column_names"] == ["schedule_id", "vehicle_id", "date"]
    )
    with op.batch_alter_table("visits", naming_convention=naming) as b:
        b.add_column(sa.Column("addon_key", sa.String(64), nullable=False, server_default=""))
        b.drop_constraint(old_unique or "uq_visits_schedule_id", type_="unique")
        b.create_unique_constraint(
            "uq_visit_service", ["schedule_id", "vehicle_id", "date", "addon_key"]
        )
    with op.batch_alter_table("jobs") as b:
        b.add_column(sa.Column("addon_booking_id", sa.Uuid(), nullable=True))
        b.create_foreign_key("fk_job_booking", "addon_bookings", ["addon_booking_id"], ["id"])
        b.create_index("ix_jobs_addon_booking_id", ["addon_booking_id"])
    # Preserve legacy add-on job IDs and their proof while separating their visits.
    bind = op.get_bind()
    meta = sa.MetaData()
    jobs = sa.Table("jobs", meta, autoload_with=bind)
    visits = sa.Table("visits", meta, autoload_with=bind)
    for job in list(bind.execute(sa.select(jobs).where(jobs.c.addon_request_id.is_not(None)))):
        original = bind.execute(sa.select(visits).where(visits.c.id == job.visit_id)).one()
        key = f"legacy:{uuid.UUID(str(job.addon_request_id))}"
        if original.addon_key:
            continue
        others = list(
            bind.execute(sa.select(jobs).where(jobs.c.visit_id == original.id, jobs.c.id != job.id))
        )
        if not others:
            bind.execute(visits.update().where(visits.c.id == original.id).values(addon_key=key))
        else:
            new_uuid = uuid.uuid4()
            new_id = new_uuid.hex if bind.dialect.name == "sqlite" else new_uuid
            bind.execute(
                visits.insert().values(
                    id=new_id,
                    schedule_id=original.schedule_id,
                    vehicle_id=original.vehicle_id,
                    date=original.date,
                    addon_key=key,
                    status=job.status,
                )
            )
            bind.execute(jobs.update().where(jobs.c.id == job.id).values(visit_id=new_id))
            states = [j.status for j in others]
            state = (
                "Completed"
                if all(s in ("Completed", "Skipped") for s in states)
                else (
                    "Could not complete"
                    if "Could not complete" in states
                    else "In progress"
                    if "In progress" in states
                    else "Scheduled"
                )
            )
            bind.execute(visits.update().where(visits.c.id == original.id).values(status=state))


def downgrade():
    if (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT 1 FROM visits GROUP BY schedule_id, vehicle_id, date HAVING COUNT(*) > 1"
            )
        )
        .first()
    ):
        raise RuntimeError(
            "Cannot downgrade while separate add-on visits exist; retain the new schema."
        )
    with op.batch_alter_table("jobs") as b:
        b.drop_constraint("fk_job_booking", type_="foreignkey")
        b.drop_index("ix_jobs_addon_booking_id")
        b.drop_column("addon_booking_id")
    with op.batch_alter_table("visits") as b:
        b.drop_constraint("uq_visit_service", type_="unique")
        b.drop_column("addon_key")
        b.create_unique_constraint("uq_visits_schedule_id", ["schedule_id", "vehicle_id", "date"])
    with op.batch_alter_table("addon_bookings") as b:
        b.drop_column("requested_date")
        b.drop_column("requested_finish_by")
    with op.batch_alter_table("auth_sessions") as b:
        for name in ("device_name", "platform", "app_version"):
            b.drop_column(name)
    with op.batch_alter_table("subscriptions") as b:
        b.drop_constraint("fk_subscription_pending_plan", type_="foreignkey")
        b.drop_column("pending_plan_id")
        b.drop_column("pending_from")
    with op.batch_alter_table("vehicles") as b:
        for name in ("fk_vehicle_society", "fk_vehicle_photo", "fk_vehicle_rc"):
            b.drop_constraint(name, type_="foreignkey")
        b.drop_index("ix_vehicles_society_id")
        for name in ("society_id", "photo_upload_id", "rc_upload_id", "rc_verified"):
            b.drop_column(name)
    with op.batch_alter_table("customers") as b:
        b.drop_column("email_verified_at")
