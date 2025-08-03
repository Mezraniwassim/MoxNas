import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from apps.proxmox.models import ProxmoxNode
from apps.containers.models import MoxNasContainer


class ProxmoxTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.node = ProxmoxNode.objects.create(
            name='test-node',
            host='192.168.1.100',
            username='root@pam',
            password='testpass'
        )

    def test_proxmox_node_creation(self):
        self.assertEqual(self.node.name, 'test-node')
        self.assertEqual(self.node.host, '192.168.1.100')
        self.assertTrue(self.node.is_active)

    def test_container_creation(self):
        container = MoxNasContainer.objects.create(
            vmid=100,
            name='test-container',
            hostname='test-moxnas',
            node=self.node,
            created_by=self.user
        )
        self.assertEqual(container.vmid, 100)
        self.assertEqual(container.status, 'stopped')
        self.assertFalse(container.is_moxnas_ready)
