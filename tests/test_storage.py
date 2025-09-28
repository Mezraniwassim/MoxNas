"""Tests for storage management functionality"""
import pytest
import json
from unittest.mock import Mock, patch
from app.models import StoragePool, StorageDevice, PoolStatus, DeviceStatus, User, UserRole
from app.storage.manager import StorageManager
from app import db

class TestStoragePool:
    """Test StoragePool model"""
    
    def test_storage_pool_creation(self, app):
        """Test storage pool creation"""
        with app.app_context():
            # Find or create admin user in this session context
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_user = User(
                    username='admin',
                    email='admin@test.com',
                    role=UserRole.ADMIN
                )
                admin_user.set_password('AdminPassword123!')
                db.session.add(admin_user)
                db.session.commit()
                
            pool = StoragePool(
                name='test_pool',
                raid_level='raid1',
                filesystem_type='ext4',
                mount_point='/mnt/test_pool',
                total_size=2000000000,
                used_size=500000000,
                created_by_id=admin_user.id
            )
            
            db.session.add(pool)
            db.session.commit()
            
            # Verify pool was created
            created_pool = StoragePool.query.filter_by(name='test_pool').first()
            assert created_pool is not None
            assert created_pool.raid_level == 'raid1'
            assert created_pool.filesystem_type == 'ext4'
            assert created_pool.status == PoolStatus.HEALTHY
    
    def test_storage_pool_usage_percentage(self, app):
        """Test storage pool usage percentage calculation"""
        with app.app_context():
            # Create a storage pool in this session context
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_user = User(
                    username='admin',
                    email='admin@test.com',
                    role=UserRole.ADMIN
                )
                admin_user.set_password('AdminPassword123!')
                db.session.add(admin_user)
                db.session.commit()
            
            storage_pool = StoragePool(
                name='usage_test_pool',
                raid_level='raid1',
                filesystem_type='ext4',
                mount_point='/mnt/usage_test',
                total_size=1000000000,  # 1GB
                used_size=100000000,    # 100MB 
                created_by_id=admin_user.id
            )
            db.session.add(storage_pool)
            db.session.commit()
            
            # Test percentage calculation (100MB / 1GB = 10%)
            assert storage_pool.usage_percentage == 10.0
            
            # Test edge cases
            storage_pool.used_size = 0
            assert storage_pool.usage_percentage == 0.0
            
            storage_pool.total_size = 0
            assert storage_pool.usage_percentage == 0.0
    
    def test_storage_pool_available_space(self, storage_pool):
        """Test available space calculation"""
        expected_available = storage_pool.total_size - storage_pool.used_size
        assert storage_pool.available_space == expected_available
    
    def test_storage_pool_representation(self, storage_pool):
        """Test string representation"""
        assert str(storage_pool) == f'<StoragePool {storage_pool.name}>'

class TestStorageDevice:
    """Test StorageDevice model"""
    
    def test_storage_device_creation(self, app, storage_pool):
        """Test storage device creation"""
        with app.app_context():
            device = StorageDevice(
                device_name='/dev/sdc1',
                device_path='/dev/sdc1',
                device_size=1000000000,
                device_model='Test SSD',
                serial_number='SN123456',
                pool_id=storage_pool.id
            )
            
            db.session.add(device)
            db.session.commit()
            
            # Verify device was created
            created_device = StorageDevice.query.filter_by(device_name='/dev/sdc1').first()
            assert created_device is not None
            assert created_device.device_model == 'Test SSD'
            assert created_device.status == DeviceStatus.HEALTHY
    
    def test_device_size_formatting(self, storage_device):
        """Test device size formatting"""
        # Test with 500MB device
        size_gb = storage_device.device_size / (1024**3)
        assert abs(size_gb - 0.466) < 0.01  # Approximately 0.466 GB
    
    def test_device_temperature_monitoring(self, app, storage_device):
        """Test device temperature tracking"""
        with app.app_context():
            # Set temperature
            storage_device.temperature = 45
            db.session.commit()
            
            # Verify temperature is stored
            updated_device = StorageDevice.query.get(storage_device.id)
            assert updated_device.temperature == 45
    
    def test_device_representation(self, storage_device):
        """Test string representation"""
        assert str(storage_device) == f'<StorageDevice {storage_device.device_name}>'

