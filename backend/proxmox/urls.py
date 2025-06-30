from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProxmoxNodeViewSet, LXCContainerViewSet

router = DefaultRouter()
router.register(r'nodes', ProxmoxNodeViewSet)
router.register(r'containers', LXCContainerViewSet)

urlpatterns = [
    path('', include(router.urls)),
]