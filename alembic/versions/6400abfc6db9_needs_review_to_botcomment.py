"""needs review to botcomment

Revision ID: 6400abfc6db9
Revises: 4f4476b92ea2
Create Date: 2019-11-11 20:38:36.871337

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6400abfc6db9'
down_revision = '4f4476b92ea2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('reddit_bot_comment', sa.Column('needs_review', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('reddit_bot_comment', 'needs_review')
    # ### end Alembic commands ###
