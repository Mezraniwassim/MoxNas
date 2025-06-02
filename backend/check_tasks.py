#!/usr/bin/env python3
"""
Check Proxmox tasks to debug container creation
"""

from proxmoxer import ProxmoxAPI
import urllib3
from secure_config import SecureConfig
urllib3.disable_warnings()

def check_tasks():
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
        
        # Get recent tasks
        tasks = api.nodes('pve').tasks.get(limit=20)
        
        print("Recent Proxmox tasks:")
        print("-" * 80)
        for task in tasks:
            task_type = task.get('type', 'unknown')
            task_id = task.get('id', 'unknown')
            status = task.get('status', 'unknown')
            exitstatus = task.get('exitstatus', 'unknown')
            starttime = task.get('starttime', 'unknown')
            endtime = task.get('endtime', 'unknown')
            
            print(f"Task: {task_type} | ID: {task_id} | Status: {status} | Exit: {exitstatus}")
            print(f"  Start: {starttime} | End: {endtime}")
            
            # If it's a container creation task, get more details
            if task_type == 'vzcreate':
                try:
                    upid = task.get('upid')
                    if upid:
                        task_log = api.nodes('pve').tasks(upid).log.get()
                        print(f"  Log entries: {len(task_log)}")
                        if task_log:
                            print(f"  Last log: {task_log[-1].get('t', '')}")
                        
                        # Check task status
                        task_status = api.nodes('pve').tasks(upid).status.get()
                        print(f"  Task status: {task_status.get('status', 'unknown')}")
                        
                except Exception as e:
                    print(f"  Error getting task details: {e}")
            
            print("-" * 40)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_tasks()
