"""Initial migration - Create all MoxNAS tables

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types for PostgreSQL
    user_role_enum = postgresql.ENUM('USER', 'ADMIN', name='userrole', create_type=True)
    share_protocol_enum = postgresql.ENUM('SMB', 'NFS', 'FTP', name='shareprotocol', create_type=True)
    share_status_enum = postgresql.ENUM('ACTIVE', 'INACTIVE', 'ERROR', name='sharestatus', create_type=True)
    pool_status_enum = postgresql.ENUM('HEALTHY', 'DEGRADED', 'FAILED', 'SCRUBBING', name='poolstatus', create_type=True)
    device_status_enum = postgresql.ENUM('HEALTHY', 'WARNING', 'FAILED', 'UNKNOWN', name='devicestatus', create_type=True)
    alert_severity_enum = postgresql.ENUM('INFO', 'WARNING', 'CRITICAL', name='alertseverity', create_type=True)
    backup_status_enum = postgresql.ENUM('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED', name='backupstatus', create_type=True)
    source_type_enum = postgresql.ENUM('DIRECTORY', 'DATABASE', 'VOLUME', name='sourcetype', create_type=True)
    destination_type_enum = postgresql.ENUM('DIRECTORY', 'S3', 'FTP', 'SSH', name='destinationtype', create_type=True)

    # Users table
    op.create_table('user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=50), nullable=True),
        sa.Column('last_name', sa.String(length=50), nullable=True),
        sa.Column('role', user_role_enum, nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False),
        sa.Column('locked_until', sa.DateTime(), nullable=True),
        sa.Column('totp_secret', sa.String(length=32), nullable=True),
        sa.Column('totp_enabled', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    
    # Storage pools table
    op.create_table('storage_pool',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('raid_level', sa.String(length=20), nullable=False),
        sa.Column('filesystem_type', sa.String(length=20), nullable=False),
        sa.Column('total_size', sa.BigInteger(), nullable=False),
        sa.Column('used_size', sa.BigInteger(), nullable=False),
        sa.Column('status', pool_status_enum, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Storage devices table
    op.create_table('storage_device',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_name', sa.String(length=50), nullable=False),
        sa.Column('device_path', sa.String(length=255), nullable=False),
        sa.Column('device_size', sa.BigInteger(), nullable=False),
        sa.Column('device_model', sa.String(length=100), nullable=True),
        sa.Column('serial_number', sa.String(length=100), nullable=True),
        sa.Column('status', device_status_enum, nullable=False),
        sa.Column('temperature', sa.Integer(), nullable=True),
        sa.Column('power_on_hours', sa.Integer(), nullable=True),
        sa.Column('pool_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['pool_id'], ['storage_pool.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('device_name')
    )
    
    # Shares table
    op.create_table('share',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('protocol', share_protocol_enum, nullable=False),
        sa.Column('dataset_id', sa.Integer(), nullable=False),
        sa.Column('path', sa.String(length=500), nullable=False),
        sa.Column('read_only', sa.Boolean(), nullable=False),
        sa.Column('guest_access', sa.Boolean(), nullable=False),
        sa.Column('status', share_status_enum, nullable=False),
        sa.Column('connections_count', sa.Integer(), nullable=False),
        sa.Column('last_access', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['dataset_id'], ['storage_pool.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Alerts table
    op.create_table('alert',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('severity', alert_severity_enum, nullable=False),
        sa.Column('component', sa.String(length=50), nullable=False),
        sa.Column('acknowledged', sa.Boolean(), nullable=False),
        sa.Column('acknowledged_by_id', sa.Integer(), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['acknowledged_by_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Backup jobs table
    op.create_table('backup_job',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('source_type', source_type_enum, nullable=False),
        sa.Column('source_path', sa.String(length=500), nullable=False),
        sa.Column('destination_type', destination_type_enum, nullable=False),
        sa.Column('destination_path', sa.String(length=500), nullable=False),
        sa.Column('schedule', sa.String(length=50), nullable=True),
        sa.Column('compression', sa.Boolean(), nullable=False),
        sa.Column('encryption', sa.Boolean(), nullable=False),
        sa.Column('retention_days', sa.Integer(), nullable=False),
        sa.Column('status', backup_status_enum, nullable=False),
        sa.Column('last_run', sa.DateTime(), nullable=True),
        sa.Column('next_run', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Backup history table
    op.create_table('backup_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('status', backup_status_enum, nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('bytes_transferred', sa.BigInteger(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['backup_job.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # System health table
    op.create_table('system_health',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('cpu_usage', sa.Float(), nullable=False),
        sa.Column('memory_usage', sa.Float(), nullable=False),
        sa.Column('disk_usage', sa.Float(), nullable=False),
        sa.Column('load_average', sa.Float(), nullable=False),
        sa.Column('services_status', sa.Text(), nullable=True),
        sa.Column('alerts_count', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better performance
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)
    op.create_index(op.f('ix_user_username'), 'user', ['username'], unique=True)
    op.create_index(op.f('ix_user_created_at'), 'user', ['created_at'])
    op.create_index(op.f('ix_user_last_login'), 'user', ['last_login'])
    
    op.create_index(op.f('ix_storage_pool_name'), 'storage_pool', ['name'], unique=True)
    op.create_index(op.f('ix_storage_pool_created_at'), 'storage_pool', ['created_at'])
    op.create_index(op.f('ix_storage_pool_status'), 'storage_pool', ['status'])
    
    op.create_index(op.f('ix_storage_device_device_name'), 'storage_device', ['device_name'], unique=True)
    op.create_index(op.f('ix_storage_device_status'), 'storage_device', ['status'])
    op.create_index(op.f('ix_storage_device_pool_id'), 'storage_device', ['pool_id'])
    
    op.create_index(op.f('ix_share_name'), 'share', ['name'], unique=True)
    op.create_index(op.f('ix_share_protocol'), 'share', ['protocol'])
    op.create_index(op.f('ix_share_status'), 'share', ['status'])
    op.create_index(op.f('ix_share_created_at'), 'share', ['created_at'])
    
    op.create_index(op.f('ix_alert_severity'), 'alert', ['severity'])
    op.create_index(op.f('ix_alert_component'), 'alert', ['component'])
    op.create_index(op.f('ix_alert_created_at'), 'alert', ['created_at'])
    op.create_index(op.f('ix_alert_acknowledged'), 'alert', ['acknowledged'])
    
    op.create_index(op.f('ix_backup_job_name'), 'backup_job', ['name'], unique=True)
    op.create_index(op.f('ix_backup_job_status'), 'backup_job', ['status'])
    op.create_index(op.f('ix_backup_job_next_run'), 'backup_job', ['next_run'])
    op.create_index(op.f('ix_backup_job_created_at'), 'backup_job', ['created_at'])
    
    op.create_index(op.f('ix_backup_history_job_id'), 'backup_history', ['job_id'])
    op.create_index(op.f('ix_backup_history_status'), 'backup_history', ['status'])
    op.create_index(op.f('ix_backup_history_started_at'), 'backup_history', ['started_at'])
    
    op.create_index(op.f('ix_system_health_timestamp'), 'system_health', ['timestamp'])


def downgrade() -> None:
    # Drop all indexes
    op.drop_index(op.f('ix_system_health_timestamp'), table_name='system_health')
    op.drop_index(op.f('ix_backup_history_started_at'), table_name='backup_history')
    op.drop_index(op.f('ix_backup_history_status'), table_name='backup_history')
    op.drop_index(op.f('ix_backup_history_job_id'), table_name='backup_history')
    op.drop_index(op.f('ix_backup_job_created_at'), table_name='backup_job')
    op.drop_index(op.f('ix_backup_job_next_run'), table_name='backup_job')
    op.drop_index(op.f('ix_backup_job_status'), table_name='backup_job')
    op.drop_index(op.f('ix_backup_job_name'), table_name='backup_job')
    op.drop_index(op.f('ix_alert_acknowledged'), table_name='alert')
    op.drop_index(op.f('ix_alert_created_at'), table_name='alert')
    op.drop_index(op.f('ix_alert_component'), table_name='alert')
    op.drop_index(op.f('ix_alert_severity'), table_name='alert')
    op.drop_index(op.f('ix_share_created_at'), table_name='share')
    op.drop_index(op.f('ix_share_status'), table_name='share')
    op.drop_index(op.f('ix_share_protocol'), table_name='share')
    op.drop_index(op.f('ix_share_name'), table_name='share')
    op.drop_index(op.f('ix_storage_device_pool_id'), table_name='storage_device')
    op.drop_index(op.f('ix_storage_device_status'), table_name='storage_device')
    op.drop_index(op.f('ix_storage_device_device_name'), table_name='storage_device')
    op.drop_index(op.f('ix_storage_pool_status'), table_name='storage_pool')
    op.drop_index(op.f('ix_storage_pool_created_at'), table_name='storage_pool')
    op.drop_index(op.f('ix_storage_pool_name'), table_name='storage_pool')
    op.drop_index(op.f('ix_user_last_login'), table_name='user')
    op.drop_index(op.f('ix_user_created_at'), table_name='user')
    op.drop_index(op.f('ix_user_username'), table_name='user')
    op.drop_index(op.f('ix_user_email'), table_name='user')
    
    # Drop all tables
    op.drop_table('system_health')
    op.drop_table('backup_history')
    op.drop_table('backup_job')
    op.drop_table('alert')
    op.drop_table('share')
    op.drop_table('storage_device')
    op.drop_table('storage_pool')
    op.drop_table('user')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS destinationtype')
    op.execute('DROP TYPE IF EXISTS sourcetype')
    op.execute('DROP TYPE IF EXISTS backupstatus')
    op.execute('DROP TYPE IF EXISTS alertseverity')
    op.execute('DROP TYPE IF EXISTS devicestatus')
    op.execute('DROP TYPE IF EXISTS poolstatus')
    op.execute('DROP TYPE IF EXISTS sharestatus')
    op.execute('DROP TYPE IF EXISTS shareprotocol')
    op.execute('DROP TYPE IF EXISTS userrole')