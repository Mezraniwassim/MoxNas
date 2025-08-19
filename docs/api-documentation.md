# MoxNAS API Documentation

Complete API reference for MoxNAS REST API. The API provides programmatic access to all MoxNAS functionality.

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Base URL and Headers](#base-url-and-headers)
4. [Response Format](#response-format)
5. [Error Handling](#error-handling)
6. [System APIs](#system-apis)
7. [Service APIs](#service-apis)
8. [Share APIs](#share-apis)
9. [Storage APIs](#storage-apis)
10. [Network APIs](#network-apis)
11. [User APIs](#user-apis)
12. [Logs APIs](#logs-apis)
13. [Code Examples](#code-examples)

## Overview

The MoxNAS API is a RESTful HTTP API that allows programmatic control of your NAS system. All API endpoints return JSON responses and follow standard HTTP status codes.

### API Version
- **Current Version**: v1
- **Base Path**: `/api`
- **Protocol**: HTTP/HTTPS

### Supported Operations
- System monitoring and statistics
- Service control and status
- Share management (SMB, NFS, FTP)
- Storage information
- Network configuration
- User management
- Log access

## Authentication

Currently, the MoxNAS API operates without authentication for local access. Future versions will include:
- API key authentication
- Session-based authentication
- OAuth2 integration

## Base URL and Headers

### Base URL
```
http://YOUR_SERVER_IP:8001/api
```

### Required Headers
```http
Content-Type: application/json
Accept: application/json
```

### CORS Support
The API includes CORS headers for cross-origin requests:
```http
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

## Response Format

### Success Response
```json
{
  "success": true,
  "data": {
    // Response data
  },
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error message",
  "code": "ERROR_CODE",
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

## Error Handling

### HTTP Status Codes
- **200**: Success
- **201**: Created
- **400**: Bad Request
- **404**: Not Found
- **500**: Internal Server Error
- **503**: Service Unavailable

### Error Types
- `VALIDATION_ERROR`: Invalid input parameters
- `RESOURCE_NOT_FOUND`: Requested resource doesn't exist
- `SERVICE_UNAVAILABLE`: Required service is not running
- `PERMISSION_DENIED`: Insufficient permissions
- `INTERNAL_ERROR`: Server-side error

## System APIs

### Get System Statistics

Get real-time system performance metrics.

**Endpoint**: `GET /api/system-stats`

**Response**:
```json
{
  "success": true,
  "data": {
    "cpu": {
      "percent": 25.4,
      "cores": 4,
      "frequency": 2400.0
    },
    "memory": {
      "percent": 45.2,
      "used": "1.8GB",
      "total": "4.0GB",
      "available": "2.2GB"
    },
    "disk": {
      "percent": 67.3,
      "used": "13.5GB",
      "total": "20.0GB",
      "free": "6.5GB"
    },
    "network": {
      "bytes_sent": "125.6MB",
      "bytes_recv": "456.2MB",
      "packets_sent": 125643,
      "packets_recv": 234567
    },
    "system": {
      "uptime": "2 days, 14:32:18",
      "processes": 156,
      "boot_time": 1704067200
    },
    "timestamp": "2024-01-01T12:00:00.000Z"
  }
}
```

### Get System Information

Get basic system information.

**Endpoint**: `GET /api/system-info`

**Response**:
```json
{
  "success": true,
  "data": {
    "hostname": "moxnas",
    "version": "1.0.0",
    "os": "Ubuntu 22.04 LTS",
    "architecture": "x86_64",
    "kernel": "5.15.0-56-generic"
  }
}
```

## Service APIs

### Get Service Status

Get status of all NAS services.

**Endpoint**: `GET /api/services`

**Response**:
```json
{
  "success": true,
  "data": {
    "nginx": {
      "active": true,
      "status": "active",
      "enabled": true,
      "pid": 1234
    },
    "smbd": {
      "active": true,
      "status": "active", 
      "enabled": true,
      "pid": 1235
    },
    "nfs-kernel-server": {
      "active": true,
      "status": "active",
      "enabled": true,
      "pid": 1236
    },
    "vsftpd": {
      "active": false,
      "status": "inactive",
      "enabled": false,
      "pid": null
    }
  }
}
```

### Restart Service

Restart a specific service.

**Endpoint**: `POST /api/services/{service}/restart`

**Parameters**:
- `service` (path): Service name (nginx, smbd, nfs-kernel-server, vsftpd)

**Response**:
```json
{
  "success": true,
  "data": {
    "message": "Service smbd restarted successfully",
    "service": "smbd",
    "status": "active"
  }
}
```

## Share APIs

### List Shares

Get list of all configured shares.

**Endpoint**: `GET /api/shares`

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "name": "public",
      "type": "smb",
      "path": "/mnt/shares/public",
      "active": true,
      "guest_access": true,
      "read_only": false
    },
    {
      "name": "backup",
      "type": "nfs",
      "path": "/mnt/shares/backup", 
      "active": true,
      "clients": ["192.168.1.0/24"],
      "options": "rw,sync,no_subtree_check"
    }
  ]
}
```

### Create Share

Create a new share.

**Endpoint**: `POST /api/shares`

**Request Body**:
```json
{
  "name": "myshare",
  "type": "smb",
  "path": "/mnt/shares/myshare",
  "guest": true,
  "read_only": false,
  "browseable": true
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "name": "myshare",
    "type": "smb", 
    "path": "/mnt/shares/myshare",
    "created": "2024-01-01T12:00:00.000Z"
  }
}
```

### Delete Share

Delete an existing share.

**Endpoint**: `DELETE /api/shares/{name}`

**Parameters**:
- `name` (path): Share name to delete

**Response**:
```json
{
  "success": true,
  "data": {
    "message": "Share 'myshare' deleted successfully",
    "name": "myshare"
  }
}
```

### Get Share Details

Get detailed information about a specific share.

**Endpoint**: `GET /api/shares/{name}`

**Response**:
```json
{
  "success": true,
  "data": {
    "name": "myshare",
    "type": "smb",
    "path": "/mnt/shares/myshare",
    "active": true,
    "guest_access": true,
    "read_only": false,
    "browseable": true,
    "created": "2024-01-01T10:00:00.000Z",
    "modified": "2024-01-01T12:00:00.000Z",
    "size": "2.5GB",
    "files": 1234,
    "permissions": "755"
  }
}
```

## Storage APIs

### Get Storage Information

Get information about storage devices and usage.

**Endpoint**: `GET /api/storage`

**Response**:
```json
{
  "success": true,
  "data": {
    "disks": [
      {
        "device": "/dev/sda1",
        "mountpoint": "/",
        "total": "20GB",
        "used": "13.5GB", 
        "free": "6.5GB",
        "percent": 67.3,
        "fstype": "ext4"
      }
    ],
    "partitions": [
      {
        "device": "/dev/sda1",
        "mountpoint": "/",
        "fstype": "ext4",
        "opts": "rw,relatime"
      }
    ]
  }
}
```

### Get Mount Points

Get list of all mount points.

**Endpoint**: `GET /api/storage/mounts`

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "device": "/dev/sda1",
      "mountpoint": "/",
      "fstype": "ext4",
      "opts": "rw,relatime"
    },
    {
      "device": "tmpfs",
      "mountpoint": "/tmp",
      "fstype": "tmpfs", 
      "opts": "rw,nosuid,nodev"
    }
  ]
}
```

## Network APIs

### Get Network Information

Get network interface and statistics information.

**Endpoint**: `GET /api/network`

**Response**:
```json
{
  "success": true,
  "data": {
    "interfaces": [
      {
        "name": "eth0",
        "addresses": [
          {
            "family": "AF_INET",
            "address": "192.168.1.100",
            "netmask": "255.255.255.0",
            "broadcast": "192.168.1.255"
          }
        ]
      }
    ],
    "stats": {
      "eth0": {
        "bytes_sent": 131072000,
        "bytes_recv": 524288000,
        "packets_sent": 125643,
        "packets_recv": 234567,
        "errin": 0,
        "errout": 0,
        "dropin": 0,
        "dropout": 0
      }
    }
  }
}
```

### Get Interface Details

Get detailed information about a specific interface.

**Endpoint**: `GET /api/network/interfaces/{name}`

**Response**:
```json
{
  "success": true,
  "data": {
    "name": "eth0",
    "status": "up",
    "mtu": 1500,
    "mac": "00:1a:2b:3c:4d:5e",
    "addresses": [
      {
        "family": "AF_INET",
        "address": "192.168.1.100",
        "netmask": "255.255.255.0",
        "broadcast": "192.168.1.255"
      }
    ],
    "stats": {
      "bytes_sent": 131072000,
      "bytes_recv": 524288000,
      "packets_sent": 125643,
      "packets_recv": 234567
    }
  }
}
```

## User APIs

### List Users

Get list of all users.

**Endpoint**: `GET /api/users`

**Response**:
```json
{
  "success": true,
  "data": {
    "admin": {
      "role": "administrator",
      "created": "2024-01-01T00:00:00.000Z",
      "last_login": "2024-01-01T12:00:00.000Z"
    },
    "user1": {
      "role": "user",
      "created": "2024-01-01T08:00:00.000Z",
      "last_login": "2024-01-01T11:30:00.000Z"
    }
  }
}
```

### Create User

Create a new user account.

**Endpoint**: `POST /api/users`

**Request Body**:
```json
{
  "username": "newuser",
  "password": "secure_password",
  "role": "user",
  "full_name": "New User",
  "email": "newuser@example.com"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "username": "newuser",
    "role": "user",
    "created": "2024-01-01T12:00:00.000Z"
  }
}
```

### Delete User

Delete a user account.

**Endpoint**: `DELETE /api/users/{username}`

**Response**:
```json
{
  "success": true,
  "data": {
    "message": "User 'username' deleted successfully",
    "username": "username"
  }
}
```

## Logs APIs

### Get Service Logs

Get logs for a specific service.

**Endpoint**: `GET /api/logs/{service}`

**Parameters**:
- `service` (path): Service name
- `lines` (query): Number of lines to return (default: 100)

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "timestamp": "1704067200000000",
      "message": "Service started successfully",
      "priority": "6",
      "unit": "moxnas-api.service"
    },
    {
      "timestamp": "1704067260000000", 
      "message": "API server listening on port 8001",
      "priority": "6",
      "unit": "moxnas-api.service"
    }
  ]
}
```

### Get System Logs

Get general system logs.

**Endpoint**: `GET /api/logs/system`

**Parameters**:
- `lines` (query): Number of lines to return (default: 100)
- `level` (query): Log level filter (error, warning, info, debug)

**Response**: Same format as service logs

## Code Examples

### Python Example

```python
import requests
import json

class MoxNASAPI:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def get_system_stats(self):
        response = self.session.get(f"{self.base_url}/system-stats")
        return response.json()
    
    def create_share(self, name, share_type, path, guest=True):
        data = {
            'name': name,
            'type': share_type,
            'path': path,
            'guest': guest
        }
        response = self.session.post(f"{self.base_url}/shares", 
                                   json=data)
        return response.json()
    
    def get_services(self):
        response = self.session.get(f"{self.base_url}/services")
        return response.json()

# Usage
api = MoxNASAPI("http://192.168.1.100:8001/api")

# Get system statistics
stats = api.get_system_stats()
print(f"CPU Usage: {stats['data']['cpu']['percent']}%")

# Create a new share
result = api.create_share("documents", "smb", "/mnt/shares/documents")
print(f"Share created: {result['success']}")

# Check service status
services = api.get_services()
for service, status in services['data'].items():
    print(f"{service}: {'Running' if status['active'] else 'Stopped'}")
```

### JavaScript Example

```javascript
class MoxNASAPI {
    constructor(baseURL) {
        this.baseURL = baseURL;
    }
    
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                ...options.headers
            },
            ...options
        };
        
        try {
            const response = await fetch(url, config);
            const data = await response.json();
            return { success: response.ok, data };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    async getSystemStats() {
        return this.request('/system-stats');
    }
    
    async createShare(shareData) {
        return this.request('/shares', {
            method: 'POST',
            body: JSON.stringify(shareData)
        });
    }
    
    async getShares() {
        return this.request('/shares');
    }
}

// Usage
const api = new MoxNASAPI('http://192.168.1.100:8001/api');

// Get system statistics
api.getSystemStats().then(result => {
    if (result.success) {
        console.log(`CPU Usage: ${result.data.cpu.percent}%`);
    }
});

// Create a share
api.createShare({
    name: 'documents',
    type: 'smb',
    path: '/mnt/shares/documents',
    guest: true
}).then(result => {
    console.log(`Share created: ${result.success}`);
});
```

### cURL Examples

```bash
# Get system statistics
curl -X GET http://192.168.1.100:8001/api/system-stats

# Create a share
curl -X POST http://192.168.1.100:8001/api/shares \
  -H "Content-Type: application/json" \
  -d '{
    "name": "documents",
    "type": "smb", 
    "path": "/mnt/shares/documents",
    "guest": true
  }'

# Get service status
curl -X GET http://192.168.1.100:8001/api/services

# Restart a service
curl -X POST http://192.168.1.100:8001/api/services/smbd/restart

# Delete a share
curl -X DELETE http://192.168.1.100:8001/api/shares/documents
```

### Rate Limiting

Currently, no rate limiting is enforced, but it's planned for future releases:
- **Default**: 100 requests per minute per IP
- **Authenticated**: 1000 requests per minute per user
- **Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### API Versioning

Future API versions will be supported:
- **URL Path**: `/api/v2/endpoint`
- **Header**: `Accept: application/vnd.moxnas.v2+json`
- **Backward Compatibility**: Previous versions supported for 2 releases

This completes the comprehensive API documentation for MoxNAS. For implementation details, see the source code in `api-server.py`.