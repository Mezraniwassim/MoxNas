from rest_framework import serializers
from .models import ProxmoxNode, LXCContainer

class ProxmoxNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProxmoxNode
        fields = ['id', 'name', 'host', 'port', 'username', 'realm', 'ssl_verify', 'enabled', 'created_at']
        extra_kwargs = {
            'password': {'write_only': True}
        }

class LXCContainerSerializer(serializers.ModelSerializer):
    node_name = serializers.CharField(source='node.name', read_only=True)
    
    class Meta:
        model = LXCContainer
        fields = [
            'id', 'vmid', 'name', 'node', 'node_name', 'status', 
            'memory', 'disk_size', 'cores', 'template', 'ip_address',
            'created_at', 'updated_at'
        ]