"""init

Revision ID: f6c08ec74bad
Revises: 
Create Date: 2019-01-27 21:08:32.275580

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f6c08ec74bad'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('reddit_post',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('post_id', sa.String(length=100), nullable=False),
    sa.Column('url', sa.String(length=100), nullable=False),
    sa.Column('post_type', sa.String(length=20), nullable=False),
    sa.Column('author', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('ingested_at', sa.DateTime(), nullable=True),
    sa.Column('subreddit', sa.String(length=100), nullable=False),
    sa.Column('title', sa.String(length=1000), nullable=False),
    sa.Column('checked_repost', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('post_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('reddit_post')
    # ### end Alembic commands ###
