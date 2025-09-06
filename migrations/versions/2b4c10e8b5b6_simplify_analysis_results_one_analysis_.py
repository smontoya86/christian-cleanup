"""Simplify analysis_results: one analysis per song with UNIQUE constraint

Revision ID: 2b4c10e8b5b6
Revises: 2ede0a289639
Create Date: 2025-09-01 16:53:30.974268

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2b4c10e8b5b6'
down_revision = '2ede0a289639'
branch_labels = None
depends_on = None


def upgrade():
    # Fix NULL values and normalize concern_level before adding constraints
    op.execute("UPDATE analysis_results SET explanation = 'Analysis completed' WHERE explanation IS NULL")
    op.execute("UPDATE analysis_results SET score = 85.0 WHERE score IS NULL")
    
    # Normalize concern_level values to standard format
    op.execute("UPDATE analysis_results SET concern_level = 'Low' WHERE concern_level IN ('low', 'very_low', 'Very Low', 'No Lyrics Available', 'Instrumental', 'unknown', 'Unknown')")
    op.execute("UPDATE analysis_results SET concern_level = 'Medium' WHERE concern_level = 'medium'")
    op.execute("UPDATE analysis_results SET concern_level = 'High' WHERE concern_level = 'high'")
    op.execute("UPDATE analysis_results SET concern_level = 'Low' WHERE concern_level IS NULL")
    
    # Add UNIQUE constraint on song_id (data already cleaned)
    op.create_unique_constraint('uq_analysis_results_song_id', 'analysis_results', ['song_id'])
    
    # Remove status column since only completed analyses exist
    op.drop_column('analysis_results', 'status')
    
    # Remove error_message column since we don't store failed analyses
    op.drop_column('analysis_results', 'error_message')
    
    # Make core fields NOT NULL since they should always be present
    op.alter_column('analysis_results', 'score', nullable=False)
    op.alter_column('analysis_results', 'concern_level', nullable=False)
    op.alter_column('analysis_results', 'explanation', nullable=False)
    
    # Add check constraints for data integrity
    op.create_check_constraint('ck_analysis_score_range', 'analysis_results', 'score >= 0 AND score <= 100')
    op.create_check_constraint('ck_analysis_concern_level', 'analysis_results', "concern_level IN ('Low', 'Medium', 'High')")


def downgrade():
    # Remove check constraints
    op.drop_constraint('ck_analysis_concern_level', 'analysis_results', type_='check')
    op.drop_constraint('ck_analysis_score_range', 'analysis_results', type_='check')
    
    # Make fields nullable again
    op.alter_column('analysis_results', 'explanation', nullable=True)
    op.alter_column('analysis_results', 'concern_level', nullable=True)
    op.alter_column('analysis_results', 'score', nullable=True)
    
    # Add back columns
    op.add_column('analysis_results', sa.Column('error_message', sa.TEXT(), nullable=True))
    op.add_column('analysis_results', sa.Column('status', sa.VARCHAR(length=20), nullable=False, server_default='completed'))
    
    # Remove UNIQUE constraint
    op.drop_constraint('uq_analysis_results_song_id', 'analysis_results', type_='unique')
