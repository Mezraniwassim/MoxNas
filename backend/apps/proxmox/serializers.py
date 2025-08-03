from rest_framework import serializers
from .models import ProxmoxNode, ProxmoxConnection


class ProxmoxNodeSerializer(serializers.ModelSerializer):
    connection_status = serializers.SerializerMethodField()
    
    class Meta:
        model = ProxmoxNode
        fields = ['id', 'name', 'host', 'port', 'username', 'verify_ssl', 
                 'is_active', 'created_at', 'updated_at', 'connection_status']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def get_connection_status(self, obj):
        try:
            connection = obj.connection
            return {
                'is_connected': connection.is_connected,
                'last_connected': connection.last_connected,
                'connection_error': connection.connection_error,
                'proxmox_version': connection.proxmox_version
            }
        except ProxmoxConnection.DoesNotExist:
            return {
                'is_connected': False,
                'last_connected': None,
                'connection_error': 'Not tested',
                'proxmox_version': ''
            }


class ProxmoxConnectionSerializer(serializers.ModelSerializer):
    node_name = serializers.CharField(source='node.name', read_only=True)
    
    class Meta:
        model = ProxmoxConnection
        fields = ['node_name', 'is_connected', 'last_connected', 
                 'connection_error', 'proxmox_version']


class ContainerCreateSerializer(serializers.Serializer):
    vmid = serializers.IntegerField()
    hostname = serializers.CharField(max_length=100)
    ostemplate = serializers.CharField(required=False)
    storage = serializers.CharField(required=False)
    memory = serializers.IntegerField(required=False)
    cores = serializers.IntegerField(required=False)
    swap = serializers.IntegerField(required=False)
    rootfs = serializers.CharField(required=False)
    net0 = serializers.CharField(required=False)
    onboot = serializers.BooleanField(required=False, default=True)
    start = serializers.BooleanField(required=False, default=True)
    unprivileged = serializers.BooleanField(required=False, default=True)
    password = serializers.CharField(required=False)


class ContainerActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['start', 'stop', 'restart'])
    node = serializers.CharField(required=False)


class CommandExecuteSerializer(serializers.Serializer):
    command = serializers.CharField()
    node = serializers.CharField(required=False)