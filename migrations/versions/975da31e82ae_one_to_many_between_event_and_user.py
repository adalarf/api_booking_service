"""one to many between event and user

Revision ID: 975da31e82ae
Revises: 00e176ad29f5
Create Date: 2024-11-18 11:51:41.171897

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '975da31e82ae'
down_revision: Union[str, None] = '00e176ad29f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('event_creator_id_key', 'event', type_='unique')
    op.drop_constraint('event_creator_id_fkey', 'event', type_='foreignkey')
    op.drop_column('event', 'creator_id')
    op.add_column('user', sa.Column('event_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'user', 'event', ['event_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'user', type_='foreignkey')
    op.drop_column('user', 'event_id')
    op.add_column('event', sa.Column('creator_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('event_creator_id_fkey', 'event', 'user', ['creator_id'], ['id'])
    op.create_unique_constraint('event_creator_id_key', 'event', ['creator_id'])
    # ### end Alembic commands ###