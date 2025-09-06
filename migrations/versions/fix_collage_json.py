"""Ensure playlists.cover_collage_urls exists

Revision ID: fix_collage_json
Revises: perf_flags_indexes
Create Date: 2025-08-30 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_collage_json'
down_revision = 'perf_flags_indexes'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c['name'] for c in insp.get_columns('playlists')}
    if 'cover_collage_urls' not in cols:
        op.add_column('playlists', sa.Column('cover_collage_urls', sa.JSON(), nullable=True))


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c['name'] for c in insp.get_columns('playlists')}
    if 'cover_collage_urls' in cols:
        op.drop_column('playlists', 'cover_collage_urls')


