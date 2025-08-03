import React from 'react';
import { useQuery } from 'react-query';
import { Server, Play, Square, Settings } from 'lucide-react';
import { fetchServices } from '../services/api';

const Services = () => {
  const { data: servicesData, isLoading, error } = useQuery(
    'services',
    fetchServices
  );

  const services = [
    { name: 'FTP Server', type: 'ftp', port: 21, status: 'stopped', description: 'File Transfer Protocol service' },
    { name: 'NFS Server', type: 'nfs', port: 2049, status: 'stopped', description: 'Network File System service' },
    { name: 'SMB/CIFS', type: 'smb', port: 445, status: 'stopped', description: 'Windows file sharing service' },
    { name: 'SSH Server', type: 'ssh', port: 22, status: 'running', description: 'Secure Shell service' },
  ];

  const getStatusBadge = (status) => {
    const statusClasses = {
      running: 'bg-green-100 text-green-800',
      stopped: 'bg-red-100 text-red-800',
    };
    
    return (
      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${statusClasses[status] || 'bg-gray-100 text-gray-800'}`}>
        {status}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Services</h1>
        <p className="text-gray-600">Manage NAS services and their configurations</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {services.map((service) => (
          <div key={service.type} className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <Server className="h-8 w-8 text-blue-600" />
              {getStatusBadge(service.status)}
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">{service.name}</h3>
            <p className="text-sm text-gray-600 mb-4">{service.description}</p>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Port: {service.port}</span>
              <div className="flex space-x-2">
                <button className="text-green-600 hover:text-green-800">
                  <Play className="h-4 w-4" />
                </button>
                <button className="text-red-600 hover:text-red-800">
                  <Square className="h-4 w-4" />
                </button>
                <button className="text-gray-600 hover:text-gray-800">
                  <Settings className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Services;