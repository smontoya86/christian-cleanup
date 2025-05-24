"""Merge migration heads

Revision ID: 0cad2d21a349
Revises: 01dc8d6f7bd9, add_user_analysis_preferences, ed274454e605
Create Date: 2025-05-24 09:49:01.337141

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0cad2d21a349'
down_revision = ('01dc8d6f7bd9', 'add_user_analysis_preferences', 'ed274454e605')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
