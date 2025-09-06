"""Add cover_collage_urls JSON column to playlists

Revision ID: add_cover_collage_urls_to_playlists
Revises: add_performance_indexes
Create Date: 2025-08-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_cover_collage_urls_to_playlists'
down_revision = 'add_performance_indexes'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('playlists', sa.Column('cover_collage_urls', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('playlists', 'cover_collage_urls')


