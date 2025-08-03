from rest_framework import serializers
from .models import MoxNasContainer, ContainerService, ContainerBackup


class ContainerServiceSerializer(serializers.ModelSerializer):
    service_type_display = serializers.CharField(source='get_service_type_display', read_only=True)
    
    class Meta:
        model = ContainerService
        fields = ['id', 'service_type', 'service_type_display', 'status', 'port', 
                 'config', 'is_enabled', 'auto_start', 'created_at', 'updated_at']


class MoxNasContainerSerializer(serializers.ModelSerializer):
    services = ContainerServiceSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    web_url = serializers.CharField(read_only=True)
    
    class Meta:
        model = MoxNasContainer
        fields = ['id', 'vmid', 'name', 'hostname', 'status', 'status_display',
                 'memory', 'cores', 'swap', 'storage', 'ip_address', 'gateway',
                 'bridge', 'is_moxnas_ready', 'moxnas_version', 'web_url',
                 'created_at', 'updated_at', 'services']


class ContainerCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    hostname = serializers.CharField(max_length=100, required=False)
    vmid = serializers.IntegerField(required=False)
    memory = serializers.IntegerField(default=2048)
    cores = serializers.IntegerField(default=2)
    swap = serializers.IntegerField(default=512)
    storage = serializers.CharField(default='local-lvm')
    ostemplate = serializers.CharField(required=False)
    net0 = serializers.CharField(required=False)
    rootfs = serializers.CharField(required=False)
    password = serializers.CharField(required=False, write_only=True)
    
    def validate_vmid(self, value):
        if value and (value < 100 or value > 999999):
            raise serializers.ValidationError("VMID must be between 100 and 999999")
        return value
    
    def validate_memory(self, value):
        if value < 512:
            raise serializers.ValidationError("Memory must be at least 512 MB")
        return value
    
    def validate_cores(self, value):
        if value < 1 or value > 32:
            raise serializers.ValidationError("Cores must be between 1 and 32")
        return value


class ContainerBackupSerializer(serializers.ModelSerializer):
    container_name = serializers.CharField(source='container.name', read_only=True)
    backup_type_display = serializers.CharField(source='get_backup_type_display', read_only=True)
    size_human = serializers.SerializerMethodField()
    
    class Meta:
        model = ContainerBackup
        fields = ['id', 'container_name', 'backup_file', 'backup_type', 
                 'backup_type_display', 'size', 'size_human', 'description',
                 'created_at', 'created_by']
    
    def get_size_human(self, obj):
        if not obj.size:
            return "Unknown"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if obj.size < 1024.0:
                return f"{obj.size:.1f} {unit}"
            obj.size /= 1024.0
        return f"{obj.size:.1f} PB"


class ServiceConfigSerializer(serializers.Serializer):
    """Generic service configuration serializer"""
    service_type = serializers.ChoiceField(choices=[
        'ssh', 'ftp', 'nfs', 'smb', 'webdav'
    ])
    config = serializers.JSONField(default=dict)
    is_enabled = serializers.BooleanField(default=True)
    auto_start = serializers.BooleanField(default=False)


class ContainerActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=[
        'start', 'stop', 'restart', 'reinstall'
    ])
    
    def validate_action(self, value):
        allowed_actions = ['start', 'stop', 'restart', 'reinstall']
        if value not in allowed_actions:
            raise serializers.ValidationError(f"Action must be one of: {', '.join(allowed_actions)}")
        return value