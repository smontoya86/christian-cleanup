"""Ensure cover_collage_urls exists on playlists

Revision ID: fix_cover_collage_urls_if_missing
Revises: perf_flags_indexes
Create Date: 2025-08-30 23:25:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_cover_collage_urls_if_missing'
down_revision = 'perf_flags_indexes'
branch_labels = None
depends_on = None


def upgrade():
    """Add playlists.cover_collage_urls if it's missing.

    This guards against environments that were stamped past the
    add_cover_collage_urls_to_playlists migration without executing it.
    """
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_columns = {col['name'] for col in insp.get_columns('playlists')}

    if 'cover_collage_urls' not in existing_columns:
        op.add_column('playlists', sa.Column('cover_collage_urls', sa.JSON(), nullable=True))


def downgrade():
    """Drop playlists.cover_collage_urls if present."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_columns = {col['name'] for col in insp.get_columns('playlists')}

    if 'cover_collage_urls' in existing_columns:
        op.drop_column('playlists', 'cover_collage_urls')


