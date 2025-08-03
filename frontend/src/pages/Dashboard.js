import React from 'react';
import { useQuery } from 'react-query';
import { 
  Server, 
  Container, 
  Activity, 
  HardDrive,
  RefreshCw
} from 'lucide-react';
import { fetchDashboardData } from '../services/api';

const Dashboard = () => {
  const { data: dashboardData, isLoading, error, refetch } = useQuery(
    'dashboard',
    fetchDashboardData,
    {
      refetchInterval: 30000, // Refresh every 30 seconds
    }
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-600">Loading dashboard...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="flex">
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">
              Error loading dashboard
            </h3>
            <div className="mt-2 text-sm text-red-700">
              {error.message || 'Failed to fetch dashboard data'}
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

  const stats = [
    {
      name: 'Total Containers',
      value: dashboardData?.containers?.total || 0,
      icon: Container,
      color: 'blue',
    },
    {
      name: 'Running Containers',
      value: dashboardData?.containers?.running || 0,
      icon: Activity,
      color: 'green',
    },
    {
      name: 'Proxmox Nodes',
      value: dashboardData?.nodes?.length || 0,
      icon: Server,
      color: 'purple',
    },
    {
      name: 'Storage Used',
      value: '45%',
      icon: HardDrive,
      color: 'yellow',
    },
  ];

  const getColorClasses = (color) => {
    const colors = {
      blue: 'bg-blue-50 text-blue-600',
      green: 'bg-green-50 text-green-600',
      purple: 'bg-purple-50 text-purple-600',
      yellow: 'bg-yellow-50 text-yellow-600',
    };
    return colors[color] || colors.blue;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <button
          onClick={() => refetch()}
          className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div
              key={stat.name}
              className="bg-white rounded-lg shadow p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-center">
                <div className={`p-2 rounded-md ${getColorClasses(stat.color)}`}>
                  <Icon className="h-6 w-6" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                  <p className="text-2xl font-semibold text-gray-900">{stat.value}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Containers Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Containers */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Recent Containers</h3>
          </div>
          <div className="p-6">
            {dashboardData?.containers?.list?.slice(0, 5).map((container) => (
              <div key={container.vmid} className="flex items-center justify-between py-3 border-b border-gray-100 last:border-b-0">
                <div className="flex items-center">
                  <Container className="h-5 w-5 text-gray-400 mr-3" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      Container {container.vmid}
                    </p>
                    <p className="text-xs text-gray-500">{container.name || 'Unnamed'}</p>
                  </div>
                </div>
                <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                  container.status === 'running' 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  {container.status}
                </span>
              </div>
            )) || (
              <p className="text-gray-500 text-center py-4">No containers found</p>
            )}
          </div>
        </div>

        {/* System Status */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">System Status</h3>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Proxmox Connection</span>
                <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                  dashboardData?.connection_status 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-red-100 text-red-800'
                }`}>
                  {dashboardData?.connection_status ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Node Status</span>
                <span className="text-sm font-medium text-gray-900">
                  {dashboardData?.node_status?.status || 'Unknown'}
                </span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Uptime</span>
                <span className="text-sm font-medium text-gray-900">
                  {dashboardData?.node_status?.uptime 
                    ? Math.floor(dashboardData.node_status.uptime / 86400) + ' days'
                    : 'Unknown'
                  }
                </span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Memory Usage</span>
                <span className="text-sm font-medium text-gray-900">
                  {dashboardData?.node_status?.memory 
                    ? `${Math.round((dashboardData.node_status.memory.used / dashboardData.node_status.memory.total) * 100)}%`
                    : 'Unknown'
                  }
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;