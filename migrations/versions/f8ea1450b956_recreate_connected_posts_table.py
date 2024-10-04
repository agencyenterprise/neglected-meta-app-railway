"""recreate_connected_posts_table

Revision ID: f8ea1450b956
Revises: 17266632e66b
Create Date: 2024-10-03 23:37:05.163203

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = 'f8ea1450b956'
down_revision: Union[str, None] = '17266632e66b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # Drop the existing table
    op.drop_table('connected_posts')

    # Recreate the table with new columns
    op.create_table('connected_posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('a_name', sa.Text(), nullable=False),
        sa.Column('depth', sa.Integer(), nullable=False),
        sa.Column('post_nodes', JSONB(), nullable=False),
        sa.Column('comment_nodes', JSONB(), nullable=False),
        sa.Column('edges', JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('a_name', 'depth')
    )

    # Create indexes
    op.create_index(op.f('ix_connected_posts_a_name'), 'connected_posts', ['a_name'], unique=False)
    op.create_index(op.f('ix_connected_posts_depth'), 'connected_posts', ['depth'], unique=False)
    op.create_index(op.f('ix_connected_posts_created_at'), 'connected_posts', ['created_at'], unique=False)
    op.create_index(op.f('ix_connected_posts_updated_at'), 'connected_posts', ['updated_at'], unique=False)

    # Create a GIN index for the JSONB columns
    op.execute('CREATE INDEX ix_connected_posts_post_nodes ON connected_posts USING GIN (post_nodes)')
    op.execute('CREATE INDEX ix_connected_posts_comment_nodes ON connected_posts USING GIN (comment_nodes)')
    op.execute('CREATE INDEX ix_connected_posts_edges ON connected_posts USING GIN (edges)')

def downgrade():
    # Drop the indexes
    op.drop_index(op.f('ix_connected_posts_a_name'), table_name='connected_posts')
    op.drop_index(op.f('ix_connected_posts_depth'), table_name='connected_posts')
    op.drop_index(op.f('ix_connected_posts_created_at'), table_name='connected_posts')
    op.drop_index(op.f('ix_connected_posts_updated_at'), table_name='connected_posts')
    op.execute('DROP INDEX ix_connected_posts_post_nodes')
    op.execute('DROP INDEX ix_connected_posts_comment_nodes')
    op.execute('DROP INDEX ix_connected_posts_edges')

    # Drop the new table
    op.drop_table('connected_posts')

    # Recreate the original table
    op.create_table('connected_posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('a_name', sa.Text(), nullable=False),
        sa.Column('depth', sa.Integer(), nullable=False),
        sa.Column('compressed_result', sa.TEXT(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('a_name', 'depth')
    )