# Proxmox Storage Management Integration

This document describes the comprehensive storage management features added to MoxNAS for managing Proxmox storage directly from the MoxNAS interface.

## 🎯 New Features Added

### 1. **Proxmox Storage Management**
- **View all storage backends**: Directory, NFS, CIFS, LVM, ZFS, CephFS, GlusterFS, iSCSI
- **Storage usage monitoring**: Real-time space usage with visual progress bars
- **Storage synchronization**: Sync storage configurations from Proxmox
- **Directory management**: Create directories on storage backends
- **Content browsing**: List and browse storage contents

### 2. **Container Storage Mounts**
- **Mount point management**: Add/remove storage mounts to/from containers
- **Dynamic mount configuration**: Configure host paths and container mount points
- **Container storage overview**: View all mounts for each container
- **Storage backend integration**: Mount Proxmox storage directly to containers

### 3. **Backup & Snapshot Management**
- **Backup creation**: Create backups of containers with compression options
- **Backup listing**: View all available backups with metadata
- **Storage selection**: Choose backup destination storage
- **Compression options**: LZO, GZip, ZSTD compression support
- **Task tracking**: Monitor backup progress and status

## 📁 Files Added/Modified

### Backend Files
1. **`backend/proxmox_integration/storage_views.py`** - New storage management views
2. **`backend/proxmox_integration/urls.py`** - Updated URL routing
3. **`backend/proxmox_integration/models.py`** - Enhanced storage models (existing)

### Frontend Files
1. **`frontend/src/components/ProxmoxStorageManager.js`** - New storage management component
2. **`frontend/src/pages/Proxmox.js`** - Updated to include storage tab

## 🔧 API Endpoints Added

### Storage Management
- `GET /api/proxmox-storage/` - List all storage configurations
- `POST /api/proxmox-storage/sync_from_proxmox/` - Sync storage from Proxmox
- `GET /api/proxmox-storage/get_usage_stats/` - Get storage usage statistics
- `POST /api/proxmox-storage/{id}/create_directory/` - Create directory on storage
- `GET /api/proxmox-storage/{id}/list_contents/` - List storage contents

### Container Storage Mounts
- `GET /api/container-storage/list_container_mounts/` - List container mounts
- `POST /api/container-storage/add_mount/` - Add storage mount to container
- `DELETE /api/container-storage/remove_mount/` - Remove storage mount from container

### Backup Management
- `GET /api/proxmox-backups/list_backups/` - List all backups
- `POST /api/proxmox-backups/create_backup/` - Create container backup

## 🎨 User Interface Features

### Storage Tab Layout
The new storage management interface includes three main tabs:

#### **Storage Management Tab**
- **Storage Overview Table**: Shows all configured storage with:
  - Storage ID and type with color-coded badges
  - Server/path information for network storage
  - Usage statistics with progress bars
  - Content types supported
  - Enable/disable status
  - Actions (browse, manage)

- **Storage Actions**:
  - **Sync from Proxmox**: Updates storage list from Proxmox API
  - **Create Directory**: Create new directories on selected storage

#### **Container Mounts Tab**
- **Container Grid View**: Shows all containers with:
  - Container status and basic info
  - Current mount points (when available)
  - Resource allocation details

- **Mount Management**:
  - **Add Mount Point**: Modal for adding new storage mounts
  - **Configure Paths**: Set container mount point and host path
  - **Storage Selection**: Choose from available Proxmox storage

#### **Backups & Snapshots Tab**
- **Backup List Table**: Shows all backups with:
  - Backup filename and metadata
  - Container information
  - File size and creation date
  - Restore/delete actions

- **Backup Creation**:
  - **Container Selection**: Choose container to backup
  - **Storage Selection**: Choose backup destination
  - **Compression Options**: Select compression algorithm

## 💡 Usage Examples

### Managing Storage
```javascript
// Sync storage from Proxmox
const response = await api.post('/api/proxmox-storage/sync_from_proxmox/', {
    host_id: 1
});

// Create directory on storage
const response = await api.post('/api/proxmox-storage/1/create_directory/', {
    path: 'new-directory'
});
```

### Container Mount Management
```javascript
// Add mount point to container
const response = await api.post('/api/container-storage/add_mount/', {
    container_id: 1,
    storage_id: 'local-lvm',
    mount_point: '/mnt/storage',
    host_path: '/host/storage'
});
```

### Backup Management
```javascript
// Create backup
const response = await api.post('/api/proxmox-backups/create_backup/', {
    container_id: 1,
    storage_id: 'backup-storage',
    compression: 'lzo'
});
```

## 🔗 Integration Benefits

### For MoxNAS Users
1. **Centralized Management**: Manage Proxmox storage directly from MoxNAS
2. **Visual Storage Monitoring**: See storage usage across all Proxmox backends
3. **Container Storage**: Easily configure storage mounts for containers
4. **Backup Management**: Create and manage container backups
5. **Multi-Storage Support**: Work with different storage types (NFS, CIFS, local, etc.)

### For System Administrators
1. **Storage Pool Management**: Monitor and manage storage pools
2. **Capacity Planning**: Visual usage statistics for capacity planning
3. **Backup Automation**: Programmatic backup creation and management
4. **Multi-Host Support**: Manage storage across multiple Proxmox hosts
5. **Container Deployment**: Streamlined container storage configuration

## 🚀 Future Enhancements

The storage management interface is designed to be extensible. Future enhancements could include:

1. **Snapshot Management**: Create and manage ZFS/LVM snapshots
2. **Storage Replication**: Configure storage replication between hosts
3. **Automated Backup Scheduling**: Schedule automatic backups
4. **Storage Templates**: Pre-configured storage setups
5. **Performance Monitoring**: I/O statistics and performance metrics
6. **Storage Migration**: Move data between storage backends

## 🔧 Technical Architecture

The storage management system follows MoxNAS's existing architecture:

- **Django REST API**: Backend storage management logic
- **React Components**: Modern UI with responsive design
- **Proxmox API Integration**: Direct communication with Proxmox VE
- **Real-time Updates**: Live storage usage and status updates
- **Error Handling**: Comprehensive error handling and user feedback
- **Security**: Proper authentication and authorization

This integration makes MoxNAS a complete solution for managing not just NAS services, but also the underlying Proxmox infrastructure and storage systems.