"""Remember the refresh token a session just replaced, so a copied token that is
used later can be detected and the session ended (security review R-07).
Nothing is backfilled: existing sessions have no previous token.

Revision ID: 0058
Revises: 0057
"""
import sqlalchemy as sa
from alembic import op

revision = "0058"
down_revision = "0057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("auth_sessions", sa.Column("previous_refresh_hash", sa.String(64)))
    op.add_column("auth_sessions", sa.Column("rotated_at", sa.DateTime(timezone=True)))
    op.create_index("ix_auth_sessions_previous_refresh_hash", "auth_sessions",
                    ["previous_refresh_hash"])


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_previous_refresh_hash", table_name="auth_sessions")
    op.drop_column("auth_sessions", "rotated_at")
    op.drop_column("auth_sessions", "previous_refresh_hash")
