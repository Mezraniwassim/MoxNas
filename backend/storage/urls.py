from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'datasets', views.DatasetViewSet)
router.register(r'shares', views.ShareViewSet)
router.register(r'mounts', views.MountPointViewSet)

urlpatterns = [
    path('', include(router.urls)),
]