"""unique key for close events

Revision ID: d2fe9805c96e
Revises: 77094a1d8362
Create Date: 2025-01-14 17:08:53.620310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2fe9805c96e'
down_revision: Union[str, None] = '77094a1d8362'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('event', sa.Column('unique_key', sa.String(), nullable=True))
    op.create_unique_constraint(None, 'event', ['unique_key'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'event', type_='unique')
    op.drop_column('event', 'unique_key')
    # ### end Alembic commands ###
