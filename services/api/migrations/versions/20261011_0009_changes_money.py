"""Changes and money: schedule changes, payments, invoices, alerts, add-on requests.

Revision ID: 0009
Revises: 0004
"""
import sqlalchemy as sa
from alembic import op

revision = "0009"
# The chain is re-made when the slices are merged.
down_revision = "0004"
branch_labels = None
depends_on = None


def _id():
    return sa.Column("id", sa.Uuid, primary_key=True)


def _ts(name, nullable=True):
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable)


def upgrade() -> None:
    op.create_table(
        "schedule_changes", _id(),
        sa.Column("customer_id", sa.Uuid, sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("vehicle_id", sa.Uuid, sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("cutoff_time", sa.Time),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("actor", sa.String(8), nullable=False),
        sa.Column("actor_login_id", sa.Uuid, sa.ForeignKey("logins.id")),
        sa.Column("idempotency_key", sa.String(64), unique=True),
        _ts("created_at", False), _ts("ended_at"))
    op.create_index("ix_schedule_changes_customer_id", "schedule_changes", ["customer_id"])
    op.create_index("ix_schedule_changes_vehicle_id", "schedule_changes", ["vehicle_id"])

    op.create_table(
        "payments", _id(),
        sa.Column("customer_id", sa.Uuid, sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("vehicle_id", sa.Uuid, sa.ForeignKey("vehicles.id")),
        sa.Column("subscription_id", sa.Uuid, sa.ForeignKey("subscriptions.id")),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("description", sa.String(120), nullable=False),
        sa.Column("amount_rupees", sa.Integer, nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("cycle_start", sa.Date),
        sa.Column("cycle_end", sa.Date),
        sa.Column("overdue_since", sa.Date),
        _ts("initiated_at"), _ts("received_at"),
        sa.Column("confirmed_by", sa.Uuid, sa.ForeignKey("logins.id")),
        _ts("voided_at"), _ts("created_at", False),
        sa.UniqueConstraint("subscription_id", "cycle_start", name="payments_cycle_unique"))
    op.create_index("ix_payments_customer_id", "payments", ["customer_id"])
    op.create_index("ix_payments_vehicle_id", "payments", ["vehicle_id"])

    op.create_table(
        "payment_events", _id(),
        sa.Column("payment_id", sa.Uuid, sa.ForeignKey("payments.id"), nullable=False),
        sa.Column("from_status", sa.String(10)),
        sa.Column("to_status", sa.String(10), nullable=False),
        sa.Column("by_login_id", sa.Uuid, sa.ForeignKey("logins.id")),
        _ts("at", False),
        sa.Column("note", sa.String(200), nullable=False))
    op.create_index("ix_payment_events_payment_id", "payment_events", ["payment_id"])

    op.create_table(
        "invoices", _id(),
        sa.Column("payment_id", sa.Uuid, sa.ForeignKey("payments.id"), nullable=False,
                  unique=True),
        sa.Column("number", sa.String(24), nullable=False, unique=True),
        _ts("issued_at", False),
        sa.Column("issued_by", sa.Uuid, sa.ForeignKey("logins.id")),
        sa.Column("amount_rupees", sa.Integer, nullable=False),
        sa.Column("customer_name", sa.String(160), nullable=False),
        sa.Column("vehicle_label", sa.String(120), nullable=False),
        sa.Column("description", sa.String(120), nullable=False))

    op.create_table(
        "money_alerts", _id(),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("payment_id", sa.Uuid, sa.ForeignKey("payments.id")),
        sa.Column("subscription_id", sa.Uuid, sa.ForeignKey("subscriptions.id")),
        _ts("created_at", False), _ts("read_at"))

    op.create_table(
        "subscription_events", _id(),
        sa.Column("subscription_id", sa.Uuid, sa.ForeignKey("subscriptions.id"),
                  nullable=False),
        sa.Column("from_status", sa.String(16), nullable=False),
        sa.Column("to_status", sa.String(16), nullable=False),
        sa.Column("by_login_id", sa.Uuid, sa.ForeignKey("logins.id")),
        sa.Column("reason", sa.String(200), nullable=False),
        _ts("at", False))
    op.create_index("ix_subscription_events_subscription_id", "subscription_events",
                    ["subscription_id"])

    op.create_table(
        "addon_bookings", _id(),
        sa.Column("customer_id", sa.Uuid, sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("vehicle_id", sa.Uuid, sa.ForeignKey("vehicles.id")),
        sa.Column("service", sa.String(40), nullable=False),
        sa.Column("standalone", sa.Boolean, nullable=False),
        sa.Column("proposed_date", sa.Date, nullable=False),
        sa.Column("finish_by", sa.Time, nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("price_rupees", sa.Integer),
        sa.Column("payment_id", sa.Uuid, sa.ForeignKey("payments.id")),
        sa.Column("contact_mobile", sa.String(10), nullable=False),
        sa.Column("notes", sa.Text, nullable=False),
        sa.Column("idempotency_key", sa.String(64), unique=True),
        _ts("created_at", False), _ts("cancelled_at"))
    op.create_index("ix_addon_bookings_customer_id", "addon_bookings", ["customer_id"])


def downgrade() -> None:
    for table in ("addon_bookings", "subscription_events", "money_alerts", "invoices",
                  "payment_events", "payments", "schedule_changes"):
        op.drop_table(table)
