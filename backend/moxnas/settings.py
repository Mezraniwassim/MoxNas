"""
Django settings for MoxNAS project.
"""

from pathlib import Path
import os
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Look for .env file in the project root (one level up from backend)
PROJECT_ROOT = BASE_DIR.parent

# SECURITY WARNING: keep the secret key used in production secret!
# Generate a new secret key if not provided
import secrets
import string

def generate_secret_key():
    """Generate a secure random secret key"""
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
    return ''.join(secrets.choice(alphabet) for _ in range(50))

SECRET_KEY = config('SECRET_KEY', default=generate_secret_key())

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

# Security: Validate ALLOWED_HOSTS configuration
def validate_allowed_hosts():
    """Validate ALLOWED_HOSTS for security"""
    hosts = config('ALLOWED_HOSTS', default='*', cast=Csv())
    
    # For container deployment, allow all hosts by default
    # This is necessary for LXC containers with dynamic IPs
    if not hosts or hosts == ['']:
        hosts = ['*']
    
    return hosts

ALLOWED_HOSTS = validate_allowed_hosts()

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'management',
    'core',
    'storage',
    'services',
    'network',
    'users',
    'proxmox',
    'proxmox_integration',
]

MIDDLEWARE = [
    'core.security_middleware.SecurityHeadersMiddleware',
    'core.security_middleware.RateLimitMiddleware', 
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.security_middleware.SecurityLoggingMiddleware',
]

ROOT_URLCONF = 'moxnas.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR.parent, 'frontend', 'build'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'moxnas.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# WhiteNoise configuration
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Add React build directory to static files
STATICFILES_DIRS = [
    os.path.join(BASE_DIR.parent, 'frontend', 'build', 'static'),
]

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}

# CORS settings - Allow all origins for container deployment
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# For LXC containers, allow all origins since IPs are dynamic
CORS_ALLOW_ALL_ORIGINS = True

# Enhanced security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Session security
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# CSRF protection
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
    SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
    CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=True, cast=bool)
    
    # Additional security headers for production
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_TLS = True

# Custom user model
AUTH_USER_MODEL = 'users.MoxNASUser'

# MoxNAS specific settings
MOXNAS_STORAGE_PATH = config('MOXNAS_STORAGE_PATH', default='/mnt/storage')
MOXNAS_CONFIG_PATH = config('MOXNAS_CONFIG_PATH', default='/etc/moxnas')
MOXNAS_LOG_PATH = config('MOXNAS_LOG_PATH', default='/var/log/moxnas')

# Proxmox settings (optional)
PROXMOX_HOST = config('PROXMOX_HOST', default='')
PROXMOX_PORT = config('PROXMOX_PORT', default=8006, cast=int)
PROXMOX_USERNAME = config('PROXMOX_USERNAME', default='root')
PROXMOX_PASSWORD = config('PROXMOX_PASSWORD', default='')
PROXMOX_REALM = config('PROXMOX_REALM', default='pam')
PROXMOX_SSL_VERIFY = config('PROXMOX_SSL_VERIFY', default=False, cast=bool)

# Proxmox integration configuration (for compatibility with proxmox_integration app)
PROXMOX_CONFIG = {
    'host': PROXMOX_HOST,
    'port': PROXMOX_PORT,
    'username': PROXMOX_USERNAME,
    'password': PROXMOX_PASSWORD,
    'realm': PROXMOX_REALM,
    'ssl_verify': PROXMOX_SSL_VERIFY,
}

# Network settings
NETWORK_TIMEOUT = config('NETWORK_TIMEOUT', default=30, cast=int)
NETWORK_RETRIES = config('NETWORK_RETRIES', default=3, cast=int)

# Storage settings
DEFAULT_STORAGE = config('DEFAULT_STORAGE', default='local')
STORAGE_PATH = config('STORAGE_PATH', default='/var/lib/moxnas')
MAX_STORAGE_SIZE = config('MAX_STORAGE_SIZE', default=1073741824, cast=int)  # 1GB default

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': config('LOG_LEVEL', default='INFO'),
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(MOXNAS_LOG_PATH, 'moxnas.log'),
            'maxBytes': 1024*1024*5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(MOXNAS_LOG_PATH, 'security.log'),
            'maxBytes': 1024*1024*5,  # 5 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'moxnas': {
            'handlers': ['console', 'file'],
            'level': config('LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'services': {
            'handlers': ['console', 'file'],
            'level': config('LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'security': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Ensure log directory exists
os.makedirs(MOXNAS_LOG_PATH, exist_ok=True)