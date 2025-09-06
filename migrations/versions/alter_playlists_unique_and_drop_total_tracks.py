"""Alter playlists uniqueness and drop total_tracks

Revision ID: alter_playlists_unique_and_drop_total_tracks
Revises: c5b293f3563b
Create Date: 2025-08-29 20:18:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'pl_owner_spotify_uniq'
down_revision = 'c5b293f3563b'
branch_labels = None
depends_on = None


def upgrade():
    # Drop global unique on spotify_id if exists
    try:
        op.drop_constraint('playlists_spotify_id_key', 'playlists', type_='unique')
    except Exception:
        pass

    # Drop total_tracks column if exists
    with op.batch_alter_table('playlists') as batch_op:
        try:
            batch_op.drop_column('total_tracks')
        except Exception:
            pass

    # Add composite unique (owner_id, spotify_id)
    try:
        op.create_unique_constraint('uq_playlists_owner_spotify', 'playlists', ['owner_id', 'spotify_id'])
    except Exception:
        pass


def downgrade():
    # Remove composite unique
    try:
        op.drop_constraint('uq_playlists_owner_spotify', 'playlists', type_='unique')
    except Exception:
        pass

    # Re-add total_tracks (nullable)
    with op.batch_alter_table('playlists') as batch_op:
        batch_op.add_column(sa.Column('total_tracks', sa.Integer(), nullable=True))

    # Recreate global unique on spotify_id
    try:
        op.create_unique_constraint('playlists_spotify_id_key', 'playlists', ['spotify_id'])
    except Exception:
        pass


