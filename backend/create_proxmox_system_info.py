#!/usr/bin/env python3
"""
Create sample system info data for MoxNAS in Proxmox environment
"""

import os
import sys
import django

# Add the backend directory to Python path
sys.path.append('/home/wassim/Documents/MoxNas/backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moxnas.settings')
django.setup()

from system_management.models import SystemInfo
import platform
import psutil
import json

def create_proxmox_system_info():
    """Create system info relevant for Proxmox LXC container environment"""
    
    try:
        # Clear existing system info
        SystemInfo.objects.all().delete()
        print("Cleared existing system info")
        
        # Get actual system info where possible, simulate Proxmox container data
        memory = psutil.virtual_memory()
        load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else [0.1, 0.15, 0.2]
        
        system_info = SystemInfo.objects.create(
            hostname="moxnas-container",
            version="MoxNAS 1.0.0 (Proxmox LXC)",
            uptime=86400,  # 1 day uptime
            cpu_usage=15.5,  # 15.5% CPU usage
            memory_total=memory.total,
            memory_used=int(memory.total * 0.65),  # 65% memory usage
            load_average=f"{load_avg[0]:.2f},{load_avg[1]:.2f},{load_avg[2]:.2f}",
        )
        
        print(f"Created system info for Proxmox container:")
        print(f"  Hostname: {system_info.hostname}")
        print(f"  Version: {system_info.version}")
        print(f"  Memory Usage: {system_info.memory_usage_percentage:.1f}%")
        print(f"  Load Average: {system_info.load_average}")
        print(f"  CPU Usage: {system_info.cpu_usage}%")
        print(f"  Uptime: {system_info.uptime} seconds")
        
    except Exception as e:
        print(f"Error creating system info: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_proxmox_system_info()
