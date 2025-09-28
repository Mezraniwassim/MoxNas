#!/usr/bin/env python3
"""
Détecteur de stockage système adapté pour Ubuntu 24.04
Détecte les vrais disques sans dépendance ZFS/LVM
"""

import os
import subprocess
import json
import re
from typing import List, Dict, Optional
from pathlib import Path

class SystemStorageDetector:
    """Détecteur de stockage pour systèmes Ubuntu sans ZFS/LVM"""
    
    def __init__(self):
        self.devices = []
        
    def scan_block_devices(self) -> List[Dict]:
        """Scanner les périphériques de blocs avec lsblk"""
        try:
            # Utiliser lsblk pour obtenir des informations détaillées
            result = subprocess.run([
                'lsblk', '-J', '-o', 
                'NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,MODEL,SERIAL,UUID,LABEL'
            ], capture_output=True, text=True, timeout=30)
            
            print(f"lsblk returncode: {result.returncode}")
            if result.stderr:
                print(f"lsblk stderr: {result.stderr}")
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                devices = []
                
                print(f"lsblk data: {data}")
                
                for device in data.get('blockdevices', []):
                    print(f"Processing device: {device}")
                    if self._is_real_disk(device):
                        device_info = self._parse_device_info(device)
                        if device_info:
                            devices.append(device_info)
                            print(f"Added device: {device_info['device_name']}")
                        else:
                            print(f"Failed to parse device: {device}")
                    else:
                        print(f"Skipped virtual device: {device.get('name', 'unknown')}")
                            
                return devices
        except json.JSONDecodeError as je:
            print(f"Erreur JSON lors du scan lsblk: {je}")
            print(f"Raw output: {result.stdout}")
        except Exception as e:
            print(f"Erreur lors du scan lsblk: {e}")
        
        return []
    
    def _is_real_disk(self, device: Dict) -> bool:
        """Vérifie si c'est un vrai disque (pas loop, ram, etc.)"""
        name = device.get('name', '')
        device_type = device.get('type', '')
        
        # Exclure les périphériques virtuels
        exclude_patterns = ['loop', 'ram', 'sr', 'fd']
        for pattern in exclude_patterns:
            if name.startswith(pattern):
                return False
                
        # Inclure seulement les disques réels
        return device_type == 'disk' and name.startswith(('sd', 'hd', 'vd', 'nvme'))
    
    def _parse_device_info(self, device: Dict) -> Optional[Dict]:
        """Parse les informations d'un périphérique"""
        try:
            name = device.get('name', '')
            size_str = device.get('size', '0')
            
            # Convertir la taille en bytes
            size_bytes = self._parse_size_to_bytes(size_str)
            
            device_info = {
                'device_path': f"/dev/{name}",
                'device_name': name,
                'device_size': size_bytes,
                'device_size_human': size_str,
                'device_model': device.get('model', 'Unknown'),
                'device_serial': device.get('serial'),
                'filesystem': device.get('fstype'),
                'mountpoint': device.get('mountpoint'),
                'uuid': device.get('uuid'),
                'label': device.get('label'),
                'status': 'healthy',
                'type': 'disk',
                'children': []
            }
            
            # Analyser les partitions
            if 'children' in device:
                for child in device['children']:
                    partition_info = {
                        'device_path': f"/dev/{child.get('name', '')}",
                        'device_name': child.get('name', ''),
                        'device_size': self._parse_size_to_bytes(child.get('size', '0')),
                        'device_size_human': child.get('size', '0'),
                        'filesystem': child.get('fstype'),
                        'mountpoint': child.get('mountpoint'),
                        'uuid': child.get('uuid'),
                        'label': child.get('label'),
                        'type': 'partition'
                    }
                    device_info['children'].append(partition_info)
            
            return device_info
            
        except Exception as e:
            print(f"Erreur lors du parsing du périphérique {device}: {e}")
            return None
    
    def _parse_size_to_bytes(self, size_str: str) -> int:
        """Convertit une taille human-readable en bytes"""
        if not size_str or size_str == '0':
            return 0
            
        # Regex pour parser les tailles (ex: "238.5G", "1.8T")
        match = re.match(r'(\d+\.?\d*)([KMGT]?)', size_str.upper())
        if not match:
            return 0
        
        value, unit = match.groups()
        value = float(value)
        
        multipliers = {
            '': 1,
            'K': 1024,
            'M': 1024**2,
            'G': 1024**3,
            'T': 1024**4
        }
        
        return int(value * multipliers.get(unit, 1))
    
    def get_device_smart_info(self, device_path: str) -> Dict:
        """Obtenir les informations SMART d'un périphérique"""
        try:
            # Essayer d'obtenir des informations SMART avec smartctl
            result = subprocess.run([
                'smartctl', '-i', '-H', device_path
            ], capture_output=True, text=True, timeout=10)
            
            smart_info = {
                'smart_available': result.returncode == 0,
                'health_status': 'unknown',
                'temperature': None,
                'power_on_hours': None
            }
            
            if result.returncode == 0:
                output = result.stdout
                
                # Parser le statut de santé
                if 'PASSED' in output:
                    smart_info['health_status'] = 'healthy'
                elif 'FAILED' in output:
                    smart_info['health_status'] = 'failed'
                
                # Parser la température (approximatif)
                temp_match = re.search(r'Temperature_Celsius.*?(\d+)', output)
                if temp_match:
                    smart_info['temperature'] = int(temp_match.group(1))
                
                # Parser les heures d'utilisation
                hours_match = re.search(r'Power_On_Hours.*?(\d+)', output)
                if hours_match:
                    smart_info['power_on_hours'] = int(hours_match.group(1))
            
            return smart_info
            
        except Exception as e:
            print(f"Erreur SMART pour {device_path}: {e}")
            return {
                'smart_available': False,
                'health_status': 'unknown',
                'temperature': None,
                'power_on_hours': None
            }
    
    def scan_all_devices(self) -> List[Dict]:
        """Scanner tous les périphériques de stockage"""
        print("🔍 Scan des périphériques de stockage...")
        
        devices = self.scan_block_devices()
        
        # Enrichir avec les informations SMART
        for device in devices:
            device_path = device['device_path']
            smart_info = self.get_device_smart_info(device_path)
            device.update(smart_info)
        
        print(f"✅ {len(devices)} périphériques détectés")
        return devices
    
    def get_system_storage_summary(self) -> Dict:
        """Obtenir un résumé du stockage système"""
        devices = self.scan_all_devices()
        
        total_capacity = sum(d['device_size'] for d in devices)
        used_devices = len([d for d in devices if d.get('mountpoint')])
        
        return {
            'total_devices': len(devices),
            'total_capacity': total_capacity,
            'total_capacity_human': self._bytes_to_human(total_capacity),
            'used_devices': used_devices,
            'available_devices': len(devices) - used_devices,
            'devices': devices
        }
    
    def _bytes_to_human(self, bytes_size: int) -> str:
        """Convertir bytes en format human-readable"""
        if bytes_size == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        size = float(bytes_size)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.1f} {units[unit_index]}"

if __name__ == "__main__":
    # Test du détecteur
    detector = SystemStorageDetector()
    summary = detector.get_system_storage_summary()
    
    print("📊 Résumé du stockage système:")
    print(f"  Périphériques totaux: {summary['total_devices']}")
    print(f"  Capacité totale: {summary['total_capacity_human']}")
    print(f"  Périphériques utilisés: {summary['used_devices']}")
    
    print("\n💾 Périphériques détectés:")
    for device in summary['devices']:
        print(f"  {device['device_name']}: {device['device_size_human']} ({device['device_model']})")
        if device.get('mountpoint'):
            print(f"    Monté sur: {device['mountpoint']}")
        for partition in device.get('children', []):
            print(f"    ├── {partition['device_name']}: {partition['device_size_human']} ({partition.get('filesystem', 'unknown')})")
            if partition.get('mountpoint'):
                print(f"        Monté sur: {partition['mountpoint']}")