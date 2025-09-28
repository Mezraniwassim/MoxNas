"""Fix schema consistency and add missing fields

Revision ID: 002
Revises: 001
Create Date: 2024-08-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fix table names to match models.py
    # Note: This assumes we're starting fresh or can recreate tables
    # For production, you'd need more careful migration steps
    
    # Import inspector for checking table/column existence
    import sqlalchemy as sa
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Only try to add enum values if the types exist
    try:
        op.execute("ALTER TYPE devicestatus ADD VALUE IF NOT EXISTS 'SMART_FAIL'")
        op.execute("ALTER TYPE devicestatus ADD VALUE IF NOT EXISTS 'OFFLINE'")  
        op.execute("ALTER TYPE poolstatus ADD VALUE IF NOT EXISTS 'OFFLINE'")
        op.execute("ALTER TYPE shareprotocol ADD VALUE IF NOT EXISTS 'SFTP'")
        op.execute("ALTER TYPE backupstatus ADD VALUE IF NOT EXISTS 'SCHEDULED'")
        op.execute("ALTER TYPE alertseverity ADD VALUE IF NOT EXISTS 'LOW'")
        op.execute("ALTER TYPE alertseverity ADD VALUE IF NOT EXISTS 'MEDIUM'")
        op.execute("ALTER TYPE alertseverity ADD VALUE IF NOT EXISTS 'HIGH'")
    except Exception as e:
        # If enum types don't exist, skip enum alterations
        print(f"Warning: Could not update enum types: {e}")
        pass
    
    # Create missing enum types
    source_type_enum = postgresql.ENUM('DIRECTORY', 'DEVICE', 'DATASET', name='sourcetype_new', create_type=True)
    destination_type_enum = postgresql.ENUM('DIRECTORY', 'S3', 'REMOTE', 'FTP', name='destinationtype_new', create_type=True)
    log_level_enum = postgresql.ENUM('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', name='loglevel', create_type=True)
    
    # Add missing columns to existing tables
    
    # Users table missing columns - check if columns exist first
    # Add columns only if they don't exist to prevent errors on re-runs
    if inspector.has_table('user'):
        user_columns = [col['name'] for col in inspector.get_columns('user')]
    else:
        user_columns = []
    
    with op.batch_alter_table('user', schema=None) as batch_op:
        if 'backup_codes' not in user_columns:
            batch_op.add_column(sa.Column('backup_codes', sa.Text(), nullable=True))
        if 'updated_at' not in user_columns:
            batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')))
        if 'force_password_change' not in user_columns:
            batch_op.add_column(sa.Column('force_password_change', sa.Boolean(), nullable=True, server_default='false'))
        if 'last_password_change' not in user_columns:
            batch_op.add_column(sa.Column('last_password_change', sa.DateTime(), nullable=True))
        if 'created_by_id' not in user_columns:
            batch_op.add_column(sa.Column('created_by_id', sa.Integer(), nullable=True))
            # Only create foreign key if column was added
            batch_op.create_foreign_key('fk_user_created_by', 'user', ['created_by_id'], ['id'], ondelete='SET NULL')
    
    # Storage pools missing columns - check if table exists
    if inspector.has_table('storage_pool'):
        pool_columns = [col['name'] for col in inspector.get_columns('storage_pool')]
        with op.batch_alter_table('storage_pool', schema=None) as batch_op:
            if 'mount_point' not in pool_columns:
                batch_op.add_column(sa.Column('mount_point', sa.String(255), nullable=True))
            if 'available_size' not in pool_columns:
                batch_op.add_column(sa.Column('available_size', sa.BigInteger(), nullable=True))
            if 'last_scrub' not in pool_columns:
                batch_op.add_column(sa.Column('last_scrub', sa.DateTime(), nullable=True))
            if 'scrub_progress' not in pool_columns:
                batch_op.add_column(sa.Column('scrub_progress', sa.Integer(), nullable=True, server_default='0'))
            if 'auto_scrub_enabled' not in pool_columns:
                batch_op.add_column(sa.Column('auto_scrub_enabled', sa.Boolean(), nullable=True, server_default='true'))
            if 'scrub_schedule' not in pool_columns:
                batch_op.add_column(sa.Column('scrub_schedule', sa.String(128), nullable=True))
            if 'updated_at' not in pool_columns:
                batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')))
            
            # Check if constraint already exists before creating
            constraints = inspector.get_unique_constraints('storage_pool')
            constraint_names = [c['name'] for c in constraints]
            if 'uq_storage_pool_mount_point' not in constraint_names and 'mount_point' not in pool_columns:
                batch_op.create_unique_constraint('uq_storage_pool_mount_point', ['mount_point'])
    
    # Storage devices missing columns
    with op.batch_alter_table('storage_device', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sector_size', sa.Integer(), nullable=True, server_default='512'))
        batch_op.add_column(sa.Column('smart_data', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')))
        batch_op.alter_column('serial_number', new_column_name='device_serial')
    
    # Create missing datasets table (this was completely missing)
    op.create_table('datasets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('path', sa.String(512), nullable=False),
        sa.Column('pool_id', sa.Integer(), nullable=False),
        sa.Column('quota_size', sa.BigInteger(), nullable=True),
        sa.Column('used_size', sa.BigInteger(), nullable=True, server_default='0'),
        sa.Column('owner_uid', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('owner_gid', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('permissions', sa.String(10), nullable=True, server_default='755'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['pool_id'], ['storage_pool.id']),
        sa.ForeignKeyConstraint(['created_by_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('path')
    )
    
    # Fix shares table to reference datasets - only if table exists
    if inspector.has_table('share'):
        share_columns = [col['name'] for col in inspector.get_columns('share')]
        with op.batch_alter_table('share', schema=None) as batch_op:
            if 'owner_id' not in share_columns:
                batch_op.add_column(sa.Column('owner_id', sa.Integer(), nullable=True))
                batch_op.create_foreign_key('fk_share_owner', 'user', ['owner_id'], ['id'], ondelete='SET NULL')
            if 'allowed_hosts' not in share_columns:
                batch_op.add_column(sa.Column('allowed_hosts', sa.Text(), nullable=True))
            if 'bytes_transferred' not in share_columns:
                batch_op.add_column(sa.Column('bytes_transferred', sa.BigInteger(), nullable=True, server_default='0'))
            if 'updated_at' not in share_columns:
                batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')))
            
            # Handle foreign key constraints carefully
            try:
                # Only try to drop if it exists
                fks = inspector.get_foreign_keys('share')
                if any(fk['name'] == 'share_dataset_id_fkey' for fk in fks):
                    batch_op.drop_constraint('share_dataset_id_fkey', type_='foreignkey')
                
                # Create new foreign key to datasets table
                if 'dataset_id' in share_columns:
                    batch_op.create_foreign_key('fk_share_dataset', 'datasets', ['dataset_id'], ['id'], ondelete='CASCADE')
            except Exception:
                # Skip foreign key operations if they fail
                pass
    
    # Create missing system_logs table (instead of system_health)
    op.create_table('system_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('level', log_level_enum, nullable=False),
        sa.Column('category', sa.String(64), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Update alerts table  
    with op.batch_alter_table('alert', schema=None) as batch_op:
        batch_op.add_column(sa.Column('category', sa.String(64), nullable=True))
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'))
        batch_op.add_column(sa.Column('auto_resolve', sa.Boolean(), nullable=True, server_default='false'))
        batch_op.add_column(sa.Column('resolved_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')))
        batch_op.drop_column('acknowledged')  # Replace with acknowledged_at
    
    # Update backup_job table
    with op.batch_alter_table('backup_job', schema=None) as batch_op:
        batch_op.add_column(sa.Column('backup_type', sa.String(32), nullable=True, server_default='incremental'))
        batch_op.add_column(sa.Column('bytes_backed_up', sa.BigInteger(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('error_message', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('retry_count', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('max_retries', sa.Integer(), nullable=True, server_default='3'))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')))
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'))


def downgrade() -> None:
    # Reverse the changes
    op.drop_table('system_logs')
    op.drop_table('datasets')
    
    # Remove added columns (simplified - in production you'd be more careful)
    with op.batch_alter_table('backup_job', schema=None) as batch_op:
        batch_op.drop_column('is_active')
        batch_op.drop_column('updated_at')
        batch_op.drop_column('max_retries')
        batch_op.drop_column('retry_count')
        batch_op.drop_column('error_message')
        batch_op.drop_column('bytes_backed_up')
        batch_op.drop_column('backup_type')
    
    with op.batch_alter_table('alert', schema=None) as batch_op:
        batch_op.add_column(sa.Column('acknowledged', sa.Boolean(), nullable=False, server_default='false'))
        batch_op.drop_column('updated_at')
        batch_op.drop_column('resolved_at')
        batch_op.drop_column('auto_resolve')
        batch_op.drop_column('is_active')
        batch_op.drop_column('category')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS loglevel')
    op.execute('DROP TYPE IF EXISTS destinationtype_new')
    op.execute('DROP TYPE IF EXISTS sourcetype_new')