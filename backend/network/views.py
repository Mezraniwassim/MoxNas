from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
import subprocess
import json
import psutil
import socket
from .models import NetworkInterface, IPConfiguration, NetworkRoute, VLANConfiguration, FirewallRule
from .serializers import (
    NetworkInterfaceSerializer, IPConfigurationSerializer, NetworkRouteSerializer,
    VLANConfigurationSerializer, FirewallRuleSerializer, NetworkStatusSerializer
)


class NetworkInterfaceViewSet(viewsets.ModelViewSet):
    """ViewSet for managing network interfaces"""
    queryset = NetworkInterface.objects.all()
    serializer_class = NetworkInterfaceSerializer
    
    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """Enable network interface"""
        interface = self.get_object()
        try:
            # Enable interface using ip command
            subprocess.run(['ip', 'link', 'set', interface.name, 'up'], check=True)
            interface.enabled = True
            interface.save()
            return Response({'status': 'Interface enabled'})
        except subprocess.CalledProcessError as e:
            return Response({'error': f'Failed to enable interface: {str(e)}'}, 
                          status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """Disable network interface"""
        interface = self.get_object()
        try:
            # Disable interface using ip command
            subprocess.run(['ip', 'link', 'set', interface.name, 'down'], check=True)
            interface.enabled = False
            interface.save()
            return Response({'status': 'Interface disabled'})
        except subprocess.CalledProcessError as e:
            return Response({'error': f'Failed to disable interface: {str(e)}'}, 
                          status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def discover(self, request):
        """Discover available network interfaces on the system"""
        try:
            interfaces = []
            for interface_name, interface_data in psutil.net_if_addrs().items():
                # Skip loopback and virtual interfaces
                if interface_name.startswith(('lo', 'docker', 'br-')):
                    continue
                    
                # Get interface statistics
                stats = psutil.net_if_stats().get(interface_name, {})
                
                interface_info = {
                    'name': interface_name,
                    'is_up': stats.isup if hasattr(stats, 'isup') else False,
                    'speed': stats.speed if hasattr(stats, 'speed') else 0,
                    'mtu': stats.mtu if hasattr(stats, 'mtu') else 1500,
                    'addresses': []
                }
                
                # Get addresses
                for addr in interface_data:
                    if addr.family == socket.AF_INET:
                        interface_info['addresses'].append({
                            'ip': addr.address,
                            'netmask': addr.netmask,
                            'family': 'IPv4'
                        })
                    elif addr.family == socket.AF_INET6:
                        interface_info['addresses'].append({
                            'ip': addr.address,
                            'netmask': addr.netmask,
                            'family': 'IPv6'
                        })
                    elif hasattr(addr, 'address') and len(addr.address) == 17:
                        interface_info['mac_address'] = addr.address
                
                interfaces.append(interface_info)
            
            return Response(interfaces)
        except Exception as e:
            return Response({'error': f'Failed to discover interfaces: {str(e)}'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class IPConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing IP configurations"""
    queryset = IPConfiguration.objects.all()
    serializer_class = IPConfigurationSerializer
    
    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """Apply IP configuration to interface"""
        ip_config = self.get_object()
        try:
            if ip_config.method == 'static':
                # Apply static IP configuration
                commands = [
                    ['ip', 'addr', 'flush', 'dev', ip_config.interface.name],
                    ['ip', 'addr', 'add', f'{ip_config.ip_address}/{self._cidr_from_netmask(ip_config.netmask)}',
                     'dev', ip_config.interface.name]
                ]
                
                if ip_config.gateway:
                    commands.append(['ip', 'route', 'add', 'default', 'via', ip_config.gateway])
                
                for cmd in commands:
                    subprocess.run(cmd, check=True)
                    
            elif ip_config.method == 'dhcp':
                # Start DHCP client
                subprocess.run(['dhclient', ip_config.interface.name], check=True)
            
            return Response({'status': 'IP configuration applied'})
        except subprocess.CalledProcessError as e:
            return Response({'error': f'Failed to apply configuration: {str(e)}'}, 
                          status=status.HTTP_400_BAD_REQUEST)
    
    def _cidr_from_netmask(self, netmask):
        """Convert netmask to CIDR notation"""
        import ipaddress
        return str(ipaddress.IPv4Network(f'0.0.0.0/{netmask}', strict=False).prefixlen)


class NetworkRouteViewSet(viewsets.ModelViewSet):
    """ViewSet for managing network routes"""
    queryset = NetworkRoute.objects.all()
    serializer_class = NetworkRouteSerializer
    
    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """Apply network route"""
        route = self.get_object()
        try:
            cmd = ['ip', 'route', 'add', route.destination, 'via', route.gateway]
            if route.interface:
                cmd.extend(['dev', route.interface.name])
            if route.metric:
                cmd.extend(['metric', str(route.metric)])
            
            subprocess.run(cmd, check=True)
            return Response({'status': 'Route applied'})
        except subprocess.CalledProcessError as e:
            return Response({'error': f'Failed to apply route: {str(e)}'}, 
                          status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def remove(self, request, pk=None):
        """Remove network route"""
        route = self.get_object()
        try:
            cmd = ['ip', 'route', 'del', route.destination, 'via', route.gateway]
            if route.interface:
                cmd.extend(['dev', route.interface.name])
                
            subprocess.run(cmd, check=True)
            return Response({'status': 'Route removed'})
        except subprocess.CalledProcessError as e:
            return Response({'error': f'Failed to remove route: {str(e)}'}, 
                          status=status.HTTP_400_BAD_REQUEST)


class VLANConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing VLAN configurations"""
    queryset = VLANConfiguration.objects.all()
    serializer_class = VLANConfigurationSerializer
    
    @action(detail=True, methods=['post'])
    def create_vlan(self, request, pk=None):
        """Create VLAN interface"""
        vlan_config = self.get_object()
        try:
            vlan_interface = f"{vlan_config.parent_interface.name}.{vlan_config.vlan_id}"
            cmd = ['ip', 'link', 'add', 'link', vlan_config.parent_interface.name, 
                   'name', vlan_interface, 'type', 'vlan', 'id', str(vlan_config.vlan_id)]
            
            subprocess.run(cmd, check=True)
            subprocess.run(['ip', 'link', 'set', vlan_interface, 'up'], check=True)
            
            return Response({'status': f'VLAN interface {vlan_interface} created'})
        except subprocess.CalledProcessError as e:
            return Response({'error': f'Failed to create VLAN: {str(e)}'}, 
                          status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def delete_vlan(self, request, pk=None):
        """Delete VLAN interface"""
        vlan_config = self.get_object()
        try:
            vlan_interface = f"{vlan_config.parent_interface.name}.{vlan_config.vlan_id}"
            subprocess.run(['ip', 'link', 'delete', vlan_interface], check=True)
            
            return Response({'status': f'VLAN interface {vlan_interface} deleted'})
        except subprocess.CalledProcessError as e:
            return Response({'error': f'Failed to delete VLAN: {str(e)}'}, 
                          status=status.HTTP_400_BAD_REQUEST)


class FirewallRuleViewSet(viewsets.ModelViewSet):
    """ViewSet for managing firewall rules"""
    queryset = FirewallRule.objects.all()
    serializer_class = FirewallRuleSerializer
    
    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """Apply firewall rule using iptables"""
        rule = self.get_object()
        try:
            iptables_cmd = self._build_iptables_command(rule)
            subprocess.run(iptables_cmd, check=True)
            
            return Response({'status': 'Firewall rule applied'})
        except subprocess.CalledProcessError as e:
            return Response({'error': f'Failed to apply rule: {str(e)}'}, 
                          status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def remove_rule(self, request, pk=None):
        """Remove firewall rule"""
        rule = self.get_object()
        try:
            iptables_cmd = self._build_iptables_command(rule, action='delete')
            subprocess.run(iptables_cmd, check=True)
            
            return Response({'status': 'Firewall rule removed'})
        except subprocess.CalledProcessError as e:
            return Response({'error': f'Failed to remove rule: {str(e)}'}, 
                          status=status.HTTP_400_BAD_REQUEST)
    
    def _build_iptables_command(self, rule, action='append'):
        """Build iptables command for firewall rule"""
        cmd = ['iptables']
        
        if action == 'append':
            cmd.extend(['-A', 'INPUT'])
        elif action == 'delete':
            cmd.extend(['-D', 'INPUT'])
        
        if rule.protocol != 'all':
            cmd.extend(['-p', rule.protocol])
        
        if rule.source_ip:
            cmd.extend(['-s', rule.source_ip])
        
        if rule.destination_ip:
            cmd.extend(['-d', rule.destination_ip])
        
        if rule.source_port and rule.protocol in ['tcp', 'udp']:
            cmd.extend(['--sport', rule.source_port])
        
        if rule.destination_port and rule.protocol in ['tcp', 'udp']:
            cmd.extend(['--dport', rule.destination_port])
        
        if rule.interface:
            cmd.extend(['-i', rule.interface.name])
        
        cmd.extend(['-j', rule.action.upper()])
        
        return cmd
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get current firewall status"""
        try:
            result = subprocess.run(['iptables', '-L', '-n'], capture_output=True, text=True, check=True)
            return Response({'rules': result.stdout})
        except subprocess.CalledProcessError as e:
            return Response({'error': f'Failed to get firewall status: {str(e)}'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NetworkStatusViewSet(viewsets.ViewSet):
    """ViewSet for network status and monitoring"""
    
    def list(self, request):
        """Get network interface status"""
        try:
            interfaces = []
            net_io = psutil.net_io_counters(pernic=True)
            
            for interface_name, stats in net_io.items():
                # Skip loopback and virtual interfaces
                if interface_name.startswith(('lo', 'docker', 'br-')):
                    continue
                
                interface_stats = psutil.net_if_stats().get(interface_name, {})
                addresses = psutil.net_if_addrs().get(interface_name, [])
                
                # Get primary IP address
                ip_address = 'N/A'
                for addr in addresses:
                    if addr.family == socket.AF_INET and not addr.address.startswith('127.'):
                        ip_address = addr.address
                        break
                
                interface_data = {
                    'interface_name': interface_name,
                    'status': 'up' if interface_stats.isup else 'down',
                    'ip_address': ip_address,
                    'rx_bytes': stats.bytes_recv,
                    'tx_bytes': stats.bytes_sent,
                    'rx_packets': stats.packets_recv,
                    'tx_packets': stats.packets_sent,
                    'errors': stats.errin + stats.errout,
                    'dropped': stats.dropin + stats.dropout
                }
                
                interfaces.append(interface_data)
            
            serializer = NetworkStatusSerializer(interfaces, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            return Response({'error': f'Failed to get network status: {str(e)}'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def connections(self, request):
        """Get active network connections"""
        try:
            connections = []
            for conn in psutil.net_connections():
                if conn.status == psutil.CONN_ESTABLISHED:
                    local_addr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else 'N/A'
                    remote_addr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else 'N/A'
                    
                    connections.append({
                        'protocol': 'TCP' if conn.type == socket.SOCK_STREAM else 'UDP',
                        'local_address': local_addr,
                        'remote_address': remote_addr,
                        'status': conn.status,
                        'pid': conn.pid
                    })
            
            return Response(connections)
            
        except Exception as e:
            return Response({'error': f'Failed to get connections: {str(e)}'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)