"""Add status and score indexes to AnalysisResult

Revision ID: add_analysis_indexes
Revises: 
Create Date: 2025-10-04

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_analysis_indexes'
down_revision = None  # Update this with your latest migration
branch_labels = None
depends_on = None


def upgrade():
    # Add indexes for frequently queried columns
    op.create_index('idx_analysis_status', 'analysis_results', ['status'])
    op.create_index('idx_analysis_score', 'analysis_results', ['score'])


def downgrade():
    # Remove indexes if rolling back
    op.drop_index('idx_analysis_status', table_name='analysis_results')
    op.drop_index('idx_analysis_score', table_name='analysis_results')

