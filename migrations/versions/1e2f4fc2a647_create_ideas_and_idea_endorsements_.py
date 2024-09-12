"""Create ideas and idea_endorsements tables

Revision ID: 1e2f4fc2a647
Revises: 
Create Date: 2023-05-24 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '1e2f4fc2a647'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create ideas table
    op.create_table('ideas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('node_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('link', sa.String(), nullable=False),
        sa.Column('label', sa.Text(), nullable=True),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('endorsement_count', sa.Integer(), server_default=sa.text('0'), nullable=True),
        sa.Column('main_article', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create idea_endorsements table
    op.create_table('idea_endorsements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('idea_id', sa.Integer(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['idea_id'], ['ideas.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('idea_endorsements')
    op.drop_table('ideas')