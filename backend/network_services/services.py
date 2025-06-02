"""Enhanced network services for MoxNAS backend."""

import subprocess
import json
import logging
import socket
import psutil
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import ipaddress


logger = logging.getLogger(__name__)


class NetworkService:
    """Base class for network service management"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(f"{__name__}.{service_name}")
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get service status and information"""
        try:
            # Check if service is active
            result = subprocess.run([
                'systemctl', 'is-active', self.service_name
            ], capture_output=True, text=True, check=False)
            
            active = result.stdout.strip() == 'active'
            
            # Get detailed status
            status_result = subprocess.run([
                'systemctl', 'status', self.service_name, '--no-pager', '-l'
            ], capture_output=True, text=True, check=False)
            
            # Check if service is enabled
            enabled_result = subprocess.run([
                'systemctl', 'is-enabled', self.service_name
            ], capture_output=True, text=True, check=False)
            
            enabled = enabled_result.stdout.strip() == 'enabled'
            
            return {
                'service': self.service_name,
                'active': active,
                'enabled': enabled,
                'status': result.stdout.strip(),
                'details': status_result.stdout,
                'timestamp': time.time()
            }
        except Exception as e:
            self.logger.error(f"Error getting service status: {e}")
            return {
                'service': self.service_name,
                'active': False,
                'enabled': False,
                'error': str(e)
            }
    
    def manage_service(self, action: str) -> Dict[str, Any]:
        """Manage service (start, stop, restart, enable, disable)"""
        valid_actions = ['start', 'stop', 'restart', 'enable', 'disable', 'reload']
        if action not in valid_actions:
            return {
                'success': False, 
                'message': f'Invalid action. Use: {", ".join(valid_actions)}'
            }
        
        try:
            result = subprocess.run([
                'systemctl', action, self.service_name
            ], capture_output=True, text=True, check=True)
            
            return {
                'success': True,
                'message': f'Service {self.service_name} {action}ed successfully',
                'output': result.stdout
            }
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'message': f'Failed to {action} {self.service_name}: {e.stderr}'
            }
    
    def check_port_status(self, port: int) -> Dict[str, Any]:
        """Check if a port is open and listening"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            listening = result == 0
            
            # Get process using the port
            process_info = None
            if listening:
                for conn in psutil.net_connections():
                    if conn.laddr.port == port and conn.status == 'LISTEN':
                        try:
                            process = psutil.Process(conn.pid)
                            process_info = {
                                'pid': conn.pid,
                                'name': process.name(),
                                'cmdline': process.cmdline()
                            }
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                        break
            
            return {
                'port': port,
                'listening': listening,
                'process': process_info,
                'timestamp': time.time()
            }
        except Exception as e:
            return {
                'port': port,
                'listening': False,
                'error': str(e)
            }


class SMBService(NetworkService):
    """SMB/CIFS service management"""
    
    def __init__(self):
        super().__init__('smbd')
        self.config_file = Path('/etc/samba/smb.conf')
        self.default_port = 445
    
    def get_shares(self) -> List[Dict[str, Any]]:
        """Get configured SMB shares"""
        try:
            result = subprocess.run([
                'smbclient', '-L', 'localhost', '-N'
            ], capture_output=True, text=True, check=False)
            
            shares = []
            in_shares_section = False
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if 'Sharename' in line:
                    in_shares_section = True
                    continue
                elif line.startswith('-----'):
                    continue
                elif in_shares_section and line:
                    if '\t' in line or '   ' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            share_name = parts[0]
                            share_type = parts[1] if len(parts) > 1 else 'Disk'
                            comment = ' '.join(parts[2:]) if len(parts) > 2 else ''
                            
                            shares.append({
                                'name': share_name,
                                'type': share_type,
                                'comment': comment
                            })
                    else:
                        break
            
            return shares
        except Exception as e:
            self.logger.error(f"Error getting SMB shares: {e}")
            return []
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get active SMB sessions"""
        try:
            result = subprocess.run([
                'smbstatus', '-S'
            ], capture_output=True, text=True, check=False)
            
            sessions = []
            in_sessions_section = False
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if 'Service' in line and 'pid' in line:
                    in_sessions_section = True
                    continue
                elif line.startswith('-----'):
                    continue
                elif in_sessions_section and line:
                    parts = line.split()
                    if len(parts) >= 5:
                        sessions.append({
                            'service': parts[0],
                            'pid': parts[1],
                            'machine': parts[2],
                            'connected_at': ' '.join(parts[3:])
                        })
            
            return sessions
        except Exception as e:
            self.logger.error(f"Error getting SMB sessions: {e}")
            return []
    
    def test_share_connectivity(self, share_name: str) -> Dict[str, Any]:
        """Test connectivity to a specific share"""
        try:
            result = subprocess.run([
                'smbclient', f'//localhost/{share_name}', '-N', '-c', 'ls'
            ], capture_output=True, text=True, check=False)
            
            accessible = result.returncode == 0
            
            return {
                'share': share_name,
                'accessible': accessible,
                'output': result.stdout if accessible else result.stderr,
                'timestamp': time.time()
            }
        except Exception as e:
            return {
                'share': share_name,
                'accessible': False,
                'error': str(e)
            }
    
    def reload_config(self) -> Dict[str, Any]:
        """Reload SMB configuration"""
        try:
            result = subprocess.run([
                'smbcontrol', 'all', 'reload-config'
            ], capture_output=True, text=True, check=True)
            
            return {
                'success': True,
                'message': 'SMB configuration reloaded successfully',
                'output': result.stdout
            }
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'message': f'Failed to reload SMB config: {e.stderr}'
            }


