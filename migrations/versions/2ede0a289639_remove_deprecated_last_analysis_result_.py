"""Remove deprecated last_analysis_result_id FK for simplicity

Revision ID: 2ede0a289639
Revises: merge_fix_collage_heads
Create Date: 2025-09-01 16:44:58.225086

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2ede0a289639'
down_revision = 'merge_fix_collage_heads'
branch_labels = None
depends_on = None


def upgrade():
    # Remove the FK constraint first
    op.drop_constraint('fk_songs_last_analysis', 'songs', type_='foreignkey')
    # Remove the column
    op.drop_column('songs', 'last_analysis_result_id')


def downgrade():
    # Add the column back
    op.add_column('songs', sa.Column('last_analysis_result_id', sa.Integer(), nullable=True))
    # Add the FK constraint back
    op.create_foreign_key('fk_songs_last_analysis', 'songs', 'analysis_results', ['last_analysis_result_id'], ['id'])
