from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/proxmox/', include('apps.proxmox.urls')),
    path('api/containers/', include('apps.containers.urls')),
    path('api/services/', include('apps.services.urls')),
    path('api/storage/', include('apps.storage.urls')),
    
    # Serve React app for all other routes
    re_path(r'^.*$', TemplateView.as_view(template_name='index.html')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)