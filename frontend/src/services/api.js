import axios from 'axios';
import Cookies from 'js-cookie';
import toast from 'react-hot-toast';

const API_BASE_URL = process.env.REACT_APP_API_URL || '';

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    const csrfToken = Cookies.get('csrftoken');
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      Cookies.remove('sessionid');
      window.location.href = '/login';
      toast.error('Session expired. Please log in again.');
    } else if (error.response?.status >= 500) {
      toast.error('Server error. Please try again later.');
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  login: (credentials) => api.post('/api/auth/login/', credentials),
  logout: () => api.post('/api/auth/logout/'),
  getUser: () => api.get('/api/auth/user/'),
  getCsrfToken: () => api.get('/api/auth/csrf/'),
};

export const systemAPI = {
  getSystemStats: () => api.get('/api/system/stats/'),
  getSystemInfo: () => api.get('/api/system/info/'),
  getSystemLogs: (params) => api.get('/api/system/logs/', { params }),
  updateSystemSettings: (settings) => api.patch('/api/system/settings/', settings),
  getSystemSettings: () => api.get('/api/system/settings/'),
  rebootSystem: () => api.post('/api/system/reboot/'),
  shutdownSystem: () => api.post('/api/system/shutdown/'),
};

export const storageAPI = {
  getDisks: () => api.get('/api/storage/disks/'),
  getDisk: (id) => api.get(`/api/storage/disks/${id}/`),
  createPool: (data) => api.post('/api/storage/pools/', data),
  getPools: () => api.get('/api/storage/pools/'),
  getPool: (id) => api.get(`/api/storage/pools/${id}/`),
  updatePool: (id, data) => api.patch(`/api/storage/pools/${id}/`, data),
  deletePool: (id) => api.delete(`/api/storage/pools/${id}/`),
  getMountPoints: () => api.get('/api/storage/mount-points/'),
  createMountPoint: (data) => api.post('/api/storage/mount-points/', data),
  deleteMountPoint: (id) => api.delete(`/api/storage/mount-points/${id}/`),
  getUsage: () => api.get('/api/storage/usage/'),
  scanDisks: () => api.post('/api/storage/scan/'),
};

export const sharesAPI = {
  getShares: () => api.get('/api/shares/'),
  getShare: (id) => api.get(`/api/shares/${id}/`),
  createShare: (data) => api.post('/api/shares/', data),
  updateShare: (id, data) => api.patch(`/api/shares/${id}/`, data),
  deleteShare: (id) => api.delete(`/api/shares/${id}/`),
  toggleShare: (id) => api.post(`/api/shares/${id}/toggle/`),
  getPermissions: (shareId) => api.get(`/api/shares/${shareId}/permissions/`),
  updatePermissions: (shareId, data) => api.patch(`/api/shares/${shareId}/permissions/`, data),
};

export const usersAPI = {
  getUsers: () => api.get('/api/users/'),
  getUser: (id) => api.get(`/api/users/${id}/`),
  createUser: (data) => api.post('/api/users/', data),
  updateUser: (id, data) => api.patch(`/api/users/${id}/`, data),
  deleteUser: (id) => api.delete(`/api/users/${id}/`),
  changePassword: (id, data) => api.post(`/api/users/${id}/change-password/`, data),
  getGroups: () => api.get('/api/users/groups/'),
  createGroup: (data) => api.post('/api/users/groups/', data),
  updateGroup: (id, data) => api.patch(`/api/users/groups/${id}/`, data),
  deleteGroup: (id) => api.delete(`/api/users/groups/${id}/`),
};

export const servicesAPI = {
  getServices: () => api.get('/api/services/'),
  getService: (name) => api.get(`/api/services/${name}/`),
  startService: (name) => api.post(`/api/services/${name}/start/`),
  stopService: (name) => api.post(`/api/services/${name}/stop/`),
  restartService: (name) => api.post(`/api/services/${name}/restart/`),
  enableService: (name) => api.post(`/api/services/${name}/enable/`),
  disableService: (name) => api.post(`/api/services/${name}/disable/`),
  getServiceLogs: (name, params) => api.get(`/api/services/${name}/logs/`, { params }),
  updateServiceConfig: (name, config) => api.patch(`/api/services/${name}/config/`, config),
};

export const networkAPI = {
  getInterfaces: () => api.get('/api/network/interfaces/'),
  getInterface: (name) => api.get(`/api/network/interfaces/${name}/`),
  updateInterface: (name, data) => api.patch(`/api/network/interfaces/${name}/`, data),
  getRoutes: () => api.get('/api/network/routes/'),
  addRoute: (data) => api.post('/api/network/routes/', data),
  deleteRoute: (id) => api.delete(`/api/network/routes/${id}/`),
  getDnsSettings: () => api.get('/api/network/dns/'),
  updateDnsSettings: (data) => api.patch('/api/network/dns/', data),
  getFirewallRules: () => api.get('/api/network/firewall/'),
  addFirewallRule: (data) => api.post('/api/network/firewall/', data),
  deleteFirewallRule: (id) => api.delete(`/api/network/firewall/${id}/`),
};

export default api;