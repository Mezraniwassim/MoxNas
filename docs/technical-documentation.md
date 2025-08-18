# MoxNAS Technical Documentation

## Architecture Overview

MoxNAS is a comprehensive Network Attached Storage solution designed for Proxmox LXC containers, built with Django REST Framework backend and React frontend.

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MoxNAS Architecture                      │
├─────────────────────────────────────────────────────────────┤
│  Frontend (React + Material-UI)                            │
│  ├── Dashboard                                              │
│  ├── Storage Management                                     │
│  ├── Service Configuration                                  │
│  └── System Monitoring                                      │
├─────────────────────────────────────────────────────────────┤
│  API Gateway (Django REST Framework)                       │
│  ├── Authentication & Authorization                        │
│  ├── Request Routing                                        │
│  └── Response Serialization                                │
├─────────────────────────────────────────────────────────────┤
│  Application Layer                                          │
│  ├── Services App (Samba/NFS/FTP Management)              │
│  ├── Storage App (Pool/Dataset Management)                 │
│  ├── System App (Health/Metrics/Monitoring)               │
│  ├── Network App (Interface/DNS Configuration)            │
│  ├── Users App (Authentication/Authorization)              │
│  └── Shares App (Share Management)                         │
├─────────────────────────────────────────────────────────────┤
│  Service Management Layer                                   │
│  ├── Template Engine (Jinja2)                             │
│  ├── Configuration Generation                              │
│  ├── Service Control (systemctl)                          │
│  └── Process Management                                     │
├─────────────────────────────────────────────────────────────┤
│  System Layer                                              │
│  ├── File System Operations                                │
│  ├── Network Configuration                                 │
│  ├── Process Control                                       │
│  └── Hardware Monitoring                                   │
├─────────────────────────────────────────────────────────────┤
│  Storage Layer                                             │
│  ├── Local Storage                                         │
│  ├── Network Storage                                       │
│  └── Cloud Storage (Future)                               │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### Backend Applications

#### Services App (`backend/apps/services/`)

**Purpose**: Manages NAS services (Samba, NFS, FTP) with template-based configuration generation.

**Key Files**:
- `models.py`: Service configuration data models
- `templates.py`: Jinja2 template engine for service configuration
- `managers.py`: Service-specific management classes
- `views.py`: REST API endpoints for service control
- `serializers.py`: Data serialization for API responses

**Template Engine** (`templates.py:43-89`):
```python
class ServiceTemplateEngine:
    def __init__(self):
        self.template_dir = Path(settings.BASE_DIR) / 'templates' / 'services'
        self.config_dir = Path('/etc/moxnas')
        self.backup_dir = self.config_dir / 'backups'
        
    def render_template(self, template_name, context, output_path=None):
        """Render Jinja2 template with given context"""
        template = self.env.get_template(template_name)
        rendered = template.render(**context)
        
        if output_path:
            self.backup_existing_config(output_path)
            self.write_config_file(output_path, rendered)
            
        return rendered
```

#### Storage App (`backend/apps/storage/`)

**Purpose**: Manages storage pools, datasets, and snapshots.

**Key Components**:
- Pool management with RAID support
- Dataset creation and configuration
- Snapshot management and scheduling
- Storage monitoring and alerts

#### System App (`backend/apps/system/`)

**Purpose**: System monitoring, health checks, and metrics collection.

**Health Check System** (`health.py:15-87`):
```python
class HealthChecker:
    def check_database(self):
        """Check database connectivity and performance"""
        
    def check_services(self):
        """Check status of managed services"""
        
    def check_storage(self):
        """Check storage pool health and capacity"""
        
    def check_system_resources(self):
        """Check CPU, memory, and disk usage"""
```

**Metrics Collection** (`metrics.py:20-156`):
```python
class MetricsCollector:
    def collect_system_metrics(self):
        """Collect CPU, memory, disk, network metrics"""
        
    def collect_service_metrics(self):
        """Collect service-specific performance metrics"""
        
    def export_prometheus_format(self):
        """Export metrics in Prometheus format"""
```

### Service Management

#### Template System

**Location**: `backend/templates/services/`

