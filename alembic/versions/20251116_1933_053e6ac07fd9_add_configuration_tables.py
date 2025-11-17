"""add_configuration_tables

Revision ID: 053e6ac07fd9
Revises: 001_initial
Create Date: 2025-11-16 19:33:01.535971

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '053e6ac07fd9'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create configurations table
    op.create_table(
        'configurations',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('config_data', sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column('version', sa.Integer, default=1, nullable=False),
        sa.Column('is_active', sa.Boolean, default=False, nullable=False),
        sa.Column('is_default', sa.Boolean, default=False, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    
    # Create indexes for configurations
    op.create_index('idx_config_user_active', 'configurations', ['user_id', 'is_active'])
    op.create_index('idx_config_user_name', 'configurations', ['user_id', 'name'])
    
    # Create configuration_history table
    op.create_table(
        'configuration_history',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('config_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('configurations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('config_data', sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column('version', sa.Integer, nullable=False),
        sa.Column('changed_by', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('change_description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    
    # Create indexes for configuration_history
    op.create_index('idx_config_history_config_version', 'configuration_history', ['config_id', 'version'])
    op.create_index('idx_config_history_created', 'configuration_history', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_config_history_created', 'configuration_history')
    op.drop_index('idx_config_history_config_version', 'configuration_history')
    op.drop_index('idx_config_user_name', 'configurations')
    op.drop_index('idx_config_user_active', 'configurations')
    
    # Drop tables
    op.drop_table('configuration_history')
    op.drop_table('configurations')
