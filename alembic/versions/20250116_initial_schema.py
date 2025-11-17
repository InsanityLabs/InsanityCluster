"""Initial database schema

Revision ID: 001_initial
Revises: 
Create Date: 2025-01-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Check if tables exist before creating
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # Create users table
    if 'users' not in existing_tables:
        op.create_table(
            'users',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
            sa.Column('email', sa.String(255), nullable=False, unique=True),
            sa.Column('api_key_hash', sa.String(255), nullable=True),
            sa.Column('role', sa.String(50), nullable=False, server_default='user'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        )
        op.create_index('ix_users_email', 'users', ['email'])

    # Create tasks table
    if 'tasks' not in existing_tables:
        op.create_table(
            'tasks',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('command', sa.Text(), nullable=False),
            sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
            sa.Column('task_graph', postgresql.JSONB(), nullable=True),
            sa.Column('result', postgresql.JSONB(), nullable=True),
            sa.Column('cost', sa.DECIMAL(10, 4), nullable=False, server_default='0.0'),
            sa.Column('latency_ms', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        )
        op.create_index('ix_tasks_status', 'tasks', ['status'])
        op.create_index('ix_tasks_created_at', 'tasks', ['created_at'])
        op.create_index('idx_tasks_user_status', 'tasks', ['user_id', 'status'])
        op.create_index('idx_tasks_created_status', 'tasks', ['created_at', 'status'])

    # Create context table
    if 'context' not in existing_tables:
        op.create_table(
            'context',
            sa.Column('session_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('context_data', postgresql.JSONB(), nullable=False),
            sa.Column('last_accessed', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        )
        op.create_index('ix_context_last_accessed', 'context', ['last_accessed'])
        op.create_index('idx_context_user_accessed', 'context', ['user_id', 'last_accessed'])

    # Create metrics table
    if 'metrics' not in existing_tables:
        op.create_table(
            'metrics',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=True),
            sa.Column('layer', sa.String(50), nullable=False),
            sa.Column('metric_name', sa.String(100), nullable=False),
            sa.Column('metric_value', sa.Float(), nullable=False),
            sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        )
        op.create_index('ix_metrics_timestamp', 'metrics', ['timestamp'])
        op.create_index('idx_metrics_layer_name', 'metrics', ['layer', 'metric_name'])
        op.create_index('idx_metrics_timestamp_layer', 'metrics', ['timestamp', 'layer'])

    # Create updated_at trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Add triggers for updated_at
    op.execute("""
        DROP TRIGGER IF EXISTS update_users_updated_at ON users;
        DROP TRIGGER IF EXISTS update_users_updated_at ON users;
        CREATE TRIGGER update_users_updated_at 
        BEFORE UPDATE ON users
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks;
        DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks;
        CREATE TRIGGER update_tasks_updated_at 
        BEFORE UPDATE ON tasks
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

    # Insert default admin user with API key (for development only)
    # Generate a default API key hash for initial setup
    import hashlib
    default_api_key = "ic_dev_admin_key_change_me_in_production"
    api_key_hash = hashlib.sha256(default_api_key.encode()).hexdigest()
    
    op.execute(f"""
        INSERT INTO users (email, role, api_key_hash) 
        VALUES ('admin@insanity-cluster.local', 'admin', '{api_key_hash}')
        ON CONFLICT (email) DO UPDATE SET api_key_hash = EXCLUDED.api_key_hash;
    """)
    
    print("\n" + "="*70)
    print("DEFAULT ADMIN API KEY (for development only):")
    print("="*70)
    print(f"API Key: {default_api_key}")
    print("Email: admin@insanity-cluster.local")
    print("\nWARNING: Change this key in production!")
    print("Run: python scripts/generate_admin_api_key.py")
    print("="*70 + "\n")


def downgrade() -> None:
    # Drop triggers
    op.execute('DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks')
    op.execute('DROP TRIGGER IF EXISTS update_users_updated_at ON users')
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column()')

    # Drop tables
    op.drop_table('metrics')
    op.drop_table('context')
    op.drop_table('tasks')
    op.drop_table('users')

    # Drop extension
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
