from rest_framework import serializers
from .models import Dataset, Share, ShareACL, UserAccount, UserGroup


class DatasetSerializer(serializers.ModelSerializer):
    container_name = serializers.CharField(source='container.name', read_only=True)
    usage_percentage = serializers.ReadOnlyField()
    compression_display = serializers.CharField(source='get_compression_display', read_only=True)
    
    class Meta:
        model = Dataset
        fields = [
            'id', 'name', 'path', 'mount_point', 'size_limit', 'used_space',
            'compression', 'compression_display', 'deduplication', 'readonly',
            'container_name', 'usage_percentage', 'created_at', 'updated_at'
        ]


class ShareACLSerializer(serializers.ModelSerializer):
    acl_type_display = serializers.CharField(source='get_acl_type_display', read_only=True)
    permission_display = serializers.CharField(source='get_permission_display', read_only=True)
    
    class Meta:
        model = ShareACL
        fields = [
            'id', 'acl_type', 'acl_type_display', 'identifier', 'permission',
            'permission_display', 'allow_read', 'allow_write', 'allow_execute',
            'allow_delete', 'allow_modify_acl', 'created_at', 'updated_at'
        ]


class ShareSerializer(serializers.ModelSerializer):
    dataset_name = serializers.CharField(source='dataset.name', read_only=True)
    container_name = serializers.CharField(source='dataset.container.name', read_only=True)
    share_type_display = serializers.CharField(source='get_share_type_display', read_only=True)
    acls = ShareACLSerializer(many=True, read_only=True)
    
    class Meta:
        model = Share
        fields = [
            'id', 'name', 'share_type', 'share_type_display', 'path', 'description',
            'is_enabled', 'readonly', 'browseable', 'guest_access', 'config',
            'dataset_name', 'container_name', 'acls', 'created_at', 'updated_at'
        ]


class UserAccountSerializer(serializers.ModelSerializer):
    container_name = serializers.CharField(source='container.name', read_only=True)
    
    class Meta:
        model = UserAccount
        fields = [
            'id', 'username', 'full_name', 'email', 'is_active', 'home_directory',
            'shell', 'allow_ssh', 'allow_ftp', 'allow_smb', 'allow_webdav',
            'container_name', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }


class UserGroupSerializer(serializers.ModelSerializer):
    container_name = serializers.CharField(source='container.name', read_only=True)
    user_count = serializers.SerializerMethodField()
    
    class Meta:
        model = UserGroup
        fields = [
            'id', 'name', 'description', 'container_name', 'user_count', 'created_at'
        ]
    
    def get_user_count(self, obj):
        return obj.users.count()


class DatasetCreateSerializer(serializers.Serializer):
    container_id = serializers.IntegerField()
    name = serializers.CharField(max_length=100)
    size_limit = serializers.IntegerField(required=False, allow_null=True)
    compression = serializers.ChoiceField(
        choices=['off', 'lz4', 'gzip', 'zstd'],
        default='lz4',
        required=False
    )
    deduplication = serializers.BooleanField(default=False, required=False)
    readonly = serializers.BooleanField(default=False, required=False)
    
    def validate_name(self, value):
        # Basic validation for dataset name
        if not value.replace('_', '').replace('-', '').isalnum():
            raise serializers.ValidationError(
                "Dataset name can only contain letters, numbers, underscores, and hyphens"
            )
        return value


class ShareCreateSerializer(serializers.Serializer):
    dataset_id = serializers.IntegerField()
    name = serializers.CharField(max_length=100)
    share_type = serializers.ChoiceField(choices=['nfs', 'smb', 'ftp', 'webdav'])
    description = serializers.CharField(required=False, allow_blank=True)
    readonly = serializers.BooleanField(default=False, required=False)
    browseable = serializers.BooleanField(default=True, required=False)
    guest_access = serializers.BooleanField(default=False, required=False)
    config = serializers.JSONField(default=dict, required=False)
    
    def validate_name(self, value):
        # Basic validation for share name
        if not value.replace('_', '').replace('-', '').isalnum():
            raise serializers.ValidationError(
                "Share name can only contain letters, numbers, underscores, and hyphens"
            )
        return value


class UserCreateSerializer(serializers.Serializer):
    container_id = serializers.IntegerField()
    username = serializers.CharField(max_length=50)
    password = serializers.CharField(write_only=True)
    full_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    shell = serializers.CharField(max_length=50, default='/bin/bash', required=False)
    allow_ssh = serializers.BooleanField(default=False, required=False)
    allow_ftp = serializers.BooleanField(default=True, required=False)
    allow_smb = serializers.BooleanField(default=True, required=False)
    allow_webdav = serializers.BooleanField(default=False, required=False)
    
    def validate_username(self, value):
        # Basic validation for username
        if not value.replace('_', '').replace('-', '').isalnum():
            raise serializers.ValidationError(
                "Username can only contain letters, numbers, underscores, and hyphens"
            )
        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long")
        return value