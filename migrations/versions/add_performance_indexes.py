"""Add performance indexes for database optimization

Revision ID: add_performance_indexes
Revises: 0953e4754acd
Create Date: 2025-05-25 15:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_performance_indexes'
down_revision = '0953e4754acd'
branch_labels = None
depends_on = None


def upgrade():
    """Add performance indexes for frequently queried columns."""

    # Songs table indexes
    op.create_index('idx_songs_spotify_id_perf', 'songs', ['spotify_id'], unique=False)
    op.create_index('idx_songs_explicit_perf', 'songs', ['explicit'], unique=False)
    op.create_index('idx_songs_last_analyzed', 'songs', ['last_analyzed'], unique=False)

    # Playlists table indexes
    op.create_index('idx_playlists_spotify_id_perf', 'playlists', ['spotify_id'], unique=False)
    op.create_index('idx_playlists_owner_id_perf', 'playlists', ['owner_id'], unique=False)
    op.create_index('idx_playlists_last_analyzed', 'playlists', ['last_analyzed'], unique=False)
    op.create_index('idx_playlists_updated_at_perf', 'playlists', [sa.text('updated_at DESC')], unique=False)

    # Analysis results table indexes (ensure we don't duplicate model-declared ones)
    op.create_index('idx_analysis_results_analyzed_at_perf', 'analysis_results', ['analyzed_at'], unique=False)
    op.create_index('idx_analysis_results_song_created_perf', 'analysis_results', ['song_id', 'created_at'], unique=False)

    # Playlist songs table indexes (for join performance)
    op.create_index('idx_playlist_songs_playlist_id_perf', 'playlist_songs', ['playlist_id'], unique=False)
    op.create_index('idx_playlist_songs_song_id_perf', 'playlist_songs', ['song_id'], unique=False)
    op.create_index('idx_playlist_songs_track_position_perf', 'playlist_songs', ['playlist_id', 'track_position'], unique=False)

    # Users table indexes
    op.create_index('idx_users_spotify_id_perf', 'users', ['spotify_id'], unique=False)

    # Whitelist table indexes
    op.create_index('idx_whitelist_user_id_perf', 'whitelist', ['user_id'], unique=False)
    op.create_index('idx_whitelist_spotify_id_perf', 'whitelist', ['spotify_id'], unique=False)
    op.create_index('idx_whitelist_item_type_perf', 'whitelist', ['item_type'], unique=False)

    # Blacklist table indexes
    op.create_index('idx_blacklist_user_id_perf', 'blacklist', ['user_id'], unique=False)
    op.create_index('idx_blacklist_spotify_id_perf', 'blacklist', ['spotify_id'], unique=False)
    op.create_index('idx_blacklist_item_type_perf', 'blacklist', ['item_type'], unique=False)


def downgrade():
    """Remove performance indexes."""

    # Remove blacklist indexes
    op.drop_index('idx_blacklist_item_type_perf', table_name='blacklist')
    op.drop_index('idx_blacklist_spotify_id_perf', table_name='blacklist')
    op.drop_index('idx_blacklist_user_id_perf', table_name='blacklist')

    # Remove whitelist indexes
    op.drop_index('idx_whitelist_item_type_perf', table_name='whitelist')
    op.drop_index('idx_whitelist_spotify_id_perf', table_name='whitelist')
    op.drop_index('idx_whitelist_user_id_perf', table_name='whitelist')

    # Remove users indexes
    op.drop_index('idx_users_spotify_id_perf', table_name='users')

    # Remove playlist_songs indexes
    op.drop_index('idx_playlist_songs_track_position_perf', table_name='playlist_songs')
    op.drop_index('idx_playlist_songs_song_id_perf', table_name='playlist_songs')
    op.drop_index('idx_playlist_songs_playlist_id_perf', table_name='playlist_songs')

    # Remove analysis_results indexes
    op.drop_index('idx_analysis_results_song_created_perf', table_name='analysis_results')
    op.drop_index('idx_analysis_results_analyzed_at_perf', table_name='analysis_results')

    # Remove playlists indexes
    op.drop_index('idx_playlists_updated_at_perf', table_name='playlists')
    op.drop_index('idx_playlists_last_analyzed', table_name='playlists')
    op.drop_index('idx_playlists_owner_id_perf', table_name='playlists')
    op.drop_index('idx_playlists_spotify_id_perf', table_name='playlists')

    # Remove songs indexes
    op.drop_index('idx_songs_last_analyzed', table_name='songs')
    op.drop_index('idx_songs_explicit_perf', table_name='songs')
    op.drop_index('idx_songs_spotify_id_perf', table_name='songs')
