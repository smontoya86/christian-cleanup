"""Add analysis_quality field to analysis_results

Revision ID: add_analysis_quality
Revises: add_analysis_cache
Create Date: 2025-10-02 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_analysis_quality'
down_revision = 'add_analysis_cache'
branch_labels = None
depends_on = None


def upgrade():
    # Add analysis_quality column with default 'full'
    op.add_column('analysis_results', 
                  sa.Column('analysis_quality', sa.String(length=20), nullable=False, server_default='full'))


def downgrade():
    op.drop_column('analysis_results', 'analysis_quality')

