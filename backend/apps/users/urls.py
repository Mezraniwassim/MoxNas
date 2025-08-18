from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)

urlpatterns = [
    # API Authentication endpoints
    path('auth/login/', views.login_view, name='api_login'),
    path('auth/logout/', views.logout_view, name='api_logout'),
    path('auth/user/', views.user_info_view, name='api_user_info'),
    path('auth/csrf/', views.csrf_token_view, name='api_csrf_token'),
    
    # User management endpoints
    path('', include(router.urls)),
]