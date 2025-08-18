# MoxNAS API Reference

## Overview

The MoxNAS API is a RESTful web service built with Django REST Framework that provides programmatic access to all NAS functionality including storage management, service configuration, system monitoring, and user administration.

## Base URL

```
http://your-moxnas-server:8000/api/
```

## Authentication

### JWT Authentication (Recommended)

```http
POST /api/auth/login/
Content-Type: application/json

{
    "username": "your-username",
    "password": "your-password"
}
```

**Response**:
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com"
    }
}
```

**Using the token**:
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

### Session Authentication

Standard Django session authentication for web interface integration.

```http
Cookie: sessionid=abcd1234...
```

## Error Handling

### Error Response Format

```json
{
    "error": "Error type",
    "message": "Human-readable error message",
    "details": {
        "field": ["Specific field error messages"]
    },
    "code": "ERROR_CODE",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

### HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `204 No Content`: Resource deleted successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict
- `422 Unprocessable Entity`: Validation errors
- `500 Internal Server Error`: Server error

## Pagination

List endpoints use cursor-based pagination:

```json
{
    "count": 150,
    "next": "http://api.example.org/accounts/?cursor=cD0yMDIz",
    "previous": "http://api.example.org/accounts/?cursor=bz0yMDIz",
    "results": [...]
}
```

**Parameters**:
- `cursor`: Pagination cursor
- `page_size`: Number of items per page (default: 20, max: 100)

## System Endpoints

### Health Checks

#### Basic Health Check
```http
GET /api/system/health/
```

**Response**:
```json
{
    "status": "healthy",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Readiness Check
```http
GET /api/system/health/ready/
```

**Response**:
```json
{
    "status": "ready",
    "timestamp": "2024-01-15T10:30:00Z",
    "checks": {
        "database": "ready",
        "cache": "ready",
        "services": "ready"
    }
}
```

#### Liveness Check
```http
GET /api/system/health/live/
```

**Response**:
```json
{
    "status": "alive",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Detailed Health Check
```http
GET /api/system/health/detailed/
Authorization: Bearer <token>
```

**Response**:
```json
{
    "status": "healthy",
    "timestamp": "2024-01-15T10:30:00Z",
    "checks": {
        "database": {
            "status": "healthy",
            "response_time": 0.05,
            "connections": 5,
            "max_connections": 20
        },
        "services": {
            "status": "healthy",
            "running": 3,
            "stopped": 0,
            "services": {
                "samba": "running",
                "nfs": "running",
                "ftp": "running"
            }
        },
        "storage": {
            "status": "healthy",
            "pools": 2,
            "total_capacity": "2TB",
            "used_capacity": "900GB",
            "usage_percentage": 45.2
        },
        "system": {
            "status": "healthy",
            "cpu_usage": 25.5,
            "memory_usage": 60.2,
            "disk_usage": 45.2,
            "load_average": [0.5, 0.7, 0.9]
        }
    }
}
```

### System Information

#### Version Information
```http
GET /api/system/version/
```

**Response**:
```json
{
    "version": "1.0.0",
    "build": "20240115-1030",
    "django_version": "4.2.7",
    "python_version": "3.9.18",
    "platform": "linux"
}
```

#### System Metrics
```http
GET /api/system/metrics/
Authorization: Bearer <token>
```

**Response**:
```json
{
    "timestamp": "2024-01-15T10:30:00Z",
    "system": {
        "cpu": {
            "usage_percent": 25.5,
            "cores": 4,
            "load_average": [0.5, 0.7, 0.9]
        },
        "memory": {
            "total": 8589934592,
            "available": 3221225472,
            "usage_percent": 62.5
        },
        "disk": {
            "total": 2199023255552,
            "free": 1199023255552,
            "usage_percent": 45.5
        },
        "network": {
            "bytes_sent": 1048576000,
            "bytes_recv": 2097152000,
            "packets_sent": 100000,
            "packets_recv": 150000
        }
    },
    "services": {
        "samba": {"status": "running", "uptime": 86400},
        "nfs": {"status": "running", "uptime": 86400},
        "ftp": {"status": "stopped", "uptime": 0}
    }
}
```

#### Prometheus Metrics
```http
GET /api/system/metrics/prometheus/
```

**Response** (Prometheus format):
```
# HELP moxnas_cpu_usage_percent CPU usage percentage
# TYPE moxnas_cpu_usage_percent gauge
moxnas_cpu_usage_percent{core="0"} 25.5
moxnas_cpu_usage_percent{core="1"} 30.2

# HELP moxnas_memory_usage_bytes Memory usage in bytes
# TYPE moxnas_memory_usage_bytes gauge
moxnas_memory_usage_bytes{type="total"} 8589934592
moxnas_memory_usage_bytes{type="available"} 3221225472

# HELP moxnas_service_status Service status (1=running, 0=stopped)
# TYPE moxnas_service_status gauge
moxnas_service_status{service="samba"} 1
moxnas_service_status{service="nfs"} 1
moxnas_service_status{service="ftp"} 0
```

## Service Management

### List Services
```http
GET /api/services/
Authorization: Bearer <token>
```

**Response**:
```json
{
    "count": 3,
    "results": [
        {
            "id": 1,
            "name": "samba",
            "service_type": "smb",
            "enabled": true,
            "auto_start": true,
            "status": "running",
            "configuration": {
                "workgroup": "WORKGROUP",
                "server_string": "MoxNAS Server"
            },
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        }
    ]
}
```

### Get Service Details
```http
GET /api/services/{id}/
Authorization: Bearer <token>
```

### Create Service
```http
POST /api/services/
Authorization: Bearer <token>
Content-Type: application/json

{
    "name": "backup-ftp",
    "service_type": "ftp",
    "enabled": true,
    "auto_start": true,
    "configuration": {
        "passive_mode": true,
        "port": 21,
        "max_clients": 10
    }
}
```

### Update Service
```http
PUT /api/services/{id}/
Authorization: Bearer <token>
Content-Type: application/json

{
    "name": "samba",
    "service_type": "smb",
    "enabled": true,
    "auto_start": true,
    "configuration": {
        "workgroup": "MYWORKGROUP",
        "server_string": "My MoxNAS Server"
    }
}
```

### Delete Service
```http
DELETE /api/services/{id}/
Authorization: Bearer <token>
```

### Service Control Actions

#### Start Service
```http
POST /api/services/{id}/start/
Authorization: Bearer <token>
```

**Response**:
```json
{
    "status": "success",
    "message": "Service started successfully",
    "service_status": "running"
}
```

#### Stop Service
```http
POST /api/services/{id}/stop/
Authorization: Bearer <token>
```

#### Restart Service
```http
POST /api/services/{id}/restart/
Authorization: Bearer <token>
```

#### Reload Configuration
```http
POST /api/services/{id}/reload/
Authorization: Bearer <token>
```

#### Get Service Status
```http
GET /api/services/{id}/status/
Authorization: Bearer <token>
```

**Response**:
```json
{
    "service": "samba",
    "status": "running",
    "pid": 1234,
    "uptime": 86400,
    "memory_usage": 50331648,
    "cpu_usage": 2.5
}
```

## Storage Management

### Storage Pools

#### List Storage Pools
```http
GET /api/storage/pools/
Authorization: Bearer <token>
```

**Response**:
```json
{
    "count": 2,
    "results": [
        {
            "id": 1,
            "name": "tank",
            "pool_type": "mirror",
            "size": 2199023255552,
            "used": 1099511627776,
            "available": 1099511627776,
            "health_status": "healthy",
            "devices": ["/dev/sdb", "/dev/sdc"],
            "created_at": "2024-01-15T10:00:00Z"
        }
    ]
}
```

#### Create Storage Pool
```http
POST /api/storage/pools/
Authorization: Bearer <token>
Content-Type: application/json

{
    "name": "backup",
    "pool_type": "single",
    "devices": ["/dev/sdd"]
}
```

#### Get Pool Details
```http
GET /api/storage/pools/{id}/
Authorization: Bearer <token>
```

#### Delete Storage Pool
```http
DELETE /api/storage/pools/{id}/
Authorization: Bearer <token>
```

### Datasets

#### List Datasets
```http
GET /api/storage/datasets/
Authorization: Bearer <token>
```

**Response**:
```json
{
    "count": 3,
    "results": [
        {
            "id": 1,
            "name": "documents",
            "mount_point": "/mnt/tank/documents",
            "quota": 107374182400,
            "used": 53687091200,
            "compression": "lz4",
            "deduplication": false,
            "storage_pool": 1,
            "created_at": "2024-01-15T10:00:00Z"
        }
    ]
}
```

#### Create Dataset
```http
POST /api/storage/datasets/
Authorization: Bearer <token>
Content-Type: application/json

{
    "name": "photos",
    "storage_pool": 1,
    "quota": 214748364800,
    "compression": "gzip",
    "deduplication": true
}
```

### Snapshots

#### List Snapshots
```http
GET /api/storage/snapshots/
Authorization: Bearer <token>
```

**Response**:
```json
{
    "count": 10,
    "results": [
        {
            "id": 1,
            "name": "documents@2024-01-15-10:30",
            "dataset": 1,
            "size": 10737418240,
            "created_at": "2024-01-15T10:30:00Z"
        }
    ]
}
```

#### Create Snapshot
```http
POST /api/storage/snapshots/
Authorization: Bearer <token>
Content-Type: application/json

{
    "dataset": 1,
    "name": "manual-backup-2024-01-15"
}
```

#### Rollback to Snapshot
```http
POST /api/storage/snapshots/{id}/rollback/
Authorization: Bearer <token>
```

#### Clone Snapshot
```http
POST /api/storage/snapshots/{id}/clone/
Authorization: Bearer <token>
Content-Type: application/json

{
    "clone_name": "documents-clone"
}
```

## Share Management

### SMB/CIFS Shares

#### List SMB Shares
```http
GET /api/shares/smb/
Authorization: Bearer <token>
```

**Response**:
```json
{
    "count": 2,
    "results": [
        {
            "id": 1,
            "name": "documents",
            "path": "/mnt/tank/documents",
            "description": "Document storage",
            "read_only": false,
            "guest_ok": false,
            "valid_users": "user1,user2",
            "storage_pool": 1,
            "enabled": true,
            "created_at": "2024-01-15T10:00:00Z"
        }
    ]
}
```

#### Create SMB Share
```http
POST /api/shares/smb/
Authorization: Bearer <token>
Content-Type: application/json

{
    "name": "backup",
    "path": "/mnt/backup/shared",
    "description": "Backup storage",
    "read_only": false,
    "guest_ok": true,
    "valid_users": "",
    "storage_pool": 2
}
```

#### Update SMB Share
```http
PUT /api/shares/smb/{id}/
Authorization: Bearer <token>
Content-Type: application/json

{
    "name": "documents",
    "path": "/mnt/tank/documents",
    "description": "Updated document storage",
    "read_only": false,
    "guest_ok": false,
    "valid_users": "user1,user2,user3",
    "storage_pool": 1
}
```

#### Delete SMB Share
```http
DELETE /api/shares/smb/{id}/
Authorization: Bearer <token>
```

### NFS Exports

#### List NFS Exports
```http
GET /api/shares/nfs/
Authorization: Bearer <token>
```

**Response**:
```json
{
    "count": 1,
    "results": [
        {
            "id": 1,
            "path": "/mnt/tank/nfs-share",
            "networks": "192.168.1.0/24",
            "options": "rw,sync,no_subtree_check",
            "storage_pool": 1,
            "enabled": true,
            "created_at": "2024-01-15T10:00:00Z"
        }
    ]
}
```

#### Create NFS Export
```http
POST /api/shares/nfs/
Authorization: Bearer <token>
Content-Type: application/json

{
    "path": "/mnt/tank/nfs-data",
    "networks": "10.0.0.0/8,192.168.0.0/16",
    "options": "rw,sync,no_subtree_check,no_root_squash",
    "storage_pool": 1
}
```

### FTP Shares

#### List FTP Users
```http
GET /api/shares/ftp/
Authorization: Bearer <token>
```

**Response**:
```json
{
    "count": 2,
    "results": [
        {
            "id": 1,
            "username": "ftpuser1",
            "home_directory": "/mnt/tank/ftp/user1",
            "upload_enabled": true,
            "download_enabled": true,
            "delete_enabled": false,
            "storage_pool": 1,
            "enabled": true,
            "created_at": "2024-01-15T10:00:00Z"
        }
    ]
}
```

#### Create FTP User
```http
POST /api/shares/ftp/
Authorization: Bearer <token>
Content-Type: application/json

{
    "username": "ftpuser2",
    "password": "secure-password",
    "home_directory": "/mnt/tank/ftp/user2",
    "upload_enabled": true,
    "download_enabled": true,
    "delete_enabled": true,
    "storage_pool": 1
}
```

## User Management

### List Users
```http
GET /api/users/
Authorization: Bearer <token>
```

**Response**:
```json
{
    "count": 3,
    "results": [
        {
            "id": 1,
            "username": "admin",
            "email": "admin@example.com",
            "first_name": "Admin",
            "last_name": "User",
            "is_active": true,
            "is_staff": true,
            "is_superuser": true,
            "groups": ["administrators"],
            "last_login": "2024-01-15T10:00:00Z",
            "date_joined": "2024-01-01T00:00:00Z"
        }
    ]
}
```

### Create User
```http
POST /api/users/
Authorization: Bearer <token>
Content-Type: application/json

{
    "username": "newuser",
    "email": "newuser@example.com",
    "first_name": "New",
    "last_name": "User",
    "password": "secure-password",
    "groups": ["users"]
}
```

### Update User
```http
PUT /api/users/{id}/
Authorization: Bearer <token>
Content-Type: application/json

{
    "username": "newuser",
    "email": "updated@example.com",
    "first_name": "Updated",
    "last_name": "User",
    "is_active": true,
    "groups": ["users", "backup-users"]
}
```

### Change Password
```http
POST /api/users/{id}/change-password/
Authorization: Bearer <token>
Content-Type: application/json

{
    "old_password": "current-password",
    "new_password": "new-secure-password"
}
```

## Network Management

### List Network Interfaces
```http
GET /api/network/interfaces/
Authorization: Bearer <token>
```

**Response**:
```json
{
    "count": 2,
    "results": [
        {
            "id": 1,
            "name": "eth0",
            "type": "ethernet",
            "mac_address": "00:11:22:33:44:55",
            "ip_address": "192.168.1.100",
            "netmask": "255.255.255.0",
            "gateway": "192.168.1.1",
            "dns_servers": ["8.8.8.8", "8.8.4.4"],
            "dhcp_enabled": false,
            "enabled": true
        }
    ]
}
```

### Update Network Interface
```http
PUT /api/network/interfaces/{id}/
Authorization: Bearer <token>
Content-Type: application/json

{
    "name": "eth0",
    "ip_address": "192.168.1.101",
    "netmask": "255.255.255.0",
    "gateway": "192.168.1.1",
    "dns_servers": ["1.1.1.1", "1.0.0.1"],
    "dhcp_enabled": false,
    "enabled": true
}
```

## Rate Limiting

API endpoints are rate-limited to prevent abuse:

- **Anonymous users**: 100 requests per hour
- **Authenticated users**: 1000 requests per hour
- **Admin users**: 5000 requests per hour

Rate limit headers:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642248000
```

## Webhooks

### Register Webhook
```http
POST /api/webhooks/
Authorization: Bearer <token>
Content-Type: application/json

{
    "url": "https://your-server.com/webhook",
    "events": ["service.started", "service.stopped", "storage.pool.created"],
    "secret": "webhook-secret",
    "active": true
}
```

### Webhook Events

Available events:
- `service.started`
- `service.stopped`
- `service.failed`
- `storage.pool.created`
- `storage.pool.deleted`
- `storage.snapshot.created`
- `system.alert.critical`
- `user.login`
- `user.created`

### Webhook Payload

```json
{
    "event": "service.started",
    "timestamp": "2024-01-15T10:30:00Z",
    "data": {
        "service": "samba",
        "status": "running",
        "user": "admin"
    },
    "signature": "sha256=..."
}
```

## OpenAPI Specification

Interactive API documentation is available at:
- **Swagger UI**: `/api/docs/`
- **ReDoc**: `/api/redoc/`
- **OpenAPI Schema**: `/api/schema/`

## Code Examples

### Python (using requests)

```python
import requests

# Authentication
response = requests.post('http://moxnas:8000/api/auth/login/', json={
    'username': 'admin',
    'password': 'password'
})
token = response.json()['access']

# Headers for authenticated requests
headers = {'Authorization': f'Bearer {token}'}

# Get system health
health = requests.get('http://moxnas:8000/api/system/health/', headers=headers)
print(health.json())

# Create SMB share
share_data = {
    'name': 'documents',
    'path': '/mnt/tank/documents',
    'read_only': False,
    'guest_ok': False
}
share = requests.post('http://moxnas:8000/api/shares/smb/', 
                     json=share_data, headers=headers)
```

### JavaScript (using fetch)

```javascript
// Authentication
const loginResponse = await fetch('http://moxnas:8000/api/auth/login/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        username: 'admin',
        password: 'password'
    })
});
const { access: token } = await loginResponse.json();

