import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Dashboard APIs
export const fetchDashboardData = async () => {
  try {
    const response = await api.get('/proxmox/dashboard/');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to fetch dashboard data');
  }
};

// Container APIs
export const fetchContainers = async () => {
  try {
    const response = await api.get('/containers/');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to fetch containers');
  }
};

export const fetchContainer = async (vmid) => {
  try {
    const response = await api.get(`/containers/${vmid}/`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to fetch container');
  }
};

export const createContainer = async (containerData) => {
  try {
    const response = await api.post('/containers/', containerData);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to create container');
  }
};

export const deleteContainer = async (vmid) => {
  try {
    const response = await api.delete(`/containers/${vmid}/`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to delete container');
  }
};

export const containerAction = async (vmid, action) => {
  try {
    const response = await api.post(`/containers/${vmid}/${action}/`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || `Failed to ${action} container`);
  }
};

// Services APIs
export const fetchServices = async () => {
  try {
    const response = await api.get('/services/status/');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to fetch services');
  }
};

export const fetchContainerServices = async (vmid) => {
  try {
    const response = await api.get(`/containers/${vmid}/services/`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to fetch container services');
  }
};

export const serviceAction = async (vmid, serviceType, action) => {
  try {
    const response = await api.post(`/containers/${vmid}/services/${serviceType}/${action}/`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || `Failed to ${action} service`);
  }
};

// Storage APIs
export const fetchDatasets = async () => {
  try {
    const response = await api.get('/storage/datasets/');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to fetch datasets');
  }
};

export const fetchShares = async () => {
  try {
    const response = await api.get('/storage/shares/');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to fetch shares');
  }
};

// Proxmox APIs
export const testProxmoxConnection = async () => {
  try {
    const response = await api.get('/proxmox/test-connection/');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to test connection');
  }
};

export const fetchProxmoxNodes = async () => {
  try {
    const response = await api.get('/proxmox/nodes/');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to fetch nodes');
  }
};

export const fetchContainerStats = async () => {
  try {
    const response = await api.get('/containers/stats/');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to fetch container stats');
  }
};

export default api;