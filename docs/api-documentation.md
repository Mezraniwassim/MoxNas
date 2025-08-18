# MoxNAS API Documentation

MoxNAS provides a comprehensive REST API for programmatic management of your NAS system.

## Base URL

All API endpoints are relative to:
```
http://YOUR-CONTAINER-IP:8000/api/
```

## Authentication

MoxNAS uses token-based authentication. Include the token in the Authorization header:

```bash
Authorization: Bearer YOUR-TOKEN-HERE
```

### Obtaining a Token

```bash
curl -X POST http://YOUR-CONTAINER-IP:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'
```

Response:
```json
{
  "token": "your-access-token",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com"
  }
}
```

## Storage Management

### Storage Pools

#### List Pools
```bash
GET /api/storage/pools/
```

#### Create Pool
```bash
POST /api/storage/pools/
Content-Type: application/json

{
  "name": "tank",
  "type": "mirror",
  "disks": ["sda", "sdb"]
}
```

#### Get Pool Details
```bash
GET /api/storage/pools/{id}/
```

#### Pool Operations
```bash
# Start scrub
POST /api/storage/pools/{id}/scrub/

# Get pool status
GET /api/storage/pools/{id}/status/
```

### Disks

#### List Disks
```bash
GET /api/storage/disks/
```

#### Get SMART Data
```bash
GET /api/storage/disks/{id}/smart/
```

#### Run SMART Test
```bash
POST /api/storage/disks/{id}/test/
Content-Type: application/json

{
  "type": "short"  # or "long", "conveyance"
}
```

### Datasets

#### List Datasets
```bash
GET /api/storage/datasets/
```

#### Create Dataset
```bash
POST /api/storage/datasets/
Content-Type: application/json

{
  "name": "documents",
  "pool": 1,
  "mount_point": "/tank/documents",
  "compression": "lz4",
  "quota": 107374182400  # 100GB in bytes
}
```

#### Create Snapshot
```bash
POST /api/storage/datasets/{id}/create_snapshot/
Content-Type: application/json

{
  "name": "backup-2024-01-15"
}
```

### Snapshots

#### List Snapshots
```bash
GET /api/storage/snapshots/
```

#### Rollback to Snapshot
```bash
POST /api/storage/snapshots/{id}/rollback/
```

#### Clone Snapshot
```bash
POST /api/storage/snapshots/{id}/clone/
Content-Type: application/json

{
  "name": "clone-dataset-name"
}
```

## Share Management

### SMB/CIFS Shares

#### List SMB Shares
```bash
GET /api/shares/smb/
```

#### Create SMB Share
```bash
POST /api/shares/smb/
Content-Type: application/json

{
  "name": "documents",
  "path": "/tank/documents",
  "comment": "Document storage",
  "read_only": false,
  "guest_ok": false,
  "valid_users": ["user1", "user2"]
}
```

### NFS Exports

#### List NFS Exports
```bash
GET /api/shares/nfs/
```

#### Create NFS Export
```bash
POST /api/shares/nfs/
Content-Type: application/json

{
  "path": "/tank/data",
  "clients": [
    {
      "network": "192.168.1.0/24",
      "options": ["rw", "sync", "no_subtree_check"]
    }
  ]
}
```

### FTP Shares

#### List FTP Users
```bash
GET /api/shares/ftp/
```

#### Create FTP User
```bash
POST /api/shares/ftp/
Content-Type: application/json

{
  "username": "ftpuser",
  "password": "secure-password",
  "home_directory": "/tank/ftp",
  "permissions": ["read", "write", "delete"]
}
```

## User Management

### Users

#### List Users
```bash
GET /api/users/
```

#### Create User
```bash
POST /api/users/
Content-Type: application/json

{
  "username": "newuser",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "password": "secure-password",
  "groups": [1, 2]
}
```

### Groups

#### List Groups
```bash
GET /api/users/groups/
```

#### Create Group
```bash
POST /api/users/groups/
Content-Type: application/json

{
  "name": "editors",
  "description": "Content editors group"
}
```

## Network Management

### Network Interfaces

#### List Interfaces
```bash
GET /api/network/interfaces/
```

#### Configure Interface
```bash
PUT /api/network/interfaces/{name}/
Content-Type: application/json

{
  "method": "static",
  "address": "192.168.1.100",
  "netmask": "255.255.255.0",
  "gateway": "192.168.1.1"
}
```

### DNS Configuration

#### Get DNS Settings
```bash
GET /api/network/dns/
```

