"""Support and feedback: complaints, feedback, visit ratings, check-ins, alerts.

Revision ID: 0010
Revises: 0004
"""
import sqlalchemy as sa
from alembic import op

revision = "0010"
# The earlier migrations are named by their short ID ("0004"), which is what
# Alembic matches; the file is 20261010_0004_onboarding_confirmed.py.
down_revision = "0008"
branch_labels = None
depends_on = None


def _id() -> sa.Column:
    return sa.Column("id", sa.Uuid, primary_key=True)


def upgrade() -> None:
    op.create_table(
        "support_options", _id(),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False),
        sa.UniqueConstraint("kind", "name", name="support_options_kind_name"))
    op.create_index("ix_support_options_kind", "support_options", ["kind"])

    op.create_table(
        "complaints", _id(),
        sa.Column("number", sa.Integer, nullable=False, unique=True),
        sa.Column("customer_id", sa.Uuid, sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("visit_id", sa.String(64)),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("photo_keys", sa.JSON, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("overdue_alerted_at", sa.DateTime(timezone=True)))
    op.create_index("ix_complaints_customer_id", "complaints", ["customer_id"])

    op.create_table(
        "complaint_updates", _id(),
        sa.Column("complaint_id", sa.Uuid, sa.ForeignKey("complaints.id"), nullable=False),
        sa.Column("author_role", sa.String(16), nullable=False),
        sa.Column("author_login_id", sa.Uuid, sa.ForeignKey("logins.id")),
        sa.Column("note", sa.Text, nullable=False),
        sa.Column("status", sa.String(16)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_complaint_updates_complaint_id", "complaint_updates", ["complaint_id"])

    op.create_table(
        "feedback", _id(),
        sa.Column("customer_id", sa.Uuid, sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("category", sa.String(80)),
        sa.Column("rating", sa.Integer),
        sa.Column("comment", sa.Text, nullable=False),
        sa.Column("testimonial_permission", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_feedback_customer_id", "feedback", ["customer_id"])

    op.create_table(
        "visit_ratings", _id(),
        sa.Column("customer_id", sa.Uuid, sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("visit_id", sa.String(64), nullable=False),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("tags", sa.JSON, nullable=False),
        sa.Column("comment", sa.Text, nullable=False),
        sa.Column("testimonial_permission", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("customer_id", "visit_id", name="visit_ratings_once"))
    op.create_index("ix_visit_ratings_customer_id", "visit_ratings", ["customer_id"])
    op.create_index("ix_visit_ratings_visit_id", "visit_ratings", ["visit_id"])

    op.create_table(
        "checkins", _id(),
        sa.Column("customer_id", sa.Uuid, sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("subscription_id", sa.Uuid, sa.ForeignKey("subscriptions.id"), nullable=False),
        sa.Column("cycle_start", sa.Date, nullable=False),
        sa.Column("answers", sa.JSON, nullable=False),
        sa.Column("comment", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("subscription_id", "cycle_start", name="checkins_once_a_cycle"))
    op.create_index("ix_checkins_customer_id", "checkins", ["customer_id"])
    op.create_index("ix_checkins_subscription_id", "checkins", ["subscription_id"])

    op.create_table(
        "admin_alerts", _id(),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("body", sa.String(500), nullable=False),
        sa.Column("ref_type", sa.String(24)),
        sa.Column("ref_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)))
    op.create_index("ix_admin_alerts_created_at", "admin_alerts", ["created_at"])


def downgrade() -> None:
    for table in ("admin_alerts", "checkins", "visit_ratings", "feedback",
                  "complaint_updates", "complaints", "support_options"):
        op.drop_table(table)