**Templates Available**:
- `samba/smb.conf.j2`: Samba configuration
- `nfs/exports.j2`: NFS exports configuration  
- `ftp/vsftpd.conf.j2`: FTP server configuration
- `nginx/moxnas.conf.j2`: Nginx reverse proxy
- `systemd/moxnas.service.j2`: Systemd service file

**Example Samba Template** (`samba/smb.conf.j2:1-45`):
```jinja2
[global]
    workgroup = {{ global_settings.workgroup|default('WORKGROUP') }}
    server string = {{ global_settings.server_string|default('MoxNAS Server') }}
    netbios name = {{ global_settings.netbios_name|default('MOXNAS') }}
    
    # Security settings
    security = user
    map to guest = bad user
    guest account = {{ global_settings.guest_account|default('nobody') }}
    
{% for share in shares %}
[{{ share.name }}]
    path = {{ share.path }}
    comment = {{ share.description|default('') }}
    {% if share.read_only %}read only = yes{% else %}read only = no{% endif %}
    {% if share.guest_ok %}guest ok = yes{% else %}guest ok = no{% endif %}
    {% if share.valid_users %}valid users = {{ share.valid_users }}{% endif %}
{% endfor %}
```

#### Service Managers

**Samba Manager** (`managers.py:15-89`):
```python
class SambaManager(ServiceManager):
    def generate_config(self, shares_queryset, global_settings=None):
        """Generate Samba configuration from Django models"""
        context = {
            'shares': shares_queryset,
            'global_settings': global_settings or {}
        }
        return self.template_engine.render_template(
            'samba/smb.conf.j2', 
            context, 
            '/etc/samba/smb.conf'
        )
    
    def reload_service(self):
        """Reload Samba service configuration"""
        return self.run_command(['systemctl', 'reload', 'smbd'])
```

## Database Schema

### Core Models

#### Service Model (`services/models.py:15-45`)
```python
class Service(models.Model):
    name = models.CharField(max_length=50, unique=True)
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES)
    enabled = models.BooleanField(default=False)
    auto_start = models.BooleanField(default=True)
    configuration = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

#### Storage Pool Model (`storage/models.py:20-58`)
```python
class StoragePool(models.Model):
    name = models.CharField(max_length=100, unique=True)
    pool_type = models.CharField(max_length=20, choices=POOL_TYPES)
    size = models.BigIntegerField()
    used = models.BigIntegerField(default=0)
    available = models.BigIntegerField(default=0)
    health_status = models.CharField(max_length=20, default='healthy')
    devices = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
```

#### Share Model (`shares/models.py:15-48`)
```python
class Share(models.Model):
    name = models.CharField(max_length=100)
    path = models.CharField(max_length=255)
    share_type = models.CharField(max_length=10, choices=SHARE_TYPES)
    read_only = models.BooleanField(default=False)
    guest_ok = models.BooleanField(default=False)
    valid_users = models.CharField(max_length=255, blank=True)
    storage_pool = models.ForeignKey(StoragePool, on_delete=models.CASCADE)
    enabled = models.BooleanField(default=True)
