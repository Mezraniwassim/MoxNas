from rest_framework import serializers
from .models import SMBShare, NFSShare, FTPShare, SharePermission

class SMBShareSerializer(serializers.ModelSerializer):
    mount_point_path = serializers.CharField(source='mount_point.path', read_only=True)
    
    class Meta:
        model = SMBShare
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def validate_path(self, value):
        """Validate that path exists"""
        import os
        if not os.path.exists(value):
            raise serializers.ValidationError("Path does not exist")
        if not os.path.isdir(value):
            raise serializers.ValidationError("Path is not a directory")
        return value

class NFSShareSerializer(serializers.ModelSerializer):
    mount_point_path = serializers.CharField(source='mount_point.path', read_only=True)
    export_line = serializers.CharField(source='get_export_line', read_only=True)
    
    class Meta:
        model = NFSShare
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def validate_path(self, value):
        """Validate that path exists"""
        import os
        if not os.path.exists(value):
            raise serializers.ValidationError("Path does not exist")
        if not os.path.isdir(value):
            raise serializers.ValidationError("Path is not a directory")
        return value

class FTPShareSerializer(serializers.ModelSerializer):
    mount_point_path = serializers.CharField(source='mount_point.path', read_only=True)
    
    class Meta:
        model = FTPShare
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class SharePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SharePermission
        fields = '__all__'
        read_only_fields = ('created_at',)