class NFSService(NetworkService):
    """NFS service management"""
    
    def __init__(self):
        super().__init__('nfs-server')
        self.exports_file = Path('/etc/exports')
        self.default_port = 2049
    
    def get_exports(self) -> List[Dict[str, Any]]:
        """Get configured NFS exports"""
        try:
            result = subprocess.run([
                'exportfs', '-v'
            ], capture_output=True, text=True, check=False)
            
            exports = []
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split()
                    if len(parts) >= 2:
                        path = parts[0]
                        client_info = parts[1]
                        options = '('.join(parts[1:]).split('(')[1:] if '(' in line else []
                        
                        exports.append({
                            'path': path,
                            'client': client_info.split('(')[0],
                            'options': options,
                            'raw': line
                        })
            
            return exports
        except Exception as e:
            self.logger.error(f"Error getting NFS exports: {e}")
            return []
    
    def get_active_mounts(self) -> List[Dict[str, Any]]:
        """Get active NFS mounts/connections"""
        try:
            result = subprocess.run([
                'ss', '-tuln', '|', 'grep', ':2049'
            ], capture_output=True, text=True, shell=True, check=False)
            
            connections = []
            for line in result.stdout.split('\n'):
                if line.strip() and '2049' in line:
                    connections.append({
                        'connection': line.strip(),
                        'timestamp': time.time()
                    })
            
            return connections
        except Exception as e:
            self.logger.error(f"Error getting NFS connections: {e}")
            return []
    
    def export_filesystem(self, path: str, client: str, options: List[str]) -> Dict[str, Any]:
        """Export a filesystem via NFS"""
        try:
            # Validate path exists
            if not Path(path).exists():
                return {
                    'success': False,
                    'message': f'Path {path} does not exist'
                }
            
            # Build export entry
            options_str = ','.join(options) if options else 'rw,sync,no_subtree_check'
            export_entry = f"{path} {client}({options_str})"
            
            # Add to exports file
            with open(self.exports_file, 'a') as f:
                f.write(f"\n{export_entry}\n")
            
            # Reload exports
            subprocess.run(['exportfs', '-ra'], check=True)
            
            return {
                'success': True,
                'message': f'Successfully exported {path}',
                'export': export_entry
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to export {path}: {str(e)}'
            }
    
    def unexport_filesystem(self, path: str) -> Dict[str, Any]:
        """Remove NFS export"""
        try:
            # Remove from exports
            subprocess.run(['exportfs', '-u', path], check=True)
            
            # Remove from exports file
            if self.exports_file.exists():
                lines = self.exports_file.read_text().split('\n')
                new_lines = [line for line in lines if not line.strip().startswith(path)]
                self.exports_file.write_text('\n'.join(new_lines))
            
            return {
                'success': True,
                'message': f'Successfully unexported {path}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to unexport {path}: {str(e)}'
            }


