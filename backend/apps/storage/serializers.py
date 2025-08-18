from rest_framework import serializers
from .models import Disk, MountPoint, StoragePool

class DiskSerializer(serializers.ModelSerializer):
    usage = serializers.ReadOnlyField()
    size_human = serializers.ReadOnlyField()

    class Meta:
        model = Disk
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class MountPointSerializer(serializers.ModelSerializer):
    disk_name = serializers.CharField(source='disk.name', read_only=True)
    disk_device = serializers.CharField(source='disk.device', read_only=True)
    usage = serializers.ReadOnlyField(source='disk.usage')

    class Meta:
        model = MountPoint
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class StoragePoolSerializer(serializers.ModelSerializer):
    mount_points_detail = MountPointSerializer(source='mount_points', many=True, read_only=True)
    total_size = serializers.ReadOnlyField()
    used_size = serializers.ReadOnlyField()
    available_size = serializers.ReadOnlyField()
    usage_percent = serializers.ReadOnlyField()

    class Meta:
        model = StoragePool
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')