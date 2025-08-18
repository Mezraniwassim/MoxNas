"""
Integration tests for MoxNAS service management system
"""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status

from apps.services.managers import samba_manager, nfs_manager, ftp_manager
from apps.services.templates import template_engine
from apps.shares.models import SMBShare, NFSShare
from apps.storage.models import Disk, MountPoint


class ServiceTemplateEngineTests(TestCase):
    """Test the service template engine"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_config_path = os.path.join(self.temp_dir, 'test.conf')
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_path_validation_existing_path(self):
        """Test path validation for existing paths"""
        result = template_engine.validate_path(self.temp_dir, must_exist=True)
        self.assertTrue(result)
    
    def test_path_validation_missing_path(self):
        """Test path validation for missing paths"""
        missing_path = os.path.join(self.temp_dir, 'missing')
        
        with self.assertRaises(ValidationError):
            template_engine.validate_path(missing_path, must_exist=True)
    
    def test_path_creation(self):
        """Test automatic path creation"""
        new_path = os.path.join(self.temp_dir, 'new_directory')
        
        result = template_engine.validate_path(new_path, create_if_missing=True)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(new_path))
    
    def test_config_writing_and_backup(self):
        """Test configuration writing with backup"""
        # Create initial config
        initial_content = "# Initial configuration"
        with open(self.test_config_path, 'w') as f:
            f.write(initial_content)
        
        # Write new config
        new_content = "# New configuration"
        template_engine.write_config(self.test_config_path, new_content)
        
        # Verify new content
        with open(self.test_config_path, 'r') as f:
            self.assertEqual(f.read(), new_content)
        
        # Verify backup was created
        backup_files = list(Path(template_engine.backup_dir).glob(f"{Path(self.test_config_path).name}.*"))
        self.assertTrue(len(backup_files) > 0)


class SambaManagerTests(TestCase):
    """Test Samba service management"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        
        # Create test disk and mount point
        self.disk = Disk.objects.create(
            device='/dev/test',
            name='Test Disk',
            size=1000000000,
            is_mounted=True
        )
        
        self.mount_point = MountPoint.objects.create(
            path='/mnt/test',
            disk=self.disk,
            filesystem='ext4'
        )
        
        # Create test SMB share
        self.smb_share = SMBShare.objects.create(
            name='test_share',
            path='/mnt/test/share',
            comment='Test Share',
            enabled=True,
            writable=True,
            browseable=True,
            guest_access=False
        )
        self.smb_share.allowed_users.add(self.user)
    
    @patch('subprocess.run')
    def test_samba_config_generation(self, mock_subprocess):
        """Test Samba configuration generation"""
        # Mock successful testparm
        mock_subprocess.return_value = MagicMock(returncode=0, stdout='', stderr='')
        
        # Create test share directory
        os.makedirs('/mnt/test/share', exist_ok=True)
        
        try:
            shares = SMBShare.objects.filter(enabled=True)
            config_content = samba_manager.generate_config(shares)
            
            # Verify config contains expected sections
            self.assertIn('[global]', config_content)
            self.assertIn('[test_share]', config_content)
            self.assertIn('path = /mnt/test/share', config_content)
            self.assertIn('read only = no', config_content)
            
        finally:
            # Cleanup
            shutil.rmtree('/mnt/test', ignore_errors=True)
    
    @patch('subprocess.run')
    def test_samba_config_validation(self, mock_subprocess):
        """Test Samba configuration validation"""
        # Mock successful testparm
        mock_subprocess.return_value = MagicMock(returncode=0, stdout='Valid config', stderr='')
        
        valid, message = samba_manager.test_config()
        self.assertTrue(valid)
        self.assertIn('Valid config', message)
        
        # Mock failed testparm
        mock_subprocess.return_value = MagicMock(returncode=1, stdout='', stderr='Invalid config')
        
        valid, message = samba_manager.test_config()
        self.assertFalse(valid)
        self.assertIn('Invalid config', message)
    
    @patch('subprocess.run')
    def test_service_status_checking(self, mock_subprocess):
        """Test service status checking"""
        # Mock active and enabled service
        mock_subprocess.side_effect = [
            MagicMock(returncode=0, stdout='active\n'),  # is-active
            MagicMock(returncode=0, stdout='enabled\n')  # is-enabled
        ]
        
        status = samba_manager.status()
        self.assertTrue(status['active'])
        self.assertTrue(status['enabled'])
        self.assertEqual(status['status'], 'running')
        
        # Mock inactive service
        mock_subprocess.side_effect = [
            MagicMock(returncode=3, stdout='inactive\n'),
            MagicMock(returncode=1, stdout='disabled\n')
        ]
        
        status = samba_manager.status()
        self.assertFalse(status['active'])
        self.assertFalse(status['enabled'])
        self.assertEqual(status['status'], 'stopped')


class NFSManagerTests(TestCase):
    """Test NFS service management"""
    
    def setUp(self):
        # Create test NFS share
        self.nfs_share = NFSShare.objects.create(
            name='test_nfs',
            path='/mnt/test/nfs',
            network='192.168.1.0/24',
            read_only=False,
            sync=True,
            root_squash=True,
            enabled=True
        )
    
    def test_nfs_exports_generation(self):
        """Test NFS exports generation"""
        # Create test directory
        os.makedirs('/mnt/test/nfs', exist_ok=True)
        
        try:
            exports = NFSShare.objects.filter(enabled=True)
            exports_content = nfs_manager.generate_exports(exports)
            
            # Verify exports contain expected content
            self.assertIn('/mnt/test/nfs', exports_content)
            self.assertIn('192.168.1.0/24', exports_content)
            self.assertIn('rw,sync,root_squash', exports_content)
            
        finally:
            # Cleanup
            shutil.rmtree('/mnt/test', ignore_errors=True)


