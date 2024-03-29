"""add_attachments_for_improvement

Revision ID: 9055e218d0d2
Revises: c7eee17c2081
Create Date: 2022-04-22 17:16:00.829064

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9055e218d0d2'
down_revision = 'c7eee17c2081'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('attachment', schema=None) as batch_op:
        batch_op.add_column(sa.Column('improved_id', sa.Unicode(), nullable=True))
        batch_op.create_foreign_key(batch_op.f('fk_attachment_improved_id_improvement'), 'improvement', ['improved_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('attachment', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_attachment_improved_id_improvement'), type_='foreignkey')
        batch_op.drop_column('improved_id')

    # ### end Alembic commands ###
