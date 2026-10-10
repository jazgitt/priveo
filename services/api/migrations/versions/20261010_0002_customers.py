"""Societies, plans, customers, vehicles, subscriptions and add-on requests.

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "societies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("sector", sa.String(80), nullable=False),
        sa.Column("city", sa.String(80), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "plans",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("monthly_price_rupees", sa.Integer(), nullable=False),
        sa.Column("list_price_rupees", sa.Integer()),
        sa.Column("includes_interior", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("login_id", sa.Uuid(), sa.ForeignKey("logins.id"), nullable=False,
                  unique=True),
        sa.Column("first_name", sa.String(80), nullable=False),
        sa.Column("last_name", sa.String(80), nullable=False),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("mobile", sa.String(10), nullable=False),
        sa.Column("society_id", sa.Uuid(), sa.ForeignKey("societies.id"), nullable=False),
        sa.Column("flat", sa.String(40), nullable=False),
        sa.Column("terms_accepted_at", sa.DateTime(timezone=True)),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_customers_society_id", "customers", ["society_id"])
    op.create_table(
        "vehicles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("customer_id", sa.Uuid(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("registration", sa.String(12), unique=True),
        sa.Column("make", sa.String(60), nullable=False),
        sa.Column("model", sa.String(80), nullable=False),
        sa.Column("variant", sa.String(80), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("parking_basement", sa.String(20), nullable=False),
        sa.Column("parking_number", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("source_ref", sa.String(40), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_vehicles_customer_id", "vehicles", ["customer_id"])
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("vehicle_id", sa.Uuid(), sa.ForeignKey("vehicles.id"), nullable=False,
                  unique=True),
        sa.Column("plan_id", sa.Uuid(), sa.ForeignKey("plans.id")),
        sa.Column("monthly_price_rupees", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("first_service_date", sa.Date(), nullable=False),
        sa.Column("cutoff_time", sa.Time()),
        sa.Column("interior_day", sa.String(9)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "addon_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("customer_id", sa.Uuid(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), sa.ForeignKey("vehicles.id")),
        sa.Column("service", sa.String(40), nullable=False),
        sa.Column("price_rupees", sa.Integer()),
        sa.Column("service_date", sa.Date()),
        sa.Column("payment_status", sa.String(16)),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.String(40), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_addon_requests_customer_id", "addon_requests", ["customer_id"])


def downgrade() -> None:
    op.drop_table("addon_requests")
    op.drop_table("subscriptions")
    op.drop_table("vehicles")
    op.drop_table("customers")
    op.drop_table("plans")
    op.drop_table("societies")
