import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { 
  Container, 
  Plus, 
  Play, 
  Square, 
  Trash2, 
  RefreshCw,
  ExternalLink,
  MoreHorizontal
} from 'lucide-react';
import toast from 'react-hot-toast';
import { fetchContainers, createContainer, deleteContainer, containerAction } from '../services/api';

const Containers = () => {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const queryClient = useQueryClient();

  const { data: containersData, isLoading, error, refetch } = useQuery(
    'containers',
    fetchContainers,
    {
      refetchInterval: 10000, // Refresh every 10 seconds
    }
  );

  const createMutation = useMutation(createContainer, {
    onSuccess: () => {
      queryClient.invalidateQueries('containers');
      setShowCreateModal(false);
      toast.success('Container creation started');
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const deleteMutation = useMutation(deleteContainer, {
    onSuccess: () => {
      queryClient.invalidateQueries('containers');
      toast.success('Container deleted successfully');
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const actionMutation = useMutation(
    ({ vmid, action }) => containerAction(vmid, action),
    {
      onSuccess: (data, variables) => {
        queryClient.invalidateQueries('containers');
        toast.success(`Container ${variables.action} completed`);
      },
      onError: (error) => {
        toast.error(error.message);
      },
    }
  );

  const handleCreateContainer = (formData) => {
    createMutation.mutate({
      name: formData.name,
      hostname: formData.hostname || formData.name,
      memory: parseInt(formData.memory) || 2048,
      cores: parseInt(formData.cores) || 2,
      swap: parseInt(formData.swap) || 512,
    });
  };

  const handleAction = (vmid, action) => {
    if (action === 'delete') {
      if (window.confirm('Are you sure you want to delete this container?')) {
        deleteMutation.mutate(vmid);
      }
    } else {
      actionMutation.mutate({ vmid, action });
    }
  };

  const getStatusBadge = (status) => {
    const statusClasses = {
      running: 'bg-green-100 text-green-800',
      stopped: 'bg-red-100 text-red-800',
      creating: 'bg-blue-100 text-blue-800',
      error: 'bg-yellow-100 text-yellow-800',
    };
    
    return (
      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${statusClasses[status] || 'bg-gray-100 text-gray-800'}`}>
        {status}
      </span>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-600">Loading containers...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="flex">
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">
              Error loading containers
            </h3>
            <div className="mt-2 text-sm text-red-700">
              {error.message}
            </div>
            <div className="mt-4">
              <button
                onClick={() => refetch()}
                className="bg-red-100 hover:bg-red-200 text-red-800 px-4 py-2 rounded-md text-sm font-medium"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const containers = containersData?.containers || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Containers</h1>
          <p className="text-gray-600">Manage your MoxNas containers</p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={() => refetch()}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            Create Container
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center">
            <Container className="h-8 w-8 text-blue-600" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total</p>
              <p className="text-2xl font-semibold text-gray-900">{containersData?.total || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center">
            <Play className="h-8 w-8 text-green-600" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Running</p>
              <p className="text-2xl font-semibold text-gray-900">
                {containers.filter(c => c.status === 'running').length}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center">
            <Square className="h-8 w-8 text-red-600" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Stopped</p>
              <p className="text-2xl font-semibold text-gray-900">
                {containers.filter(c => c.status === 'stopped').length}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center">
            <RefreshCw className="h-8 w-8 text-blue-600" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Creating</p>
              <p className="text-2xl font-semibold text-gray-900">
                {containers.filter(c => c.status === 'creating').length}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Containers Table */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Container List</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Container
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Resources
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  IP Address
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {containers.map((container) => (
                <tr key={container.vmid} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <Container className="h-5 w-5 text-gray-400 mr-3" />
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {container.name}
                        </div>
                        <div className="text-sm text-gray-500">
                          VMID: {container.vmid}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {getStatusBadge(container.status)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {container.memory}MB RAM, {container.cores} CPU
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {container.ip_address || 'N/A'}
                    {container.web_url && (
                      <a
                        href={container.web_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="ml-2 text-blue-600 hover:text-blue-900"
                      >
                        <ExternalLink className="h-4 w-4 inline" />
                      </a>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex space-x-2">
                      {container.status === 'stopped' && (
                        <button
                          onClick={() => handleAction(container.vmid, 'start')}
                          className="text-green-600 hover:text-green-900"
                          disabled={actionMutation.isLoading}
                        >
                          <Play className="h-4 w-4" />
                        </button>
                      )}
                      {container.status === 'running' && (
                        <button
                          onClick={() => handleAction(container.vmid, 'stop')}
                          className="text-red-600 hover:text-red-900"
                          disabled={actionMutation.isLoading}
                        >
                          <Square className="h-4 w-4" />
                        </button>
                      )}
                      <button
                        onClick={() => handleAction(container.vmid, 'delete')}
                        className="text-red-600 hover:text-red-900"
                        disabled={deleteMutation.isLoading}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {containers.length === 0 && (
            <div className="text-center py-12">
              <Container className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No containers</h3>
              <p className="mt-1 text-sm text-gray-500">
                Get started by creating a new container.
              </p>
              <div className="mt-6">
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Create Container
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create Container Modal */}
      {showCreateModal && (
        <CreateContainerModal
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateContainer}
          isLoading={createMutation.isLoading}
        />
      )}
    </div>
  );
};

const CreateContainerModal = ({ onClose, onSubmit, isLoading }) => {
  const [formData, setFormData] = useState({
    name: '',
    hostname: '',
    memory: '2048',
    cores: '2',
    swap: '512',
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 transition-opacity">
          <div className="absolute inset-0 bg-gray-500 opacity-75" onClick={onClose}></div>
        </div>

        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <form onSubmit={handleSubmit}>
            <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
              <div className="sm:flex sm:items-start">
                <div className="mt-3 text-center sm:mt-0 sm:text-left w-full">
                  <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                    Create New Container
                  </h3>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        Container Name
                      </label>
                      <input
                        type="text"
                        name="name"
                        value={formData.name}
                        onChange={handleChange}
                        required
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                        placeholder="moxnas-container"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        Hostname (optional)
                      </label>
                      <input
                        type="text"
                        name="hostname"
                        value={formData.hostname}
                        onChange={handleChange}
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                        placeholder="Leave empty to use container name"
                      />
                    </div>
                    
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700">
                          Memory (MB)
                        </label>
                        <input
                          type="number"
                          name="memory"
                          value={formData.memory}
                          onChange={handleChange}
                          min="512"
                          className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700">
                          CPU Cores
                        </label>
                        <input
                          type="number"
                          name="cores"
                          value={formData.cores}
                          onChange={handleChange}
                          min="1"
                          max="32"
                          className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700">
                          Swap (MB)
                        </label>
                        <input
                          type="number"
                          name="swap"
                          value={formData.swap}
                          onChange={handleChange}
                          min="0"
                          className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
              <button
                type="submit"
                disabled={isLoading}
                className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50"
              >
                {isLoading ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create Container'
                )}
              </button>
              <button
                type="button"
                onClick={onClose}
                className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Containers;