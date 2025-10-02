"""Add last_login column to users table for force re-auth

Revision ID: add_last_login_to_users
Revises: add_analysis_quality_field
Create Date: 2025-10-02 23:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_last_login_to_users'
down_revision = 'add_analysis_quality_field'
branch_labels = None
depends_on = None


def upgrade():
    # Add last_login column to users table
    op.add_column('users', sa.Column('last_login', sa.DateTime(timezone=True), nullable=True))
    
    # Set existing users' last_login to their updated_at timestamp
    op.execute("UPDATE users SET last_login = updated_at WHERE last_login IS NULL")


def downgrade():
    # Remove last_login column
    op.drop_column('users', 'last_login')

