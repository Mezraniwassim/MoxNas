from rest_framework import serializers
from .models import StoragePool, Dataset, Share, AccessControlList


class StoragePoolSerializer(serializers.ModelSerializer):
    available_size = serializers.ReadOnlyField()
    usage_percentage = serializers.ReadOnlyField()

    class Meta:
        model = StoragePool
        fields = '__all__'


class DatasetSerializer(serializers.ModelSerializer):
    full_path = serializers.ReadOnlyField()

    class Meta:
        model = Dataset
        fields = '__all__'


class ShareSerializer(serializers.ModelSerializer):
    class Meta:
        model = Share
        fields = '__all__'


class AccessControlListSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = AccessControlList
        fields = '__all__'