class FTPService(NetworkService):
    """FTP service management"""
    
    def __init__(self):
        super().__init__('vsftpd')
        self.config_file = Path('/etc/vsftpd.conf')
        self.default_port = 21
    
    def get_active_connections(self) -> List[Dict[str, Any]]:
        """Get active FTP connections"""
        try:
            connections = []
            for conn in psutil.net_connections():
                if conn.laddr.port == self.default_port and conn.status == 'ESTABLISHED':
                    try:
                        process = psutil.Process(conn.pid)
                        connections.append({
                            'local_address': f"{conn.laddr.ip}:{conn.laddr.port}",
                            'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}",
                            'pid': conn.pid,
                            'process': process.name(),
                            'status': conn.status
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        connections.append({
                            'local_address': f"{conn.laddr.ip}:{conn.laddr.port}",
                            'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}",
                            'status': conn.status
                        })
            
            return connections
        except Exception as e:
            self.logger.error(f"Error getting FTP connections: {e}")
            return []
    
    def test_ftp_login(self, username: str = 'anonymous', password: str = '') -> Dict[str, Any]:
        """Test FTP login functionality"""
        try:
            import ftplib
            
            ftp = ftplib.FTP()
            ftp.connect('localhost', self.default_port)
            
            if username == 'anonymous':
                ftp.login()
            else:
                ftp.login(username, password)
            
            # Try to list directory
            files = ftp.nlst()
            ftp.quit()
            
            return {
                'success': True,
                'message': f'FTP login successful for {username}',
                'files_count': len(files)
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'FTP login failed: {str(e)}'
            }


class SSHService(NetworkService):
    """SSH service management"""
    
    def __init__(self):
        super().__init__('ssh')
        self.config_file = Path('/etc/ssh/sshd_config')
        self.default_port = 22
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get active SSH sessions"""
        try:
            result = subprocess.run([
                'who'
            ], capture_output=True, text=True, check=False)
            
            sessions = []
            for line in result.stdout.split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 3:
                        sessions.append({
                            'user': parts[0],
                            'terminal': parts[1],
                            'login_time': ' '.join(parts[2:]),
                            'timestamp': time.time()
                        })
            
            return sessions
        except Exception as e:
            self.logger.error(f"Error getting SSH sessions: {e}")
            return []
    
    def get_failed_logins(self, lines: int = 50) -> List[Dict[str, Any]]:
        """Get recent failed SSH login attempts"""
        try:
            result = subprocess.run([
                'journalctl', '-u', 'ssh', '--no-pager', '-n', str(lines),
                '|', 'grep', 'Failed'
            ], capture_output=True, text=True, shell=True, check=False)
            
            failed_logins = []
            for line in result.stdout.split('\n'):
                if 'Failed' in line and 'ssh' in line.lower():
                    failed_logins.append({
                        'log_entry': line.strip(),
                        'timestamp': time.time()
                    })
            
            return failed_logins
        except Exception as e:
            self.logger.error(f"Error getting failed logins: {e}")
            return []


class NetworkInterfaceService:
    """Network interface management service"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.network_interface")
    
    def get_interfaces(self) -> List[Dict[str, Any]]:
        """Get all network interfaces with detailed information"""
        try:
            interfaces = []
            stats = psutil.net_if_stats()
            addrs = psutil.net_if_addrs()
            
            for interface_name, interface_stats in stats.items():
                interface_addrs = addrs.get(interface_name, [])
                
                # Get IP addresses
                ipv4_addrs = [
                    {
                        'address': addr.address,
                        'netmask': addr.netmask,
                        'broadcast': addr.broadcast
                    }
                    for addr in interface_addrs 
                    if addr.family == socket.AF_INET
                ]
                
                ipv6_addrs = [
                    {
                        'address': addr.address,
                        'netmask': addr.netmask
                    }
                    for addr in interface_addrs 
                    if addr.family == socket.AF_INET6
                ]
                
                # Get MAC address
                mac_addr = None
                for addr in interface_addrs:
                    if addr.family == psutil.AF_LINK:
                        mac_addr = addr.address
                        break
                
                interfaces.append({
                    'name': interface_name,
                    'is_up': interface_stats.isup,
                    'duplex': interface_stats.duplex.name if interface_stats.duplex else 'unknown',
                    'speed': interface_stats.speed,
                    'mtu': interface_stats.mtu,
                    'mac_address': mac_addr,
                    'ipv4_addresses': ipv4_addrs,
                    'ipv6_addresses': ipv6_addrs,
                    'timestamp': time.time()
                })
            
            return interfaces
        except Exception as e:
            self.logger.error(f"Error getting network interfaces: {e}")
            return []
    
    def get_interface_stats(self, interface_name: str) -> Dict[str, Any]:
        """Get detailed statistics for a specific interface"""
        try:
            io_counters = psutil.net_io_counters(pernic=True)
            interface_io = io_counters.get(interface_name)
            
            if not interface_io:
                return {'error': f'Interface {interface_name} not found'}
            
            return {
                'interface': interface_name,
                'bytes_sent': interface_io.bytes_sent,
                'bytes_recv': interface_io.bytes_recv,
                'packets_sent': interface_io.packets_sent,
                'packets_recv': interface_io.packets_recv,
                'errin': interface_io.errin,
                'errout': interface_io.errout,
                'dropin': interface_io.dropin,
                'dropout': interface_io.dropout,
                'timestamp': time.time()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def test_connectivity(self, host: str, timeout: int = 5) -> Dict[str, Any]:
        """Test network connectivity to a host"""
        try:
            result = subprocess.run([
                'ping', '-c', '3', '-W', str(timeout), host
            ], capture_output=True, text=True, check=False)
            
            success = result.returncode == 0
            
            # Parse ping statistics
            output_lines = result.stdout.split('\n')
            stats = {}
            
            for line in output_lines:
                if 'packets transmitted' in line:
                    parts = line.split(',')
                    if len(parts) >= 3:
                        transmitted = int(parts[0].split()[0])
                        received = int(parts[1].split()[0])
                        loss_percent = float(parts[2].split()[0].replace('%', ''))
                        
                        stats = {
                            'packets_transmitted': transmitted,
                            'packets_received': received,
                            'packet_loss_percent': loss_percent
                        }
                elif 'min/avg/max' in line:
                    times = line.split('=')[1].strip().split('/')
                    if len(times) >= 3:
                        stats.update({
                            'rtt_min': float(times[0]),
                            'rtt_avg': float(times[1]),
                            'rtt_max': float(times[2])
                        })
            
            return {
                'host': host,
                'reachable': success,
                'output': result.stdout,
                'stats': stats,
                'timestamp': time.time()
            }
        except Exception as e:
            return {
                'host': host,
                'reachable': False,
                'error': str(e)
            }


class FirewallService:
    """Firewall management service"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.firewall")
    
    def get_firewall_status(self) -> Dict[str, Any]:
        """Get firewall status and rules"""
        try:
            # Check if ufw is installed and active
            result = subprocess.run([
                'ufw', 'status', 'verbose'
            ], capture_output=True, text=True, check=False)
            
            if result.returncode != 0:
                # Try iptables if ufw is not available
                iptables_result = subprocess.run([
                    'iptables', '-L', '-n'
                ], capture_output=True, text=True, check=False)
                
                return {
                    'firewall_type': 'iptables',
                    'active': iptables_result.returncode == 0,
                    'rules': iptables_result.stdout.split('\n') if iptables_result.returncode == 0 else [],
                    'raw_output': iptables_result.stdout
                }
            
            # Parse ufw output
            lines = result.stdout.split('\n')
            status = 'inactive'
            rules = []
            
            for line in lines:
                if 'Status:' in line:
                    status = line.split(':')[1].strip().lower()
                elif line.strip() and not line.startswith('Status:') and not line.startswith('Logging:'):
                    if line.strip() and line[0].isdigit():
                        rules.append(line.strip())
            
            return {
                'firewall_type': 'ufw',
                'active': status == 'active',
                'status': status,
                'rules': rules,
                'raw_output': result.stdout
            }
        except Exception as e:
            return {
                'firewall_type': 'unknown',
                'active': False,
                'error': str(e)
            }
    
    def open_port(self, port: int, protocol: str = 'tcp') -> Dict[str, Any]:
        """Open a port in the firewall"""
        try:
            result = subprocess.run([
                'ufw', 'allow', f'{port}/{protocol}'
            ], capture_output=True, text=True, check=True)
            
            return {
                'success': True,
                'message': f'Port {port}/{protocol} opened successfully',
                'output': result.stdout
            }
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'message': f'Failed to open port {port}/{protocol}: {e.stderr}'
            }
        except FileNotFoundError:
            return {
                'success': False,
                'message': 'UFW not installed or not available'
            }
