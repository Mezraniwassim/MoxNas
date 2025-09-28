"""Test configuration and fixtures for MoxNAS"""
import pytest
import tempfile
import os
import shutil
from datetime import datetime
from app import create_app, db
from app.models import (
    User, UserRole, StoragePool, StorageDevice, Share, 
    ShareProtocol, Alert, AlertSeverity, BackupJob, SourceType, DestinationType
)

@pytest.fixture
def smb_share(app):
    """Create test SMB share"""
    with app.app_context():
        # Create/get admin user in this session
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@moxnas.local',
                role=UserRole.ADMIN,
                first_name='Admin',
                last_name='User'
            )
            admin_user.set_password('AdminPassword123!')
            db.session.add(admin_user)
            db.session.commit()
        
        # Create/get storage pool in this session
        storage_pool = StoragePool.query.filter_by(name='test_pool').first()
        if not storage_pool:
            storage_pool = StoragePool(
                name='test_pool',
                raid_level='raid1',
                filesystem_type='ext4',
                mount_point='/mnt/test_pool',
                total_size=1000000000,
                used_size=100000000,
                created_by_id=admin_user.id
            )
            db.session.add(storage_pool)
            db.session.commit()
        
        # Create dataset
        from app.models import Dataset
        dataset = Dataset(
            name='test_smb_dataset',
            path='/mnt/storage/test_smb',
            pool_id=storage_pool.id,
            created_by_id=admin_user.id
        )
        db.session.add(dataset)
        db.session.flush()
        
        share = Share(
            name='test_smb_share',
            protocol=ShareProtocol.SMB,
            dataset_id=dataset.id,
            path='/mnt/storage/test_smb',
            read_only=True,
            guest_access=True,
            owner_id=admin_user.id,
            created_by_id=admin_user.id
        )
        db.session.add(share)
        db.session.commit()
        
        # Ensure the share is attached to the current session
        db.session.refresh(share)
        return share

@pytest.fixture
def app():
    """Create and configure a test app instance"""
    # Create a temporary directory for test database
    db_fd, db_path = tempfile.mkstemp()
    
    # Set environment variables for test configuration
    os.environ['TESTING'] = 'True'
    os.environ['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    os.environ['WTF_CSRF_ENABLED'] = 'False'
    os.environ['SECRET_KEY'] = 'test-secret-key-32-characters-long'
    os.environ['CELERY_TASK_ALWAYS_EAGER'] = 'True'
    os.environ['CELERY_TASK_EAGER_PROPAGATES'] = 'True'
    os.environ['SECURITY_HARDENING_ENABLED'] = 'False'  # Disable security hardening in tests
    os.environ['RATELIMIT_ENABLED'] = 'False'  # Disable rate limiting in tests
    
    app = create_app('testing')
    
    with app.app_context():
        # Import models after app creation to avoid circular imports
        from app import models
        db.create_all()
        yield app
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """Test client for making requests"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Test CLI runner"""
    return app.test_cli_runner()

@pytest.fixture
def admin_user(app):
    """Create admin user for testing"""
    with app.app_context():
        # Check if user already exists
        user = User.query.filter_by(username='admin').first()
        if not user:
            user = User(
                username='admin',
                email='admin@test.com',
                role=UserRole.ADMIN,
                first_name='Admin',
                last_name='User'
            )
            user.set_password('AdminPassword123!')
            user.is_active = True
            db.session.add(user)
            db.session.commit()
        # Refresh the user object to ensure it's attached to the current session
        db.session.refresh(user)
        return user

@pytest.fixture
def regular_user(app):
    """Create regular user for testing"""
    with app.app_context():
        # Check if user already exists
        user = User.query.filter_by(username='testuser').first()
        if not user:
            user = User(
                username='testuser',
                email='user@test.com',
                role=UserRole.USER,
                first_name='Test',
                last_name='User'
            )
            user.set_password('UserPassword123!')
            user.is_active = True
            db.session.add(user)
            db.session.commit()
        return user

@pytest.fixture
def authenticated_admin_client(client, app):
    """Client authenticated as admin user"""
    with app.app_context():
        # Find or create admin user in this session context
        user = User.query.filter_by(username='admin').first()
        if not user:
            user = User(
                username='admin',
                email='admin@moxnas.local',
                role=UserRole.ADMIN,
                first_name='Admin',
                last_name='User'
            )
            user.set_password('AdminPassword123!')
            db.session.add(user)
            db.session.commit()
        
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['_fresh'] = True
    return client

@pytest.fixture
def authenticated_user_client(client, app):
    """Client authenticated as regular user"""
    with app.app_context():
        # Find or create regular user in this session context
        user = User.query.filter_by(username='testuser').first()
        if not user:
            user = User(
                username='testuser',
                email='test@moxnas.local',
                role=UserRole.USER,
                first_name='Test',
                last_name='User'
            )
            user.set_password('UserPassword123!')
            db.session.add(user)
            db.session.commit()
        
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['_fresh'] = True
    return client

@pytest.fixture
def storage_pool(app):
    """Create test storage pool"""
    with app.app_context():
        # Find or create admin user in this session context
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@moxnas.local',
                role=UserRole.ADMIN,
                first_name='Admin',
                last_name='User'
            )
            admin_user.set_password('AdminPassword123!')
            db.session.add(admin_user)
            db.session.commit()
            
        # Check if pool already exists
        pool = StoragePool.query.filter_by(name='test_pool').first()
        if not pool:
            pool = StoragePool(
                name='test_pool',
                raid_level='raid1',
                filesystem_type='ext4',
                mount_point='/mnt/test_pool',
                total_size=1000000000,  # 1GB
                used_size=100000000,    # 100MB
                created_by_id=admin_user.id
            )
            db.session.add(pool)
            db.session.commit()
        
        # Refresh the pool object to ensure it's attached to the current session
        db.session.refresh(pool)
        return pool

