"""Admin alert preference and durable email delivery."""
import sqlalchemy as sa
from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("logins") as batch:
        batch.add_column(sa.Column("alert_email", sa.String(254), nullable=False, server_default=""))
        batch.add_column(sa.Column("alert_email_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_table("admin_alert_emails",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("alert_id", sa.Uuid(), sa.ForeignKey("admin_alerts.id"), nullable=False),
        sa.Column("login_id", sa.Uuid(), sa.ForeignKey("logins.id"), nullable=False),
        sa.Column("recipient_email", sa.String(254), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("stopped_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("alert_id", "login_id", name="admin_alert_email_once"))
    op.create_index("ix_admin_alert_emails_alert_id", "admin_alert_emails", ["alert_id"])
    op.create_index("ix_admin_alert_emails_login_id", "admin_alert_emails", ["login_id"])


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM admin_alert_emails")):
        raise RuntimeError("Cannot discard recorded admin email deliveries during downgrade.")
    op.drop_table("admin_alert_emails")
    with op.batch_alter_table("logins") as batch:
        batch.drop_column("alert_email_enabled")
        batch.drop_column("alert_email")
