"""Reference data: society basements, plan inclusions, vehicle catalogue,
services, working slots, checklists, reasons, settings, add-on catalogue, audit.

Revision ID: 0011
Revises: 0010
"""
import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def _id() -> sa.Column:
    return sa.Column("id", sa.Uuid, primary_key=True)


def upgrade() -> None:
    with op.batch_alter_table("societies") as batch:
        batch.add_column(sa.Column(
            "parking_basements", sa.JSON, nullable=False,
            server_default=sa.text("""'["B1", "B2", "B3", "B4"]'""")))
    with op.batch_alter_table("plans") as batch:
        batch.add_column(sa.Column("inclusions", sa.JSON, nullable=False,
                                   server_default=sa.text("'[]'")))
        batch.add_column(sa.Column("badge", sa.String(40), nullable=False,
                                   server_default=""))
        batch.add_column(sa.Column("sort_order", sa.Integer, nullable=False,
                                   server_default="0"))

    op.create_table(
        "vehicle_catalogue", _id(),
        sa.Column("make", sa.String(60), nullable=False),
        sa.Column("model", sa.String(80), nullable=False),
        sa.Column("variant", sa.String(80), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("active", sa.Boolean, nullable=False))
    op.create_index("ix_vehicle_catalogue_make", "vehicle_catalogue", ["make"])

    op.create_table(
        "directory_services", _id(),
        sa.Column("name", sa.String(24), nullable=False, unique=True),
        sa.Column("duration_minutes", sa.Integer, nullable=False),
        sa.Column("min_photos", sa.Integer, nullable=False),
        sa.Column("min_videos", sa.Integer, nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False))

    op.create_table(
        "working_slots", _id(),
        sa.Column("society_id", sa.Uuid, sa.ForeignKey("societies.id"), nullable=False),
        sa.Column("service", sa.String(24), nullable=False),
        sa.Column("start_minute", sa.Integer, nullable=False),
        sa.Column("end_minute", sa.Integer, nullable=False),
        sa.Column("days", sa.JSON, nullable=False))
    op.create_index("ix_working_slots_society_id", "working_slots", ["society_id"])

    op.create_table(
        "checklist_items", _id(),
        sa.Column("service", sa.String(24), nullable=False),
        sa.Column("key", sa.String(40), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False))
    op.create_index("ix_checklist_items_service", "checklist_items", ["service"])

    op.create_table(
        "cnc_reasons", _id(),
        sa.Column("key", sa.String(40), nullable=False, unique=True),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False))

    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(60), primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.Uuid, sa.ForeignKey("logins.id")))

    op.create_table(
        "addon_catalogue", _id(),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("service", sa.String(24), nullable=False),
        sa.Column("price_rupees", sa.Integer, nullable=False),
        sa.Column("list_price_rupees", sa.Integer),
        sa.Column("duration_minutes", sa.Integer, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False))

    op.create_table(
        "directory_audit", _id(),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("admin_login_id", sa.Uuid, sa.ForeignKey("logins.id")),
        sa.Column("entity", sa.String(24), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("detail", sa.JSON, nullable=False))
    op.create_index("ix_directory_audit_at", "directory_audit", ["at"])
    op.create_index("ix_directory_audit_entity", "directory_audit", ["entity"])


def downgrade() -> None:
    for table in ("directory_audit", "addon_catalogue", "system_settings", "cnc_reasons",
                  "checklist_items", "working_slots", "directory_services",
                  "vehicle_catalogue"):
        op.drop_table(table)
    with op.batch_alter_table("plans") as batch:
        batch.drop_column("sort_order")
        batch.drop_column("badge")
        batch.drop_column("inclusions")
    with op.batch_alter_table("societies") as batch:
        batch.drop_column("parking_basements")
