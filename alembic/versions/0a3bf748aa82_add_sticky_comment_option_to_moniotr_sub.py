"""Add sticky comment option to moniotr sub

Revision ID: 0a3bf748aa82
Revises: 32bcf6ee2dee
Create Date: 2019-11-02 09:14:05.637924

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0a3bf748aa82'
down_revision = '32bcf6ee2dee'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('reddit_monitored_sub', sa.Column('sticky_comment', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('reddit_monitored_sub', 'sticky_comment')
    # ### end Alembic commands ###