"""add_annual_leave_allocation_to_user

Revision ID: 20251115_add_annual_leave_allocation
Revises: e031abb3bee2
Create Date: 2025-11-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'r20251115a'
down_revision = 'e031abb3bee2'
branch_labels = None
depends_on = None


def upgrade():
    # Add `annual_leave_allocation` to `user` table with default 30
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('annual_leave_allocation', sa.Integer(), nullable=False, server_default=sa.text('30')))


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('annual_leave_allocation')
