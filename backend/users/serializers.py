from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import MoxNASUser, MoxNASGroup, AccessControlList

class MoxNASUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = MoxNASUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'home_directory', 'shell', 'samba_enabled', 'nfs_enabled', 
            'ftp_enabled', 'ssh_enabled', 'quota_bytes', 'is_active',
            'date_joined', 'last_login', 'password'
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = MoxNASUser.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class MoxNASGroupSerializer(serializers.ModelSerializer):
    users = MoxNASUserSerializer(many=True, read_only=True)
    user_count = serializers.SerializerMethodField()
    
    class Meta:
        model = MoxNASGroup
        fields = ['id', 'name', 'description', 'gid', 'users', 'user_count', 'created_at', 'updated_at']
    
    def get_user_count(self, obj):
        return obj.users.count()

class AccessControlListSerializer(serializers.ModelSerializer):
    target_user_username = serializers.CharField(source='target_user.username', read_only=True)
    target_group_name = serializers.CharField(source='target_group.name', read_only=True)
    
    class Meta:
        model = AccessControlList
        fields = [
            'id', 'path', 'acl_type', 'target_user', 'target_group',
            'target_user_username', 'target_group_name', 'permissions',
            'recursive', 'created_at'
        ]