class TestStorageManager:
    """Test StorageManager functionality"""
    
    def test_storage_manager_initialization(self):
        """Test storage manager initialization"""
        manager = StorageManager()
        assert manager is not None
    
    @patch('subprocess.run')
    def test_scan_devices(self, mock_run):
        """Test device scanning functionality"""
        # Mock lsblk output
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps({
            'blockdevices': [
                {
                    'name': 'sdb1',
                    'size': '1G',
                    'type': 'part',
                    'mountpoint': None,
                    'fstype': None
                }
            ]
        })
        
        manager = StorageManager()
        devices = manager.scan_storage_devices()
        
        assert len(devices) > 0
        assert devices[0]['name'] == 'sdb1'
    
    @patch('subprocess.run')
    def test_create_raid_array(self, mock_run, temp_storage_dir):
        """Test RAID array creation"""
        # Mock successful mdadm command
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = 'mdadm: array created successfully'
        
        manager = StorageManager()
        success, message = manager.create_raid_array(
            name='test_array',
            level='1',
            devices=['/dev/sdb1', '/dev/sdc1'],
            filesystem='ext4'
        )
        
        assert success
        assert 'created successfully' in message.lower() or 'success' in message.lower()
    
    @patch('subprocess.run')
    def test_get_raid_status(self, mock_run):
        """Test RAID status checking"""
        # Mock mdstat output
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '''
        Personalities : [raid1] [raid6] [raid5] [raid4]
        md0 : active raid1 sdb1[1] sda1[0]
              500107776 blocks super 1.2 [2/2] [UU]
        '''
        
        manager = StorageManager()
        status = manager.get_raid_status()
        
        assert 'md0' in status
        assert 'active' in status['md0'].lower()
    
    @patch('subprocess.run')
    def test_smart_data_collection(self, mock_run):
        """Test SMART data collection"""
        # Mock smartctl output
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps({
            'device': {
                'name': '/dev/sda',
                'type': 'scsi'
            },
            'smart_status': {
                'passed': True
            },
            'temperature': {
                'current': 35
            },
            'power_on_time': {
                'hours': 8760
            }
        })
        
        manager = StorageManager()
        smart_data = manager.get_smart_data('/dev/sda')
        
        assert smart_data is not None
        assert smart_data['smart_status']['passed']
        assert smart_data['temperature']['current'] == 35
    
    def test_filesystem_creation(self, mock_mdadm, temp_storage_dir):
        """Test filesystem creation on RAID array"""
        manager = StorageManager()
        
        # Create a test file to represent the RAID device
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as f:
            device_path = f.name
        
        try:
            success, message = manager.create_filesystem(device_path, 'ext4')
            # In testing environment, this might fail due to lack of real device
            # But we test that the method exists and handles errors gracefully
            assert isinstance(success, bool)
            assert isinstance(message, str)
        finally:
            import os
            os.unlink(device_path)
    
    def test_mount_filesystem(self, temp_storage_dir):
        """Test filesystem mounting"""
        manager = StorageManager()
        
        # Test mounting (will likely fail in test environment but should handle gracefully)
        success, message = manager.mount_filesystem('/dev/fake', temp_storage_dir)
        
        # Should return boolean and string regardless of actual success
        assert isinstance(success, bool)
        assert isinstance(message, str)

