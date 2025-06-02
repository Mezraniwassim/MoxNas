#!/usr/bin/env python3
"""
Check container status directly
"""

from proxmoxer import ProxmoxAPI
import urllib3
from secure_config import SecureConfig
urllib3.disable_warnings()

def check_containers():
    try:
        # Get secure configuration
        config = SecureConfig.get_proxmox_config()
        
        if not config['host'] or not config['password']:
            print("❌ Proxmox connection parameters not configured in .env file")
            return
        
        api = ProxmoxAPI(
            config['host'], 
            user=config['user'], 
            password=config['password'], 
            verify_ssl=config['verify_ssl']
        )
        containers = api.nodes('pve').lxc.get()
        
        print(f"Total containers: {len(containers)}")
        print("\nAll containers:")
        for c in sorted(containers, key=lambda x: int(x['vmid'])):
            print(f"  VMID {c['vmid']}: {c['name']} ({c['status']})")
        
        # Check for container 950 specifically
        target_vmids = [950, 996, 997, 999]
        for vmid in target_vmids:
            try:
                config = api.nodes('pve').lxc(str(vmid)).config.get()
                status = api.nodes('pve').lxc(str(vmid)).status.current.get()
                print(f"\n✅ Container {vmid} exists:")
                print(f"   Hostname: {config.get('hostname', 'unknown')}")
                print(f"   Status: {status.get('status', 'unknown')}")
                print(f"   RootFS: {config.get('rootfs', 'unknown')}")
            except Exception as e:
                print(f"❌ Container {vmid} not found")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_containers()
