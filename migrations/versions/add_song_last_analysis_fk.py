"""Add Song.last_analysis_result_id FK

Revision ID: song_last_analysis_fk
Revises: pl_owner_spotify_uniq
Create Date: 2025-08-29 20:27:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'song_last_analysis_fk'
down_revision = 'pl_owner_spotify_uniq'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('songs') as batch_op:
        batch_op.add_column(sa.Column('last_analysis_result_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_songs_last_analysis',
            'analysis_results',
            ['last_analysis_result_id'],
            ['id'],
            ondelete=None,
        )
    # Optional index for faster joins
    op.create_index('idx_songs_last_analysis_fk', 'songs', ['last_analysis_result_id'], unique=False)


def downgrade():
    try:
        op.drop_index('idx_songs_last_analysis_fk', table_name='songs')
    except Exception:
        pass
    with op.batch_alter_table('songs') as batch_op:
        try:
            batch_op.drop_constraint('fk_songs_last_analysis', type_='foreignkey')
        except Exception:
            pass
        batch_op.drop_column('last_analysis_result_id')