@pytest.fixture
def storage_device(app, storage_pool):
    """Create test storage device"""
    with app.app_context():
        # Refresh the pool object in the current session
        storage_pool = db.session.merge(storage_pool)
        device = StorageDevice(
            device_name='/dev/sdb1',
            device_path='/dev/sdb1',
            device_size=500000000,  # 500MB
            device_model='Test Drive',
            device_serial='TEST123',
            pool_id=storage_pool.id
        )
        db.session.add(device)
        db.session.commit()
        return device

@pytest.fixture
def nfs_share(app):
    """Create test NFS share"""
    with app.app_context():
        # Create/get admin user in this session
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@moxnas.local',
                role=UserRole.ADMIN,
                first_name='Admin',
                last_name='User'
            )
            admin_user.set_password('AdminPassword123!')
            db.session.add(admin_user)
            db.session.commit()
        
        # Create/get storage pool in this session
        storage_pool = StoragePool.query.filter_by(name='test_pool').first()
        if not storage_pool:
            storage_pool = StoragePool(
                name='test_pool',
                raid_level='raid1',
                filesystem_type='ext4',
                mount_point='/mnt/test_pool',
                total_size=1000000000,
                used_size=100000000,
                created_by_id=admin_user.id
            )
            db.session.add(storage_pool)
            db.session.commit()
        
        # Create dataset
        from app.models import Dataset
        dataset = Dataset(
            name='test_dataset',
            path='/mnt/storage/test_nfs',
            pool_id=storage_pool.id,
            created_by_id=admin_user.id
        )
        db.session.add(dataset)
        db.session.flush()
        
        share = Share(
            name='test_nfs_share',
            protocol=ShareProtocol.NFS,
            dataset_id=dataset.id,
            path='/mnt/storage/test_nfs',
            read_only=False,
            guest_access=False,
            owner_id=admin_user.id,
            created_by_id=admin_user.id
        )
        db.session.add(share)
        db.session.commit()
        
        # Ensure the share is attached to the current session
        db.session.refresh(share)
        return share


@pytest.fixture
def test_alert(app):
    """Create test alert"""
    with app.app_context():
        alert = Alert(
            title='Test Alert',
            message='This is a test alert message',
            severity=AlertSeverity.WARNING,
            component='test'
        )
        db.session.add(alert)
        db.session.commit()
        return alert

@pytest.fixture
def backup_job(app, admin_user):
    """Create test backup job"""
    with app.app_context():
        job = BackupJob(
            name='Test Backup Job',
            source_type=SourceType.DIRECTORY,
            source_path='/mnt/storage',
            destination_type=DestinationType.DIRECTORY,
            destination_path='/mnt/backups/test',
            schedule='0 2 * * *',  # Daily at 2 AM
            compression=True,
            encryption=False,
            retention_days=30,
            created_by_id=admin_user.id
        )
        db.session.add(job)
        db.session.commit()
        return job

