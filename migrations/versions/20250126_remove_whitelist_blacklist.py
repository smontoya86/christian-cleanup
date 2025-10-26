"""Remove whitelist and blacklist tables

Revision ID: remove_whitelist_blacklist
Revises: add_analysis_indexes
Create Date: 2025-01-26

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_whitelist_blacklist'
down_revision = 'add_analysis_indexes'
branch_labels = None
depends_on = None


def upgrade():
    # Drop whitelist and blacklist tables
    op.drop_table('whitelist')
    op.drop_table('blacklist')


def downgrade():
    # Recreate whitelist table (in case we need to roll back)
    op.create_table(
        'whitelist',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('spotify_id', sa.String(length=255), nullable=False),
        sa.Column('item_type', sa.String(length=50), nullable=False),
        sa.Column('item_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'spotify_id', 'item_type', name='uq_whitelist_user_item')
    )
    
    # Recreate blacklist table (in case we need to roll back)
    op.create_table(
        'blacklist',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('spotify_id', sa.String(length=255), nullable=False),
        sa.Column('item_type', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'spotify_id', 'item_type', name='uq_blacklist_user_item')
    )

