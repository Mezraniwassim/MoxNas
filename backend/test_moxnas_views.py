#!/usr/bin/env python3
"""
Test MoxNAS views directly without HTTP client
"""

import os
import sys
import django
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moxnas.settings')
django.setup()

def test_proxmox_views():
    """Test Proxmox views directly"""
    print("🌐 Testing MoxNAS Proxmox Views...")
    
    try:
        from proxmox_integration import views
        from django.http import HttpRequest
        
        # Test 1: Frontend config view
        print("\n1️⃣ Testing get_frontend_config view...")
        try:
            request = HttpRequest()
            response = views.get_frontend_config(request)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                import json
                config = json.loads(response.content)
                print(f"   ✅ Frontend config loaded")
                print(f"   📝 Host: {config.get('host', 'not set')}")
                print(f"   📝 Port: {config.get('port', 'not set')}")
            else:
                print(f"   ❌ Frontend config failed")
        except Exception as e:
            print(f"   ❌ Frontend config error: {e}")
        
        # Test 2: Connect Proxmox view
        print("\n2️⃣ Testing connect_proxmox view...")
        try:
            request = HttpRequest()
            request.method = 'POST'
            response = views.connect_proxmox(request)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                import json
                result = json.loads(response.content)
                print(f"   ✅ Connection test completed")
                print(f"   📝 Success: {result.get('success', False)}")
                if result.get('success'):
                    print(f"   📝 Message: {result.get('message', 'No message')}")
                else:
                    print(f"   📝 Error: {result.get('error', 'No error details')}")
            else:
                print(f"   ❌ Connection test failed")
        except Exception as e:
            print(f"   ❌ Connection test error: {e}")
        
        # Test 3: Real-time data view
        print("\n3️⃣ Testing get_realtime_data view...")
        try:
            request = HttpRequest()
            response = views.get_realtime_data(request)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                import json
                data = json.loads(response.content)
                print(f"   ✅ Real-time data working")
                print(f"   📝 Data keys: {list(data.keys())}")
                
                # Show some sample data
                if 'nodes' in data:
                    print(f"   📝 Nodes: {len(data['nodes'])}")
                if 'containers' in data:
                    print(f"   📝 Containers: {len(data['containers'])}")
            else:
                print(f"   ❌ Real-time data failed")
        except Exception as e:
            print(f"   ❌ Real-time data error: {e}")
        
    except Exception as e:
        print(f"❌ Views test failed: {e}")
        import traceback
        traceback.print_exc()

def test_proxmox_viewsets():
    """Test Proxmox ViewSets"""
    print("\n\n🗂️ Testing MoxNAS ViewSets...")
    
    try:
        from proxmox_integration.views import (
            ProxmoxHostViewSet, ProxmoxNodeViewSet, 
            ProxmoxContainerViewSet, ProxmoxStorageViewSet
        )
        
        # Test ViewSet initialization
        print("\n1️⃣ Testing ViewSet initialization...")
        
        host_viewset = ProxmoxHostViewSet()
        print("   ✅ ProxmoxHostViewSet initialized")
        
        node_viewset = ProxmoxNodeViewSet()
        print("   ✅ ProxmoxNodeViewSet initialized")
        
        container_viewset = ProxmoxContainerViewSet()
        print("   ✅ ProxmoxContainerViewSet initialized")
        
        storage_viewset = ProxmoxStorageViewSet()
        print("   ✅ ProxmoxStorageViewSet initialized")
        
        # Test queryset access
        print("\n2️⃣ Testing ViewSet querysets...")
        try:
            hosts = host_viewset.get_queryset()
            print(f"   ✅ Hosts queryset: {hosts.count()} hosts")
        except Exception as e:
            print(f"   ❌ Hosts queryset error: {e}")
        
        try:
            nodes = node_viewset.get_queryset()
            print(f"   ✅ Nodes queryset: {nodes.count()} nodes")
        except Exception as e:
            print(f"   ❌ Nodes queryset error: {e}")
        
        try:
            containers = container_viewset.get_queryset()
            print(f"   ✅ Containers queryset: {containers.count()} containers")
        except Exception as e:
            print(f"   ❌ Containers queryset error: {e}")
        
    except Exception as e:
        print(f"❌ ViewSets test failed: {e}")

def test_live_proxmox_integration():
    """Test live Proxmox integration through views"""
    print("\n\n🔗 Testing Live Proxmox Integration...")
    
    try:
        from proxmox_integration.manager import ProxmoxManager
        from secure_config import SecureConfig
        
        # Get configuration
        config = SecureConfig.get_proxmox_config()
        print(f"📝 Testing with {config['host']}:{config['port']}")
        
        # Test connection through manager
        manager = ProxmoxManager(config)
        
        if manager.connect():
            print("✅ Proxmox connection successful!")
            
            # Test getting live data (similar to what views would do)
            try:
                nodes = manager.get_nodes()
                print(f"✅ Live nodes data: {len(nodes)} nodes")
                for node in nodes:
                    print(f"   - {node.get('node', 'unknown')} ({node.get('status', 'unknown')})")
            except Exception as e:
                print(f"❌ Live nodes error: {e}")
            
            try:
                if nodes:
                    node_name = nodes[0].get('node', 'pve')
                    containers = manager.get_containers(node_name)
                    print(f"✅ Live containers data: {len(containers)} containers")
                    for container in containers[:3]:  # Show first 3
                        print(f"   - {container.get('vmid')}: {container.get('name', 'unnamed')} ({container.get('status')})")
            except Exception as e:
                print(f"❌ Live containers error: {e}")
            
        else:
            print("❌ Proxmox connection failed")
        
    except Exception as e:
        print(f"❌ Live integration test failed: {e}")

def main():
    print("🎯 MoxNAS Application Integration Test")
    print("=" * 50)
    
    test_proxmox_views()
    test_proxmox_viewsets() 
    test_live_proxmox_integration()
    
    print("\n" + "=" * 50)
    print("✨ MoxNAS application test completed!")

if __name__ == "__main__":
    main()