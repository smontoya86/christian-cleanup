"""merge heads for collage + analysis v3.1

Revision ID: c5b293f3563b
Revises: 1d29840152fe, add_cover_collage_urls_to_playlists
Create Date: 2025-08-29 20:02:12.666967

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c5b293f3563b'
down_revision = ('1d29840152fe', 'add_cover_collage_urls_to_playlists')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