```

## API Reference

### Authentication

All API endpoints require authentication via JWT tokens or session authentication.

**Authentication Headers**:
```http
Authorization: Bearer <jwt-token>
# OR
Cookie: sessionid=<session-id>
```

### Core Endpoints

#### System Health
```http
GET /api/system/health/
GET /api/system/health/ready/
GET /api/system/health/live/
GET /api/system/health/detailed/
```

**Response Format**:
```json
{
    "status": "healthy",
    "timestamp": "2024-01-15T10:30:00Z",
    "checks": {
        "database": {"status": "healthy", "response_time": 0.05},
        "services": {"status": "healthy", "running": 3, "stopped": 0},
        "storage": {"status": "healthy", "pools": 2, "usage": 45.2},
        "system": {"status": "healthy", "cpu": 25.5, "memory": 60.2}
    }
}
```

#### Service Management
```http
GET /api/services/                    # List all services
POST /api/services/                   # Create service
GET /api/services/{id}/               # Get service details
PUT /api/services/{id}/               # Update service
DELETE /api/services/{id}/            # Delete service
POST /api/services/{id}/start/        # Start service
POST /api/services/{id}/stop/         # Stop service
POST /api/services/{id}/restart/      # Restart service
POST /api/services/{id}/reload/       # Reload service config
```

#### Storage Management
```http
GET /api/storage/pools/               # List storage pools
POST /api/storage/pools/              # Create pool
GET /api/storage/pools/{id}/          # Get pool details
DELETE /api/storage/pools/{id}/       # Delete pool
GET /api/storage/datasets/            # List datasets
POST /api/storage/datasets/           # Create dataset
GET /api/storage/snapshots/           # List snapshots
POST /api/storage/snapshots/          # Create snapshot
```

#### Share Management
```http
GET /api/shares/smb/                  # List SMB shares
POST /api/shares/smb/                 # Create SMB share
GET /api/shares/nfs/                  # List NFS exports
POST /api/shares/nfs/                 # Create NFS export
GET /api/shares/ftp/                  # List FTP shares
POST /api/shares/ftp/                 # Create FTP share
```

#### Metrics
```http
GET /api/system/metrics/              # Get system metrics (JSON)
GET /api/system/metrics/prometheus/   # Get metrics (Prometheus format)
```

### Request/Response Examples

#### Create SMB Share
```http
POST /api/shares/smb/
Content-Type: application/json

{
    "name": "documents",
    "path": "/mnt/pool1/documents",
    "description": "Document storage",
    "read_only": false,
    "guest_ok": false,
    "valid_users": "user1,user2",
    "storage_pool": 1
}
```

**Response**:
```json
{
    "id": 1,
    "name": "documents",
    "path": "/mnt/pool1/documents",
    "description": "Document storage",
    "read_only": false,
    "guest_ok": false,
    "valid_users": "user1,user2",
    "storage_pool": 1,
    "enabled": true,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
}
```

## Configuration Management

### Environment Variables

**Core Settings**:
```bash
# Database
DATABASE_URL=sqlite:///db.sqlite3
# DATABASE_URL=postgresql://user:pass@localhost/moxnas

# Security
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Cache
REDIS_URL=redis://localhost:6379/0

# Monitoring
PROMETHEUS_ENABLED=True
METRICS_RETENTION_DAYS=30

# Services
SAMBA_CONFIG_PATH=/etc/samba/smb.conf
NFS_EXPORTS_PATH=/etc/exports
FTP_CONFIG_PATH=/etc/vsftpd/vsftpd.conf
```

### Production Configuration

**Location**: `config/production/settings.py`

**Key Settings**:
```python
# Security
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'moxnas'),
        'USER': os.environ.get('DB_USER', 'moxnas'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# Caching
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
    }
}
```

## Deployment Architecture

### Container Deployment

**Dockerfile** (`Dockerfile.optimized`):
```dockerfile
FROM python:3.9-slim AS production

# Create non-root user
RUN useradd --create-home --shell /bin/bash moxnas

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .
RUN chown -R moxnas:moxnas /app

USER moxnas

# Health check
HEALTHCHECK --interval=30s --timeout=10s \
    CMD curl -f http://localhost:8000/api/system/health/ || exit 1

