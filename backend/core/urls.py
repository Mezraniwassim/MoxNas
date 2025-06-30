from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'system', views.SystemInfoViewSet)
router.register(r'services', views.ServiceStatusViewSet)
router.register(r'logs', views.LogEntryViewSet)

urlpatterns = [
    path('', include(router.urls)),
]