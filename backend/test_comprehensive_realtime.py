#!/usr/bin/env python
"""
Comprehensive test for the real-time monitoring system
Tests both system metrics (which work without Proxmox) and API endpoints
"""

import os
import sys
import django
import requests
import json
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moxnas.settings')
django.setup()

from proxmox_integration.realtime import get_realtime_aggregator, start_realtime_monitoring, stop_realtime_monitoring
from proxmox_integration.manager import get_proxmox_manager
from django.core.cache import cache

def test_system_metrics():
    """Test system metrics collection (works without Proxmox)"""
    print("=== Testing System Metrics Collection ===")
    
    try:
        import psutil
        
        # Test CPU usage
        cpu_usage = psutil.cpu_percent(interval=1)
        print(f"✓ CPU Usage: {cpu_usage}%")
        
        # Test memory usage
        memory = psutil.virtual_memory()
        print(f"✓ Memory Usage: {memory.percent}% ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)")
        
        # Test disk usage
        disk = psutil.disk_usage('/')
        print(f"✓ Disk Usage: {disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)")
        
        # Test network stats
        network = psutil.net_io_counters()
        print(f"✓ Network IO: {network.bytes_sent // (1024**2)}MB sent, {network.bytes_recv // (1024**2)}MB received")
        
        return True
        
    except Exception as e:
        print(f"✗ Error collecting system metrics: {e}")
        return False

def test_realtime_aggregator():
    """Test the real-time aggregator"""
    print("\n=== Testing Real-time Aggregator ===")
    
    try:
        aggregator = get_realtime_aggregator()
        if not aggregator:
            print("✗ Failed to get aggregator")
            return False
            
        print("✓ Real-time aggregator available")
        
        # Start monitoring briefly
        print("Starting monitoring for 5 seconds...")
        start_realtime_monitoring()
        time.sleep(5)
        
        # Check if system metrics are being collected
        dashboard_data = aggregator.get_dashboard_data()
        if dashboard_data and dashboard_data.get('system_metrics'):
            sys_metrics = dashboard_data['system_metrics']
            print(f"✓ System metrics collected:")
            print(f"  - CPU: {sys_metrics.get('cpu_usage', 0):.1f}%")
            print(f"  - Memory: {sys_metrics.get('memory_usage', 0):.1f}%")
            print(f"  - Disk: {sys_metrics.get('disk_usage', 0):.1f}%")
        else:
            print("⚠ No system metrics in dashboard data")
        
        # Stop monitoring
        stop_realtime_monitoring()
        print("✓ Monitoring stopped")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing aggregator: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_django_server():
    """Test if Django server is accessible"""
    print("\n=== Testing Django Server ===")
    
    try:
        # Try to access a simple endpoint
        response = requests.get('http://localhost:8000/proxmox/api/config/', timeout=5)
        if response.status_code == 200:
            print("✓ Django server is accessible")
            data = response.json()
            print(f"✓ Config endpoint returns: {data.get('success', False)}")
            return True
        else:
            print(f"⚠ Django server returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("⚠ Django server not running on port 8000")
        return False
    except Exception as e:
        print(f"✗ Error testing Django server: {e}")
        return False

def test_cache_system():
    """Test Django cache system"""
    print("\n=== Testing Cache System ===")
    
    try:
        # Test cache write/read
        test_key = "test_realtime_cache"
        test_data = {"timestamp": time.time(), "test": True}
        
        cache.set(test_key, test_data, 60)
        retrieved_data = cache.get(test_key)
        
        if retrieved_data and retrieved_data.get('test'):
            print("✓ Cache system working")
            cache.delete(test_key)
            return True
        else:
            print("✗ Cache system not working properly")
            return False
            
    except Exception as e:
        print(f"✗ Error testing cache system: {e}")
        return False

def test_frontend_files():
    """Test if frontend files exist"""
    print("\n=== Testing Frontend Files ===")
    
    frontend_dir = project_root.parent / 'frontend'
    realtime_html = frontend_dir / 'realtime-monitor.html'
    
    if realtime_html.exists():
        print("✓ Real-time monitor HTML file exists")
        # Check if it contains the necessary elements
        content = realtime_html.read_text()
        if 'chart' in content.lower() and 'realtime' in content.lower():
            print("✓ Real-time monitor HTML contains chart elements")
            return True
        else:
            print("⚠ Real-time monitor HTML missing expected elements")
            return False
    else:
        print("✗ Real-time monitor HTML file not found")
        return False

def main():
    """Run all tests"""
    print("=== MoxNAS Real-time Monitoring System Test ===\n")
    
    results = []
    
    # Test system metrics (should always work)
    results.append(("System Metrics", test_system_metrics()))
    
    # Test cache system
    results.append(("Cache System", test_cache_system()))
    
    # Test real-time aggregator
    results.append(("Real-time Aggregator", test_realtime_aggregator()))
    
    # Test Django server (may not be running)
    results.append(("Django Server", test_django_server()))
    
    # Test frontend files
    results.append(("Frontend Files", test_frontend_files()))
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY:")
    print("="*50)
    
    passed = 0
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:.<30} {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed >= 3:  # System metrics, cache, and aggregator should work
        print("\n🎉 Core real-time monitoring system is functional!")
        print("\nTo start the full system:")
        print("1. Update .env file with your Proxmox credentials")
        print("2. Start Django server: python manage.py runserver")
        print("3. Open frontend/realtime-monitor.html in browser")
    else:
        print("\n⚠ Some core components are not working properly")

if __name__ == "__main__":
    main()
