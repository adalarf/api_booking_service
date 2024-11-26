"""swap relation between user and event(2)

Revision ID: c1546c995298
Revises: 975da31e82ae
Create Date: 2024-11-18 11:57:18.459510

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1546c995298'
down_revision: Union[str, None] = '975da31e82ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('event', sa.Column('creator_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'event', 'user', ['creator_id'], ['id'])
    op.drop_constraint('user_event_id_fkey', 'user', type_='foreignkey')
    op.drop_column('user', 'event_id')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('event_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('user_event_id_fkey', 'user', 'event', ['event_id'], ['id'])
    op.drop_constraint(None, 'event', type_='foreignkey')
    op.drop_column('event', 'creator_id')
    # ### end Alembic commands ###