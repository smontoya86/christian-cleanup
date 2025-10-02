"""Add analysis cache table

Revision ID: add_analysis_cache
Revises: 
Create Date: 2025-10-02 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_analysis_cache'
down_revision = None  # Update this to the latest migration
branch_labels = None
depends_on = None


def upgrade():
    # Create analysis_cache table
    op.create_table(
        'analysis_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('artist', sa.String(length=500), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('lyrics_hash', sa.String(length=64), nullable=False),
        sa.Column('analysis_result', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('model_version', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('artist', 'title', 'lyrics_hash', name='uq_analysis_cache_song')
    )
    
    # Create indexes for fast lookups
    op.create_index('idx_analysis_cache_artist_title', 'analysis_cache', ['artist', 'title'])
    op.create_index('idx_analysis_cache_model_version', 'analysis_cache', ['model_version'])
    op.create_index('idx_analysis_cache_created_at', 'analysis_cache', ['created_at'])


def downgrade():
    op.drop_index('idx_analysis_cache_created_at', table_name='analysis_cache')
    op.drop_index('idx_analysis_cache_model_version', table_name='analysis_cache')
    op.drop_index('idx_analysis_cache_artist_title', table_name='analysis_cache')
    op.drop_table('analysis_cache')