@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory for testing"""
    temp_dir = tempfile.mkdtemp(prefix='moxnas_test_storage_')
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def temp_backup_dir():
    """Create temporary backup directory for testing"""
    temp_dir = tempfile.mkdtemp(prefix='moxnas_test_backup_')
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def mock_mdadm(monkeypatch):
    """Mock mdadm commands for testing"""
    def mock_run(*args, **kwargs):
        class MockResult:
            returncode = 0
            stdout = "mock_output"
            stderr = ""
        return MockResult()
    
    import subprocess
    monkeypatch.setattr(subprocess, 'run', mock_run)

@pytest.fixture
def mock_smartctl(monkeypatch):
    """Mock smartctl commands for testing"""
    def mock_run(*args, **kwargs):
        class MockResult:
            returncode = 0
            stdout = '''
            {
                "device": {
                    "name": "/dev/sda",
                    "model_name": "Test Drive"
                },
                "smart_status": {
                    "passed": true
                },
                "temperature": {
                    "current": 35
                },
                "power_on_time": {
                    "hours": 1000
                }
            }
            '''
            stderr = ""
        return MockResult()
    
    import subprocess
    monkeypatch.setattr(subprocess, 'run', mock_run)

@pytest.fixture
def mock_samba_commands(monkeypatch):
    """Mock Samba-related commands"""
    def mock_run(*args, **kwargs):
        class MockResult:
            returncode = 0
            stdout = "mock_samba_output"
            stderr = ""
        return MockResult()
    
    import subprocess
    monkeypatch.setattr(subprocess, 'run', mock_run)

@pytest.fixture
def mock_nfs_commands(monkeypatch):
    """Mock NFS-related commands"""
    def mock_run(*args, **kwargs):
        class MockResult:
            returncode = 0
            stdout = "mock_nfs_output"
            stderr = ""
        return MockResult()
    
    import subprocess
    monkeypatch.setattr(subprocess, 'run', mock_run)

@pytest.fixture
def sample_system_metrics():
    """Sample system metrics data for testing"""
    return {
        'cpu_usage': 45.2,
        'memory_usage': 65.8,
        'disk_usage': 78.3,
        'load_average': 1.2,
        'network_io': {
            'bytes_sent': 1024000,
            'bytes_recv': 2048000
        },
        'disk_io': {
            'read_bytes': 5120000,
            'write_bytes': 3072000
        }
    }

@pytest.fixture
def mock_celery(monkeypatch):
    """Mock Celery tasks for testing"""
    class MockTask:
        def delay(self, *args, **kwargs):
            return MockAsyncResult()
        
        def apply_async(self, *args, **kwargs):
            return MockAsyncResult()
    
    class MockAsyncResult:
        def __init__(self):
            self.id = 'test-task-id'
            self.state = 'SUCCESS'
            self.result = 'test-result'
        
        def ready(self):
            return True
        
        def successful(self):
            return True
        
        def get(self):
            return self.result
    
    # Mock all task functions
    from app import tasks
    for attr_name in dir(tasks):
        attr = getattr(tasks, attr_name)
        if hasattr(attr, 'delay'):
            monkeypatch.setattr(tasks, attr_name, MockTask())

class TestData:
    """Test data constants"""
    
    VALID_EMAIL = 'test@example.com'
    VALID_USERNAME = 'testuser123'
    VALID_PASSWORD = 'TestPassword123!'
    ADMIN_PASSWORD = 'AdminPassword123!'
    USER_PASSWORD = 'UserPassword123!'
    
    STORAGE_DEVICE = {
        'device_name': '/dev/sdc1',
        'device_path': '/dev/sdc1',
        'device_size': 1000000000,
        'device_model': 'Test Storage Device',
        'serial_number': 'SN123456789'
    }
    
    STORAGE_POOL = {
        'name': 'test_pool_2',
        'raid_level': 'raid0',
        'filesystem_type': 'ext4'
    }
    
    NFS_SHARE = {
        'name': 'test_nfs_share_2',
        'protocol': 'nfs',
        'path': '/mnt/storage/nfs_test',
        'read_only': False,
        'guest_access': False
    }
    
    SMB_SHARE = {
        'name': 'test_smb_share_2',
        'protocol': 'smb',
        'path': '/mnt/storage/smb_test',
        'read_only': True,
        'guest_access': True
    }
    
    BACKUP_JOB = {
        'name': 'Test Daily Backup',
        'source_type': 'directory',
        'source_path': '/mnt/storage/important',
        'destination_type': 'directory',
        'destination_path': '/mnt/backups/daily',
        'schedule': '0 3 * * *',
        'compression': True,
        'encryption': True,
        'retention_days': 7
    }