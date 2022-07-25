"""add more column to Claim and Task

Revision ID: c7eee17c2081
Revises: c0f674a8ae39
Create Date: 2022-03-31 22:52:32.632637

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7eee17c2081'
down_revision = 'c0f674a8ae39'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('claim', schema=None) as batch_op:
        batch_op.add_column(sa.Column('start_date', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('due_date', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('completion', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('lesson_learned', sa.Unicode(), nullable=True))
        batch_op.add_column(sa.Column('milestone_id', sa.Unicode(), nullable=True))
        batch_op.add_column(sa.Column('teamleader_id', sa.Unicode(), nullable=True))
        batch_op.create_foreign_key(batch_op.f('fk_claim_teamleader_id_user'), 'user', ['teamleader_id'], ['id'])
        batch_op.create_foreign_key(batch_op.f('fk_claim_milestone_id_milestone'), 'milestone', ['milestone_id'], ['id'])

    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('start_date', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('due_date', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('completion', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('lesson_learned', sa.Unicode(), nullable=True))
        batch_op.add_column(sa.Column('teamleader_id', sa.Unicode(), nullable=True))
        batch_op.create_foreign_key(batch_op.f('fk_task_teamleader_id_user'), 'user', ['teamleader_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_task_teamleader_id_user'), type_='foreignkey')
        batch_op.drop_column('teamleader_id')
        batch_op.drop_column('lesson_learned')
        batch_op.drop_column('completion')
        batch_op.drop_column('due_date')
        batch_op.drop_column('start_date')

    with op.batch_alter_table('claim', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_claim_milestone_id_milestone'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('fk_claim_teamleader_id_user'), type_='foreignkey')
        batch_op.drop_column('teamleader_id')
        batch_op.drop_column('milestone_id')
        batch_op.drop_column('lesson_learned')
        batch_op.drop_column('completion')
        batch_op.drop_column('due_date')
        batch_op.drop_column('start_date')

    # ### end Alembic commands ###