class ServiceAPITests(APITestCase):
    """Test service management API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.client.force_authenticate(user=self.user)
    
    @patch('apps.services.managers.samba_manager.status')
    @patch('apps.services.managers.nfs_manager.status')
    @patch('apps.services.managers.ftp_manager.status')
    def test_service_status_endpoint(self, mock_ftp_status, mock_nfs_status, mock_samba_status):
        """Test service status API endpoint"""
        # Mock service status responses
        mock_samba_status.return_value = {'active': True, 'enabled': True, 'status': 'running'}
        mock_nfs_status.return_value = {'active': False, 'enabled': True, 'status': 'stopped'}
        mock_ftp_status.return_value = {'active': True, 'enabled': False, 'status': 'running'}
        
        response = self.client.get('/api/services/status/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('services', response.data)
        self.assertIn('samba', response.data['services'])
        self.assertIn('nfs', response.data['services'])
        self.assertIn('ftp', response.data['services'])
        self.assertTrue(response.data['services']['samba']['active'])
        self.assertFalse(response.data['services']['nfs']['active'])
    
    @patch('apps.services.managers.samba_manager.start')
    @patch('apps.services.managers.samba_manager.status')
    def test_service_control_endpoint(self, mock_status, mock_start):
        """Test service control API endpoint"""
        # Mock successful service start
        mock_start.return_value = True
        mock_status.return_value = {'active': True, 'enabled': True, 'status': 'running'}
        
        response = self.client.post('/api/services/control/', {
            'service': 'samba',
            'action': 'start'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Successfully started samba', response.data['message'])
        mock_start.assert_called_once()
    
    def test_service_control_invalid_service(self):
        """Test service control with invalid service name"""
        response = self.client.post('/api/services/control/', {
            'service': 'invalid_service',
            'action': 'start'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Unknown service', response.data['error'])
    
    def test_service_control_missing_parameters(self):
        """Test service control with missing parameters"""
        response = self.client.post('/api/services/control/', {
            'service': 'samba'
            # Missing 'action' parameter
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Both service and action are required', response.data['error'])


class ServiceIntegrationTests(TransactionTestCase):
    """Integration tests for complete service workflow"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        
        # Create test storage
        self.disk = Disk.objects.create(
            device='/dev/test',
            name='Test Disk',
            size=1000000000,
            is_mounted=True
        )
        
        self.mount_point = MountPoint.objects.create(
            path='/mnt/test',
            disk=self.disk,
            filesystem='ext4'
        )
    
    @patch('subprocess.run')
    @patch('apps.services.signals.call_command')
    def test_automatic_config_regeneration(self, mock_call_command, mock_subprocess):
        """Test automatic configuration regeneration on share changes"""
        # Mock successful operations
        mock_subprocess.return_value = MagicMock(returncode=0)
        
        # Create test directory
        os.makedirs('/mnt/test/auto_share', exist_ok=True)
        
        try:
            # Create SMB share - should trigger signal
            smb_share = SMBShare.objects.create(
                name='auto_share',
                path='/mnt/test/auto_share',
                comment='Auto Share',
                enabled=True
            )
            
            # Verify signal was triggered
            mock_call_command.assert_called_with('configure_services', '--service=samba')
            
            # Update share - should trigger signal again
            smb_share.comment = 'Updated Auto Share'
            smb_share.save()
            
            # Verify signal was triggered again
            self.assertEqual(mock_call_command.call_count, 2)
            
        finally:
            # Cleanup
            shutil.rmtree('/mnt/test', ignore_errors=True)
    
    def test_end_to_end_share_creation(self):
        """Test complete end-to-end share creation workflow"""
        # Create test directory
        test_share_path = '/mnt/test/e2e_share'
        os.makedirs(test_share_path, exist_ok=True)
        
        try:
            with patch('subprocess.run') as mock_subprocess:
                # Mock successful operations
                mock_subprocess.return_value = MagicMock(returncode=0, stdout='', stderr='')
                
                # Create SMB share
                smb_share = SMBShare.objects.create(
                    name='e2e_share',
                    path=test_share_path,
                    comment='End-to-End Test Share',
                    enabled=True,
                    writable=True,
                    browseable=True
                )
                smb_share.allowed_users.add(self.user)
                
                # Generate configuration
                shares = SMBShare.objects.filter(enabled=True)
                config_content = samba_manager.generate_config(shares)
                
                # Verify configuration
                self.assertIn('[e2e_share]', config_content)
                self.assertIn(f'path = {test_share_path}', config_content)
                self.assertIn('read only = no', config_content)
                self.assertIn(self.user.username, config_content)
                
        finally:
            # Cleanup
            shutil.rmtree('/mnt/test', ignore_errors=True)


class ServiceManagementCommandTests(TestCase):
    """Test service management Django commands"""
    
    @patch('subprocess.run')
    @patch('apps.services.managers.samba_manager.generate_config')
    @patch('apps.services.managers.samba_manager.test_config')
    def test_configure_services_command(self, mock_test_config, mock_generate_config, mock_subprocess):
        """Test configure_services management command"""
        from django.core.management import call_command
        from io import StringIO
        
        # Mock successful operations
        mock_generate_config.return_value = "# Test config"
        mock_test_config.return_value = (True, "Configuration OK")
        mock_subprocess.return_value = MagicMock(returncode=0)
        
        # Test command execution
        out = StringIO()
        call_command('configure_services', '--service=samba', '--test-only', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Configuring Samba', output)
        self.assertIn('✓ Samba configuration is valid', output)
        mock_generate_config.assert_called_once()
        mock_test_config.assert_called_once()


# Import ValidationError at the top
from django.core.exceptions import ValidationError