EXPOSE 8000
CMD ["gunicorn", "moxnas.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### Docker Compose Stack

**Production Stack** (`docker-compose.production.yml`):
```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.optimized
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://moxnas:${DB_PASSWORD}@db:5432/moxnas
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./data:/app/data
      - /etc/moxnas:/etc/moxnas
    ports:
      - "8000:8000"

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=moxnas
      - POSTGRES_USER=moxnas
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./config/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
```

## Monitoring and Observability

### Health Checks

**Health Check Levels**:
1. **Basic** (`/api/system/health/`): Simple alive check
2. **Ready** (`/api/system/health/ready/`): Service readiness
3. **Live** (`/api/system/health/live/`): Liveness probe
4. **Detailed** (`/api/system/health/detailed/`): Comprehensive diagnostics

### Metrics Collection

**System Metrics**:
- CPU usage (per core and average)
- Memory usage (RAM and swap)
- Disk I/O (read/write operations)
- Network I/O (bytes in/out)
- Temperature sensors

**Application Metrics**:
- Request count and response times
- Error rates and status codes
- Service status and uptime
- Database query performance

**Prometheus Metrics Format**:
```
# HELP moxnas_cpu_usage_percent CPU usage percentage
# TYPE moxnas_cpu_usage_percent gauge
moxnas_cpu_usage_percent{core="0"} 25.5
moxnas_cpu_usage_percent{core="1"} 30.2

# HELP moxnas_service_status Service status (1=running, 0=stopped)
# TYPE moxnas_service_status gauge
moxnas_service_status{service="samba"} 1
moxnas_service_status{service="nfs"} 1
```

### Logging

**Log Levels**:
- DEBUG: Detailed debugging information
- INFO: General information messages
- WARNING: Warning messages for attention
- ERROR: Error conditions
- CRITICAL: Critical errors requiring immediate attention

**Log Format** (JSON):
```json
{
    "timestamp": "2024-01-15T10:30:00.123Z",
    "level": "INFO",
    "logger": "moxnas.services",
    "message": "Samba service restarted successfully",
    "correlation_id": "req-123456",
    "user_id": "admin",
    "service": "samba",
    "action": "restart"
}
```

## Security Considerations

### Authentication & Authorization

- JWT token-based authentication
- Session-based authentication for web interface
- Role-based access control (RBAC)
- API key authentication for service integrations

### Security Headers

```python
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
X_FRAME_OPTIONS = 'DENY'
```

### Input Validation

- All user inputs validated using Django serializers
- Path traversal protection
- SQL injection prevention via ORM
- CSRF protection enabled

### Service Security

- Services run as non-root users
- Minimal container images
- Regular security updates
- Firewall configuration

## Performance Optimization

### Database Optimization

- Connection pooling
- Query optimization
- Database indexing
- Read/write splitting (future)

### Caching Strategy

- Redis for session storage
- API response caching
- Static file caching
- Template fragment caching

### Application Performance

- Gunicorn with multiple workers
- Nginx reverse proxy
- Static file compression
- Database query optimization

## Testing Strategy

### Test Types

1. **Unit Tests**: Individual component testing
2. **Integration Tests**: Service interaction testing
3. **API Tests**: REST endpoint testing
4. **Performance Tests**: Load and stress testing
5. **Security Tests**: Security vulnerability testing

### Test Coverage

Current test coverage targets:
- Core functionality: 90%+
- API endpoints: 95%+
- Service management: 85%+
- Error handling: 80%+

### Test Execution

```bash
# Run all tests
./scripts/run_tests.sh

# Run specific test categories
./scripts/run_tests.sh unit
./scripts/run_tests.sh integration
./scripts/run_tests.sh api
./scripts/run_tests.sh security
```

## Development Workflow

### Code Structure

```
backend/
├── apps/
│   ├── services/     # Service management
│   ├── storage/      # Storage management
│   ├── system/       # System monitoring
│   ├── network/      # Network configuration
│   ├── users/        # User management
│   └── shares/       # Share management
├── templates/        # Jinja2 templates
├── tests/           # Test suites
└── moxnas/          # Django project settings
```

### Development Commands

```bash
# Start development server
python manage.py runserver

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Validate database
python manage.py validate_database

# Configure services
python manage.py configure_services
```

## Troubleshooting

### Common Issues

#### Service Configuration Errors
- Check template syntax in `/backend/templates/services/`
- Verify service permissions and paths
- Review service logs: `journalctl -u <service-name>`

#### Database Connection Issues
- Verify database credentials in environment variables
- Check database server status
- Review connection pool settings

#### Performance Issues
- Monitor system metrics via `/api/system/metrics/`
- Check database query performance
- Review application logs for slow requests

### Log Locations

- Application logs: `/var/log/moxnas/`
- Service logs: `journalctl -u moxnas`
- Nginx logs: `/var/log/nginx/`
- Database logs: Service-specific locations

### Support Resources

1. **Health Check Dashboard**: `/api/system/health/detailed/`
2. **Metrics Dashboard**: Grafana at port 3000
3. **API Documentation**: `/api/docs/`
4. **System Logs**: `journalctl -u moxnas -f`

For additional support, consult the [User Guide](user-guide.md) and [Troubleshooting Guide](troubleshooting.md).