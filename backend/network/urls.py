from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'interfaces', views.NetworkInterfaceViewSet)
router.register(r'ip-configs', views.IPConfigurationViewSet)
router.register(r'routes', views.NetworkRouteViewSet)
router.register(r'vlans', views.VLANConfigurationViewSet)
router.register(r'firewall', views.FirewallRuleViewSet)
router.register(r'status', views.NetworkStatusViewSet, basename='network-status')

urlpatterns = [
    path('', include(router.urls)),
]