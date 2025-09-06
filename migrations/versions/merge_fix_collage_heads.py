"""merge heads for collage fix

Revision ID: merge_fix_collage_heads
Revises: fix_collage_json, fix_cover_collage_urls_if_missing
Create Date: 2025-08-30 23:33:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_fix_collage_heads'
down_revision = ('fix_collage_json', 'fix_cover_collage_urls_if_missing')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass


