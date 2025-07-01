from rest_framework import serializers
from .models import NetworkInterface, IPConfiguration, NetworkRoute, VLANConfiguration, FirewallRule


class NetworkInterfaceSerializer(serializers.ModelSerializer):
    """Serializer for network interfaces"""
    ip_configs = serializers.StringRelatedField(many=True, read_only=True)
    
    class Meta:
        model = NetworkInterface
        fields = ['id', 'name', 'interface_type', 'mac_address', 'enabled', 
                 'auto_start', 'mtu', 'description', 'ip_configs', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
        
    def validate_name(self, value):
        """Validate interface name format"""
        if not value.replace('-', '').replace('_', '').isalnum():
            raise serializers.ValidationError("Interface name must contain only letters, numbers, hyphens, and underscores")
        return value
        
    def validate_mtu(self, value):
        """Validate MTU size"""
        if not 68 <= value <= 9000:
            raise serializers.ValidationError("MTU must be between 68 and 9000")
        return value


class IPConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for IP configurations"""
    interface_name = serializers.CharField(source='interface.name', read_only=True)
    
    class Meta:
        model = IPConfiguration
        fields = ['id', 'interface', 'interface_name', 'method', 'ip_address', 
                 'netmask', 'gateway', 'dns_servers', 'is_primary', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
        
    def validate(self, data):
        """Validate IP configuration"""
        method = data.get('method')
        
        if method == 'static':
            if not data.get('ip_address'):
                raise serializers.ValidationError("IP address is required for static configuration")
            if not data.get('netmask'):
                raise serializers.ValidationError("Netmask is required for static configuration")
                
        return data


class NetworkRouteSerializer(serializers.ModelSerializer):
    """Serializer for network routes"""
    interface_name = serializers.CharField(source='interface.name', read_only=True)
    
    class Meta:
        model = NetworkRoute
        fields = ['id', 'destination', 'gateway', 'interface', 'interface_name', 
                 'metric', 'enabled', 'description', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
        
    def validate_destination(self, value):
        """Validate destination network format"""
        import ipaddress
        try:
            ipaddress.ip_network(value, strict=False)
        except ValueError:
            raise serializers.ValidationError("Invalid network format. Use CIDR notation (e.g., 192.168.1.0/24)")
        return value


class VLANConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for VLAN configurations"""
    parent_interface_name = serializers.CharField(source='parent_interface.name', read_only=True)
    
    class Meta:
        model = VLANConfiguration
        fields = ['id', 'parent_interface', 'parent_interface_name', 'vlan_id', 
                 'name', 'description', 'enabled', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
        
    def validate_vlan_id(self, value):
        """Validate VLAN ID range"""
        if not 1 <= value <= 4094:
            raise serializers.ValidationError("VLAN ID must be between 1 and 4094")
        return value


class FirewallRuleSerializer(serializers.ModelSerializer):
    """Serializer for firewall rules"""
    interface_name = serializers.CharField(source='interface.name', read_only=True)
    
    class Meta:
        model = FirewallRule
        fields = ['id', 'name', 'enabled', 'action', 'protocol', 'source_ip', 
                 'destination_ip', 'source_port', 'destination_port', 'interface', 
                 'interface_name', 'priority', 'description', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
        
    def validate_priority(self, value):
        """Validate priority range"""
        if not 1 <= value <= 1000:
            raise serializers.ValidationError("Priority must be between 1 and 1000")
        return value
        
    def validate_source_port(self, value):
        """Validate port format"""
        if value and not self._validate_port_format(value):
            raise serializers.ValidationError("Invalid port format. Use single port (80) or range (80-443)")
        return value
        
    def validate_destination_port(self, value):
        """Validate port format"""
        if value and not self._validate_port_format(value):
            raise serializers.ValidationError("Invalid port format. Use single port (80) or range (80-443)")
        return value
        
    def _validate_port_format(self, port_string):
        """Helper method to validate port format"""
        import re
        # Single port or port range
        pattern = r'^(\d+(-\d+)?)(,\d+(-\d+)?)*$'
        if not re.match(pattern, port_string):
            return False
            
        # Check port ranges
        for port_part in port_string.split(','):
            if '-' in port_part:
                start, end = port_part.split('-')
                if not (1 <= int(start) <= 65535) or not (1 <= int(end) <= 65535):
                    return False
                if int(start) >= int(end):
                    return False
            else:
                if not (1 <= int(port_part) <= 65535):
                    return False
        return True


class NetworkStatusSerializer(serializers.Serializer):
    """Serializer for network status information"""
    interface_name = serializers.CharField()
    status = serializers.CharField()
    ip_address = serializers.CharField()
    rx_bytes = serializers.IntegerField()
    tx_bytes = serializers.IntegerField()
    rx_packets = serializers.IntegerField()
    tx_packets = serializers.IntegerField()
    errors = serializers.IntegerField()
    dropped = serializers.IntegerField()