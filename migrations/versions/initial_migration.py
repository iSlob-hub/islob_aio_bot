"""Initial migration

Revision ID: 0001
Revises: 
Create Date: 2025-05-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=32), nullable=True),
        sa.Column('first_name', sa.String(length=64), nullable=False),
        sa.Column('last_name', sa.String(length=64), nullable=True),
        sa.Column('current_node', sa.String(length=64), nullable=True),
        sa.Column('context', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_users_chat_id'), 'users', ['chat_id'], unique=True)


def downgrade() -> None:
    # Drop users table
    op.drop_index(op.f('ix_users_chat_id'), table_name='users')
    op.drop_table('users')
