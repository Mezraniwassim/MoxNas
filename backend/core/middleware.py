from django.utils.deprecation import MiddlewareMixin
from .models import ServiceStatus

class EnsureServicesMiddleware(MiddlewareMixin):
    """Middleware to ensure services are initialized on first request"""
    
    def process_request(self, request):
        # Only check for API requests to avoid overhead
        if request.path.startswith('/api/core/services'):
            try:
                # Ensure services exist when accessing services API
                ServiceStatus.ensure_services_exist()
            except Exception:
                # Silently fail to avoid breaking the request
                pass
        return None