#### Update DNS Settings
```bash
PUT /api/network/dns/
Content-Type: application/json

{
  "nameservers": ["8.8.8.8", "8.8.4.4"],
  "search_domains": ["local", "example.com"]
}
```

## Service Management

### Service Control

#### List Services
```bash
GET /api/services/
```

#### Service Status
```bash
GET /api/services/{name}/status/
```

#### Start Service
```bash
POST /api/services/{name}/start/
```

#### Stop Service
```bash
POST /api/services/{name}/stop/
```

#### Restart Service
```bash
POST /api/services/{name}/restart/
```

## System Information

### System Stats

#### Get System Information
```bash
GET /api/system/info/
```

Response:
```json
{
  "hostname": "moxnas",
  "uptime": 86400,
  "load_average": [0.5, 0.3, 0.2],
  "cpu_usage": 15.2,
  "memory": {
    "total": 2147483648,
    "used": 1073741824,
    "free": 1073741824,
    "percentage": 50.0
  },
  "disk_usage": [
    {
      "mountpoint": "/",
      "total": 10737418240,
      "used": 2147483648,
      "free": 8589934592,
      "percentage": 20.0
    }
  ]
}
```

#### Get Real-time Stats
```bash
GET /api/system/stats/
```

### Logs

#### Get System Logs
```bash
GET /api/system/logs/?service=moxnas&lines=100
```

Query parameters:
- `service`: Filter by service name
- `lines`: Number of lines to return (default: 50)
- `level`: Log level filter (error, warning, info, debug)

## WebSocket API

MoxNAS provides real-time updates via WebSocket connections.

### Connection

```javascript
const ws = new WebSocket('ws://YOUR-CONTAINER-IP:8000/ws/');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
```

### Subscribing to Updates

```javascript
// Subscribe to system stats
ws.send(JSON.stringify({
    'action': 'subscribe',
    'channel': 'system_stats'
}));

// Subscribe to storage events
ws.send(JSON.stringify({
    'action': 'subscribe',
    'channel': 'storage_events'
}));
```

### Available Channels

- `system_stats`: Real-time system performance data
- `storage_events`: Storage pool and dataset events
- `service_status`: Service state changes
- `alerts`: System alerts and notifications

## Error Handling

### HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource already exists
- `500 Internal Server Error`: Server error

### Error Response Format

```json
{
  "error": "Error description",
  "details": {
    "field": ["Field-specific error message"]
  },
  "code": "ERROR_CODE"
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Authentication endpoints**: 5 requests per minute
- **Read operations**: 100 requests per minute
- **Write operations**: 30 requests per minute

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Examples

### Python Example

```python
import requests

# Authentication
response = requests.post('http://192.168.1.100:8000/api/auth/login/', 
                        json={'username': 'admin', 'password': 'password'})
token = response.json()['token']

headers = {'Authorization': f'Bearer {token}'}

# Get storage pools
pools = requests.get('http://192.168.1.100:8000/api/storage/pools/', 
                    headers=headers)
print(pools.json())

# Create snapshot
snapshot_data = {'name': f'auto-{int(time.time())}'}
response = requests.post(f'http://192.168.1.100:8000/api/storage/datasets/1/create_snapshot/',
                        json=snapshot_data, headers=headers)
```

### curl Examples

```bash
# Get token
TOKEN=$(curl -s -X POST http://192.168.1.100:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}' | \
  jq -r '.token')

# Create dataset
curl -X POST http://192.168.1.100:8000/api/storage/datasets/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "backup",
    "pool": 1,
    "mount_point": "/tank/backup",
    "compression": "lz4"
  }'

# Get system stats
curl -H "Authorization: Bearer $TOKEN" \
  http://192.168.1.100:8000/api/system/stats/
```

## SDK and Libraries

Official SDKs are available for:

- **Python**: `pip install moxnas-python-sdk`
- **JavaScript/Node.js**: `npm install moxnas-js-sdk`
- **Go**: Available on GitHub

### Python SDK Example

```python
from moxnas import MoxNASClient

client = MoxNASClient('http://192.168.1.100:8000', 'your-token')

# List pools
pools = client.storage.pools.list()

# Create snapshot
snapshot = client.storage.datasets.create_snapshot(
    dataset_id=1, 
    name='my-snapshot'
)
```

For complete API reference and more examples, visit the interactive API documentation at:
`http://YOUR-CONTAINER-IP:8000/api/docs/`