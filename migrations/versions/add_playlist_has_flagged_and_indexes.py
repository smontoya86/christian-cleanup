"""Add Playlist.has_flagged and indexes for performance

Revision ID: perf_flags_indexes
Revises: song_last_analysis_fk
Create Date: 2025-08-30 22:16:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'perf_flags_indexes'
down_revision = 'song_last_analysis_fk'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('playlists') as batch_op:
        batch_op.add_column(sa.Column('has_flagged', sa.Boolean(), nullable=False, server_default=sa.text('false')))

    # Add performance indexes (idempotent checks omitted for brevity; Alembic will manage duplicates)
    op.create_index('idx_analysis_song_analyzed', 'analysis_results', ['song_id', 'analyzed_at'], unique=False)
    op.create_index('idx_playlist_songs_song', 'playlist_songs', ['song_id'], unique=False)


def downgrade():
    try:
        op.drop_index('idx_playlist_songs_song', table_name='playlist_songs')
    except Exception:
        pass
    try:
        op.drop_index('idx_analysis_song_analyzed', table_name='analysis_results')
    except Exception:
        pass
    with op.batch_alter_table('playlists') as batch_op:
        batch_op.drop_column('has_flagged')


