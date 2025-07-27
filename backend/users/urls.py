from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MoxNASUserViewSet, MoxNASGroupViewSet, AccessControlListViewSet

router = DefaultRouter()
router.register(r'users', MoxNASUserViewSet)
router.register(r'groups', MoxNASGroupViewSet)
router.register(r'acl', AccessControlListViewSet)

urlpatterns = [
    path('', include(router.urls)),
]