"""Create connected_posts table

Revision ID: 17266632e66b
Revises: 13d8d76be90f
Create Date: 2024-10-03 20:10:11.010221

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = '17266632e66b'
down_revision: Union[str, None] = '13d8d76be90f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table('connected_posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('a_name', sa.Text(), nullable=False),
        sa.Column('depth', sa.Integer(), nullable=False),
        sa.Column('result', JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('a_name', 'depth')
    )

def downgrade():
    op.drop_table('connected_posts')