from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'smb', views.SMBShareViewSet)
router.register(r'nfs', views.NFSShareViewSet)
router.register(r'ftp', views.FTPShareViewSet)
router.register(r'permissions', views.SharePermissionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]