"""bookings relationship in User

Revision ID: 3c01ad52a0dd
Revises: abfa1d921f82
Create Date: 2024-11-06 19:52:08.195899

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c01ad52a0dd'
down_revision: Union[str, None] = 'abfa1d921f82'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
