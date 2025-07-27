from rest_framework import serializers
from .models import Dataset, Share, MountPoint
import os
import psutil

class DatasetSerializer(serializers.ModelSerializer):
    size_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Dataset
        fields = '__all__'
    
    def get_size_info(self, obj):
        """Get size information for the dataset path"""
        try:
            if os.path.exists(obj.path):
                usage = psutil.disk_usage(obj.path)
                return {
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': (usage.used / usage.total) * 100
                }
        except:
            pass
        return None

class ShareSerializer(serializers.ModelSerializer):
    protocol_display = serializers.CharField(source='get_protocol_display', read_only=True)
    
    class Meta:
        model = Share
        fields = '__all__'

class MountPointSerializer(serializers.ModelSerializer):
    usage_info = serializers.SerializerMethodField()
    
    class Meta:
        model = MountPoint
        fields = '__all__'
    
    def get_usage_info(self, obj):
        """Get disk usage information for the mount point"""
        try:
            if os.path.exists(obj.path) and obj.mounted:
                usage = psutil.disk_usage(obj.path)
                return {
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': (usage.used / usage.total) * 100
                }
        except:
            pass
        return None