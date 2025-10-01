"""Update lyrics_cache to use artist/title instead of requiring song_id

Revision ID: update_lyrics_cache_schema
Revises: 
Create Date: 2025-01-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'update_lyrics_cache_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Drop existing lyrics_cache table if it exists (it's just a cache)
    op.execute('DROP TABLE IF EXISTS lyrics_cache CASCADE')
    
    # Recreate with new schema
    op.create_table(
        'lyrics_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('artist', sa.String(length=500), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('song_id', sa.Integer(), nullable=True),
        sa.Column('lyrics', sa.Text(), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('retrieved_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('artist', 'title', name='uq_lyrics_artist_title')
    )
    
    # Create indexes
    op.create_index('ix_lyrics_cache_artist', 'lyrics_cache', ['artist'])
    op.create_index('ix_lyrics_cache_title', 'lyrics_cache', ['title'])


def downgrade():
    op.drop_table('lyrics_cache')