// Headers for authenticated requests
const headers = {'Authorization': `Bearer ${token}`};

// Get system metrics
const metricsResponse = await fetch('http://moxnas:8000/api/system/metrics/', {
    headers
});
const metrics = await metricsResponse.json();
console.log(metrics);
```

### cURL Examples

```bash
# Login and get token
TOKEN=$(curl -s -X POST http://moxnas:8000/api/auth/login/ \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"password"}' | \
    jq -r '.access')

# Get system health
curl -H "Authorization: Bearer $TOKEN" \
    http://moxnas:8000/api/system/health/detailed/

# Create storage pool
curl -X POST -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name":"backup","pool_type":"single","devices":["/dev/sdd"]}' \
    http://moxnas:8000/api/storage/pools/

# Start service
curl -X POST -H "Authorization: Bearer $TOKEN" \
    http://moxnas:8000/api/services/1/start/
```

## Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| AUTH_REQUIRED | Authentication required | 401 |
| INVALID_CREDENTIALS | Invalid username or password | 401 |
| PERMISSION_DENIED | Insufficient permissions | 403 |
| RESOURCE_NOT_FOUND | Resource not found | 404 |
| VALIDATION_ERROR | Request validation failed | 422 |
| SERVICE_ERROR | Service operation failed | 500 |
| STORAGE_ERROR | Storage operation failed | 500 |
| NETWORK_ERROR | Network operation failed | 500 |

## Support

For API support and questions:
- Check the interactive documentation at `/api/docs/`
- Review the [Technical Documentation](technical-documentation.md)
- Submit issues on the project repository
- Contact support for enterprise deployments