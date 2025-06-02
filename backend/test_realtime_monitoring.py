#!/usr/bin/env python
"""
Test script for real-time monitoring system
"""

import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moxnas.settings')
django.setup()

from proxmox_integration.realtime import get_realtime_aggregator, start_realtime_monitoring, stop_realtime_monitoring
from proxmox_integration.manager import get_proxmox_manager
import time
import json

def test_realtime_monitoring():
    """Test the real-time monitoring system"""
    print("=== Testing Real-time Monitoring System ===")
    
    # Test 1: Check if Proxmox manager is available
    print("\n1. Testing Proxmox Manager Connection...")
    manager = get_proxmox_manager()
    if manager:
        print(f"✓ Proxmox manager available (host: {manager.host})")
        print(f"✓ Connection status: {manager.is_connected}")
    else:
        print("✗ No Proxmox manager available")
    
    # Test 2: Get real-time aggregator
    print("\n2. Testing Real-time Aggregator...")
    aggregator = get_realtime_aggregator()
    if aggregator:
        print("✓ Real-time aggregator available")
    else:
        print("✗ Failed to get real-time aggregator")
        return
    
    # Test 3: Start monitoring
    print("\n3. Starting Real-time Monitoring...")
    try:
        start_realtime_monitoring()
        print("✓ Real-time monitoring started")
        
        # Wait a bit for data collection
        print("Waiting 10 seconds for data collection...")
        time.sleep(10)
        
        # Test 4: Get dashboard data
        print("\n4. Testing Dashboard Data...")
        dashboard_data = aggregator.get_dashboard_data()
        if dashboard_data:
            print("✓ Dashboard data available")
            print(f"  - System metrics: {'✓' if dashboard_data.get('system_metrics') else '✗'}")
            print(f"  - Node metrics: {'✓' if dashboard_data.get('node_metrics') else '✗'}")
            print(f"  - Last updated: {dashboard_data.get('last_updated', 'Never')}")
            
            # Print some sample data
            if dashboard_data.get('system_metrics'):
                sys_metrics = dashboard_data['system_metrics']
                print(f"  - CPU Usage: {sys_metrics.get('cpu_usage', 0):.1f}%")
                print(f"  - Memory Usage: {sys_metrics.get('memory_usage', 0):.1f}%")
                print(f"  - Disk Usage: {sys_metrics.get('disk_usage', 0):.1f}%")
        else:
            print("✗ No dashboard data available")
        
        # Test 5: Stop monitoring
        print("\n5. Stopping Real-time Monitoring...")
        stop_realtime_monitoring()
        print("✓ Real-time monitoring stopped")
        
    except Exception as e:
        print(f"✗ Error during monitoring test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_realtime_monitoring()
