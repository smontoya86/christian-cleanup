"""Initial database schema

Revision ID: 0543cea91b5b
Revises: 
Create Date: 2025-05-08 10:22:48.598773

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0543cea91b5b'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('bible_verses',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('book', sa.String(length=50), nullable=False),
    sa.Column('chapter', sa.Integer(), nullable=False),
    sa.Column('verse_start', sa.Integer(), nullable=False),
    sa.Column('verse_end', sa.Integer(), nullable=True),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('theme_keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('songs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('spotify_id', sa.String(length=255), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('artist', sa.String(length=255), nullable=False),
    sa.Column('album', sa.String(length=255), nullable=True),
    sa.Column('lyrics', sa.Text(), nullable=True),
    sa.Column('explicit', sa.Boolean(), nullable=True),
    sa.Column('last_analyzed', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('spotify_id')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('spotify_id', sa.String(length=255), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('display_name', sa.String(length=255), nullable=True),
    sa.Column('access_token', sa.String(length=512), nullable=False),
    sa.Column('refresh_token', sa.String(length=512), nullable=True),
    sa.Column('token_expiry', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('spotify_id')
    )
    op.create_table('analysis_results',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('themes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('problematic_content', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('alignment_score', sa.Float(), nullable=True),
    sa.Column('explanation', sa.Text(), nullable=True),
    sa.Column('analyzed_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('playlists',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('spotify_id', sa.String(length=255), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('owner_id', sa.Integer(), nullable=False),
    sa.Column('last_analyzed', sa.DateTime(), nullable=True),
    sa.Column('overall_alignment_score', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('spotify_id')
    )
    op.create_table('whitelist',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('artist_name', sa.String(length=255), nullable=True),
    sa.Column('song_title', sa.String(length=255), nullable=True),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'artist_name', name='_user_artist_uc'),
    sa.UniqueConstraint('user_id', 'song_title', 'artist_name', name='_user_song_artist_uc')
    )
    op.create_table('playlist_songs',
    sa.Column('playlist_id', sa.Integer(), nullable=False),
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['playlist_id'], ['playlists.id'], ),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ),
    sa.PrimaryKeyConstraint('playlist_id', 'song_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('playlist_songs')
    op.drop_table('whitelist')
    op.drop_table('playlists')
    op.drop_table('analysis_results')
    op.drop_table('users')
    op.drop_table('songs')
    op.drop_table('bible_verses')
    # ### end Alembic commands ###
