"""rename_ideas_to_spotlight_approaches

Revision ID: 13d8d76be90f
Revises: 1e2f4fc2a647
Create Date: 2024-09-17 18:02:13.023597

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '13d8d76be90f'
down_revision: Union[str, None] = '1e2f4fc2a647'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # Rename tables
    op.rename_table('ideas', 'approaches')
    op.rename_table('idea_endorsements', 'spotlights')

    # Rename columns
    with op.batch_alter_table('approaches') as batch_op:
        batch_op.alter_column('endorsement_count', new_column_name='spotlight_count')

    with op.batch_alter_table('spotlights') as batch_op:
        batch_op.alter_column('idea_id', new_column_name='approach_id')

    # Update foreign key constraint
    op.drop_constraint('idea_endorsements_idea_id_fkey', 'spotlights', type_='foreignkey')
    op.create_foreign_key(None, 'spotlights', 'approaches', ['approach_id'], ['id'])

def downgrade():
    # Revert foreign key constraint
    op.drop_constraint(None, 'spotlights', type_='foreignkey')
    op.create_foreign_key('idea_endorsements_idea_id_fkey', 'spotlights', 'approaches', ['approach_id'], ['id'])

    # Revert column names
    with op.batch_alter_table('spotlights') as batch_op:
        batch_op.alter_column('approach_id', new_column_name='idea_id')

    with op.batch_alter_table('approaches') as batch_op:
        batch_op.alter_column('spotlight_count', new_column_name='endorsement_count')

    # Revert table names
    op.rename_table('spotlights', 'idea_endorsements')
    op.rename_table('approaches', 'ideas')