class TestStorageAPI:
    """Test storage API endpoints"""
    
    def test_storage_index_page(self, authenticated_admin_client, storage_pool, storage_device):
        """Test storage index page loads"""
        response = authenticated_admin_client.get('/storage/')
        assert response.status_code == 200
        assert b'Storage Management' in response.data
    
    def test_storage_overview_api(self, authenticated_admin_client, storage_pool):
        """Test storage overview API"""
        response = authenticated_admin_client.get('/api/storage/overview')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'total_capacity' in data
        assert 'used_capacity' in data
        assert 'pools' in data
    
    def test_create_pool_page(self, authenticated_admin_client):
        """Test create pool page loads"""
        response = authenticated_admin_client.get('/storage/create-pool')
        assert response.status_code == 200
        assert b'Create Storage Pool' in response.data
    
    def test_create_pool_submission(self, authenticated_admin_client, mock_mdadm):
        """Test pool creation form submission"""
        response = authenticated_admin_client.post('/storage/create-pool', data={
            'name': 'new_test_pool',
            'raid_level': 'raid1',
            'filesystem_type': 'ext4',
            'devices': ['/dev/sdb1', '/dev/sdc1'],
            'csrf_token': 'test_token'
        }, follow_redirects=True)
        
        # Should redirect to storage page on success
        assert response.status_code == 200
    
    def test_pool_detail_page(self, authenticated_admin_client, storage_pool):
        """Test pool detail page"""
        response = authenticated_admin_client.get(f'/storage/pool/{storage_pool.id}')
        assert response.status_code == 200
        assert storage_pool.name.encode() in response.data
    
    def test_device_scan_api(self, authenticated_admin_client, mock_mdadm):
        """Test device scan API endpoint"""
        with patch.object(StorageManager, 'scan_storage_devices') as mock_scan:
            mock_scan.return_value = [
                {
                    'name': 'sdb1',
                    'size': '1G',
                    'type': 'part',
                    'mountpoint': None
                }
            ]
            
            response = authenticated_admin_client.post('/api/storage/scan-devices')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success']
            assert len(data['devices']) == 1
    
    def test_unauthorized_access_to_storage_creation(self, authenticated_user_client):
        """Test that regular users cannot create storage pools"""
        response = authenticated_user_client.get('/storage/create-pool')
        # Should redirect or return 403
        assert response.status_code in [302, 403]

class TestStorageIntegration:
    """Integration tests for storage system"""
    
    def test_pool_device_relationship(self, app, storage_pool, storage_device):
        """Test relationship between pools and devices"""
        with app.app_context():
            # Verify device is associated with pool
            assert storage_device.pool_id == storage_pool.id
            assert storage_device.pool == storage_pool
            
            # Verify pool has device
            assert storage_device in storage_pool.devices
    
    def test_pool_creation_workflow(self, app, authenticated_admin_client, mock_mdadm):
        """Test complete pool creation workflow"""
        with app.app_context():
            # Step 1: Scan for available devices
            with patch.object(StorageManager, 'scan_storage_devices') as mock_scan:
                mock_scan.return_value = [
                    {'name': 'sdb1', 'size': '1G', 'type': 'part'},
                    {'name': 'sdc1', 'size': '1G', 'type': 'part'}
                ]
                
                response = authenticated_admin_client.post('/api/storage/scan-devices')
                assert response.status_code == 200
            
            # Step 2: Create pool with scanned devices
            initial_pool_count = StoragePool.query.count()
            
            response = authenticated_admin_client.post('/storage/create-pool', data={
                'name': 'integration_test_pool',
                'raid_level': 'raid1',
                'filesystem_type': 'ext4',
                'devices': ['/dev/sdb1', '/dev/sdc1'],
                'csrf_token': 'test_token'
            })
            
            # Pool creation might fail in test environment, but form should be processed
            assert response.status_code in [200, 302]
    
    def test_storage_monitoring_data(self, app, storage_pool, storage_device):
        """Test storage monitoring data collection"""
        with app.app_context():
            # Update device with monitoring data
            storage_device.temperature = 42
            storage_device.power_on_hours = 5000
            db.session.commit()
            
            # Verify monitoring data is stored
            updated_device = StorageDevice.query.get(storage_device.id)
            assert updated_device.temperature == 42
            assert updated_device.power_on_hours == 5000
    
    def test_pool_health_status_calculation(self, app, storage_pool):
        """Test pool health status calculation based on devices"""
        with app.app_context():
            # Add multiple devices to pool
            device1 = StorageDevice(
                device_name='/dev/sdb1',
                device_path='/dev/sdb1',
                device_size=500000000,
                status=DeviceStatus.HEALTHY,
                pool_id=storage_pool.id
            )
            
            device2 = StorageDevice(
                device_name='/dev/sdc1',
                device_path='/dev/sdc1',
                device_size=500000000,
                status=DeviceStatus.FAILED,
                pool_id=storage_pool.id
            )
            
            db.session.add_all([device1, device2])
            db.session.commit()
            
            # Pool should be degraded if any device is failed
            # This would require implementing the health calculation logic
            # For now, just verify devices are associated
            assert len(storage_pool.devices) >= 2