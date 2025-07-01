from rest_framework import serializers
from .models import SystemInfo, ServiceStatus, LogEntry
import psutil
import socket

class SystemInfoSerializer(serializers.ModelSerializer):
    cpu_usage = serializers.SerializerMethodField()
    memory_usage = serializers.SerializerMethodField()
    disk_usage = serializers.SerializerMethodField()
    network_interfaces = serializers.SerializerMethodField()
    
    class Meta:
        model = SystemInfo
        fields = '__all__'
    
    def get_cpu_usage(self, obj):
        return psutil.cpu_percent(interval=1)
    
    def get_memory_usage(self, obj):
        memory = psutil.virtual_memory()
        return {
            'total': memory.total,
            'used': memory.used,
            'free': memory.free,
            'percent': memory.percent
        }
    
    def get_disk_usage(self, obj):
        disk = psutil.disk_usage('/')
        return {
            'total': disk.total,
            'used': disk.used,
            'free': disk.free,
            'percent': (disk.used / disk.total) * 100
        }
    
    def get_network_interfaces(self, obj):
        interfaces = []
        for name, addrs in psutil.net_if_addrs().items():
            if name == 'lo':
                continue
            interface = {"name": name, "addresses": []}
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    interface["addresses"].append({
                        "ip": addr.address,
                        "netmask": addr.netmask
                    })
            if interface["addresses"]:
                interfaces.append(interface)
        return interfaces

class ServiceStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceStatus
        fields = '__all__'

class LogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LogEntry
        fields = '__all__'