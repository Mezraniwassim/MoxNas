from rest_framework import serializers
from .models import ServiceConfig, CloudSyncTask, RsyncTask, TaskLog, UPSConfig

class ServiceConfigSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceConfig
        fields = '__all__'
    
    def get_status(self, obj):
        # This would normally check actual service status
        return 'running' if obj.enabled else 'stopped'

class CloudSyncTaskSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    provider_display = serializers.CharField(source='get_provider_display', read_only=True)
    direction_display = serializers.CharField(source='get_direction_display', read_only=True)
    schedule_display = serializers.CharField(source='get_schedule_display', read_only=True)
    
    class Meta:
        model = CloudSyncTask
        fields = '__all__'
        extra_kwargs = {
            'credentials': {'write_only': True}  # Don't expose credentials in API
        }

class RsyncTaskSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    direction_display = serializers.CharField(source='get_direction_display', read_only=True)
    schedule_display = serializers.CharField(source='get_schedule_display', read_only=True)
    
    class Meta:
        model = RsyncTask
        fields = '__all__'

class TaskLogSerializer(serializers.ModelSerializer):
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = TaskLog
        fields = '__all__'
    
    def get_duration(self, obj):
        if obj.finished_at and obj.started_at:
            return (obj.finished_at - obj.started_at).total_seconds()
        return None

class UPSConfigSerializer(serializers.ModelSerializer):
    ups_type_display = serializers.CharField(source='get_ups_type_display', read_only=True)
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = UPSConfig
        fields = '__all__'
    
    def get_status(self, obj):
        # This would normally check actual UPS status
        return 'online' if obj.enabled else 'offline'