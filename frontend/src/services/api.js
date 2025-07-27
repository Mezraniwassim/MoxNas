import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for authentication
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Token ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// API endpoints
export const systemAPI = {
  getSystemInfo: () => api.get('/core/system/current/'),
  getServices: () => api.get('/core/services/'),
  startService: (id) => api.post(`/core/services/${id}/start/`),
  stopService: (id) => api.post(`/core/services/${id}/stop/`),
  restartService: (id) => api.post(`/core/services/${id}/restart/`),
  getLogs: () => api.get('/core/logs/recent/'),
};

export const storageAPI = {
  getDatasets: () => api.get('/storage/datasets/'),
  createDataset: (data) => api.post('/storage/datasets/', data),
  updateDataset: (id, data) => api.put(`/storage/datasets/${id}/`, data),
  deleteDataset: (id) => api.delete(`/storage/datasets/${id}/`),
  
  getShares: () => api.get('/storage/shares/'),
  createShare: (data) => api.post('/storage/shares/', data),
  updateShare: (id, data) => api.put(`/storage/shares/${id}/`, data),
  deleteShare: (id) => api.delete(`/storage/shares/${id}/`),
  
  getMountPoints: () => api.get('/storage/mounts/'),
  createMountPoint: (data) => api.post('/storage/mounts/', data),
  mountFilesystem: (id) => api.post(`/storage/mounts/${id}/mount/`),
  unmountFilesystem: (id) => api.post(`/storage/mounts/${id}/unmount/`),
  checkMounts: () => api.get('/storage/mounts/check_mounts/'),
};

export const networkAPI = {
  getInterfaces: () => api.get('/network/interfaces/'),
  updateInterface: (id, data) => api.put(`/network/interfaces/${id}/`, data),
};

export const usersAPI = {
  getUsers: () => api.get('/users/users/'),
  createUser: (data) => api.post('/users/users/', data),
  updateUser: (id, data) => api.put(`/users/users/${id}/`, data),
  deleteUser: (id) => api.delete(`/users/users/${id}/`),
  setUserPassword: (id, password) => api.post(`/users/users/${id}/set_password/`, { password }),
  
  getGroups: () => api.get('/users/groups/'),
  createGroup: (data) => api.post('/users/groups/', data),
  updateGroup: (id, data) => api.put(`/users/groups/${id}/`, data),
  deleteGroup: (id) => api.delete(`/users/groups/${id}/`),
  addUserToGroup: (groupId, userId) => api.post(`/users/groups/${groupId}/add_user/`, { user_id: userId }),
  
  getACLs: () => api.get('/users/acl/'),
  createACL: (data) => api.post('/users/acl/', data),
  updateACL: (id, data) => api.put(`/users/acl/${id}/`, data),
  deleteACL: (id) => api.delete(`/users/acl/${id}/`),
  getPathACLs: (path) => api.get(`/users/acl/path_acls/?path=${encodeURIComponent(path)}`),
};

export const proxmoxAPI = {
  getNodes: () => api.get('/proxmox/nodes/'),
  createNode: (data) => api.post('/proxmox/nodes/', data),
  updateNode: (id, data) => api.put(`/proxmox/nodes/${id}/`, data),
  deleteNode: (id) => api.delete(`/proxmox/nodes/${id}/`),
  testConnection: (id) => api.post(`/proxmox/nodes/${id}/test_connection/`),
  
  getContainers: () => api.get('/proxmox/containers/'),
  createMoxNASContainer: (data) => api.post('/proxmox/containers/create_moxnas_container/', data),
  startContainer: (id) => api.post(`/proxmox/containers/${id}/start/`),
  stopContainer: (id) => api.post(`/proxmox/containers/${id}/stop/`),
  syncContainers: () => api.get('/proxmox/containers/sync_from_proxmox/'),
};

export const servicesAPI = {
  // Service Configuration
  getServiceConfigs: () => api.get('/services/config/'),
  createServiceConfig: (data) => api.post('/services/config/', data),
  updateServiceConfig: (id, data) => api.put(`/services/config/${id}/`, data),
  deleteServiceConfig: (id) => api.delete(`/services/config/${id}/`),
  
  // Service Management
  getServicesStatus: () => api.get('/services/status/'),
  startService: (name) => api.post(`/services/start/${name}/`),
  stopService: (name) => api.post(`/services/stop/${name}/`),
  restartService: (name) => api.post(`/services/restart/${name}/`),
  
  // Cloud Sync Tasks
  getCloudSyncTasks: () => api.get('/services/cloud-sync/'),
  createCloudSyncTask: (data) => api.post('/services/cloud-sync/', data),
  updateCloudSyncTask: (id, data) => api.put(`/services/cloud-sync/${id}/`, data),
  deleteCloudSyncTask: (id) => api.delete(`/services/cloud-sync/${id}/`),
  runCloudSyncTask: (id) => api.post(`/services/cloud-sync/${id}/run/`),
  
  // Rsync Tasks
  getRsyncTasks: () => api.get('/services/rsync/'),
  createRsyncTask: (data) => api.post('/services/rsync/', data),
  updateRsyncTask: (id, data) => api.put(`/services/rsync/${id}/`, data),
  deleteRsyncTask: (id) => api.delete(`/services/rsync/${id}/`),
  runRsyncTask: (id) => api.post(`/services/rsync/${id}/run/`),
  
  // Task Logs
  getTaskLogs: () => api.get('/services/task-logs/'),
  getTaskLog: (id) => api.get(`/services/task-logs/${id}/`),
  
  // UPS Configuration
  getUPSConfigs: () => api.get('/services/ups/'),
  createUPSConfig: (data) => api.post('/services/ups/', data),
  updateUPSConfig: (id, data) => api.put(`/services/ups/${id}/`, data),
  deleteUPSConfig: (id) => api.delete(`/services/ups/${id}/`),
};

export default api;