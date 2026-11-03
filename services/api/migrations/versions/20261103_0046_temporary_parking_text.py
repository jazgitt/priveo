"""A temporary or permanent parking change takes free text up to 60 characters
(ADM-CUS-27), the same width as a vehicle's own parking number.

Revision ID: 0046
Revises: 0045
"""
import sqlalchemy as sa
from alembic import op

revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("vehicle_parking_changes") as batch:
        batch.alter_column("number", existing_type=sa.String(20), type_=sa.String(60),
                           existing_nullable=False)


def downgrade():
    with op.batch_alter_table("vehicle_parking_changes") as batch:
        batch.alter_column("number", existing_type=sa.String(60), type_=sa.String(20),
                           existing_nullable=False)
