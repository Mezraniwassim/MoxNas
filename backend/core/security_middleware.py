"""
Security middleware for MoxNAS
Provides security logging and monitoring
"""

import logging
import time
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseForbidden
from django.core.cache import cache
from django.conf import settings

security_logger = logging.getLogger('security')


class SecurityLoggingMiddleware(MiddlewareMixin):
    """Log security-related events"""
    
    def process_request(self, request):
        # Log potentially suspicious requests
        suspicious_patterns = [
            '../', '..\\', '/etc/', '/proc/', '/sys/',
            'union', 'select', 'drop', 'insert', 'update',
            '<script', 'javascript:', 'data:',
        ]
        
        request_data = str(request.GET) + str(request.POST) + str(request.path)
        
        for pattern in suspicious_patterns:
            if pattern.lower() in request_data.lower():
                security_logger.warning(
                    f"Suspicious request detected: {pattern} in {request.path} "
                    f"from {self.get_client_ip(request)}"
                )
                break
        
        # Store request start time
        request._moxnas_start_time = time.time()
    
    def process_response(self, request, response):
        # Log slow requests (potential DoS attacks)
        if hasattr(request, '_moxnas_start_time'):
            duration = time.time() - request._moxnas_start_time
            if duration > 5.0:  # 5 seconds
                security_logger.warning(
                    f"Slow request detected: {request.path} took {duration:.2f}s "
                    f"from {self.get_client_ip(request)}"
                )
        
        # Log 4xx and 5xx responses
        if response.status_code >= 400:
            security_logger.info(
                f"HTTP {response.status_code} for {request.path} "
                f"from {self.get_client_ip(request)}"
            )
        
        return response
    
    def get_client_ip(self, request):
        """Get the real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class RateLimitMiddleware(MiddlewareMixin):
    """Simple rate limiting middleware"""
    
    def process_request(self, request):
        if not settings.DEBUG:
            client_ip = self.get_client_ip(request)
            cache_key = f"rate_limit_{client_ip}"
            
            # Get current request count
            requests = cache.get(cache_key, 0)
            
            # Check if limit exceeded
            if requests >= 300:  # 300 requests per hour
                security_logger.warning(
                    f"Rate limit exceeded for IP {client_ip}"
                )
                return HttpResponseForbidden("Rate limit exceeded")
            
            # Increment counter
            cache.set(cache_key, requests + 1, 3600)  # 1 hour
        
        return None
    
    def get_client_ip(self, request):
        """Get the real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add additional security headers"""
    
    def process_response(self, request, response):
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response['Content-Security-Policy'] = csp
        
        return response