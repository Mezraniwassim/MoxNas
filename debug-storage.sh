#!/bin/bash

echo "=== Proxmox Storage Debug ==="
echo
echo "All storage:"
pvesm status
echo
echo "Active storage (excluding local):"
pvesm status | awk 'NR>1 && $3=="active" && $1!="local" {print $1}'
echo
echo "Available storage for containers:"
for storage in local-lvm local-zfs pve-storage data; do
    if pvesm status | grep -q "^$storage"; then
        echo "Found: $storage"
    fi
done
echo
echo "Recommended command:"
echo "Try using: pct create 201 /var/lib/vz/template/cache/ubuntu-22.04-standard_22.04-1_amd64.tar.zst --rootfs local-lvm:32"