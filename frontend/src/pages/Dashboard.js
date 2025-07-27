import React, { useState, useEffect } from 'react';
import { FaMicrochip, FaMemory, FaHdd, FaClock, FaPlay, FaStop, FaRedo, FaTachometerAlt, FaServer, FaNetworkWired } from 'react-icons/fa';
import { systemAPI } from '../services/api';

const Dashboard = () => {
  const [systemInfo, setSystemInfo] = useState(null);
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [systemResponse, servicesResponse] = await Promise.all([
        systemAPI.getSystemInfo(),
        systemAPI.getServices()
      ]);
      
      setSystemInfo(systemResponse.data);
      setServices(servicesResponse.data);
      setLoading(false);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
      setLoading(false);
    }
  };

  const handleServiceAction = async (serviceId, action) => {
    try {
      let response;
      switch (action) {
        case 'start':
          response = await systemAPI.startService(serviceId);
          break;
        case 'stop':
          response = await systemAPI.stopService(serviceId);
          break;
        case 'restart':
          response = await systemAPI.restartService(serviceId);
          break;
        default:
          return;
      }
      
      if (response.data.success) {
        loadData();
      } else {
        alert(response.data.message || 'Action failed');
      }
    } catch (error) {
      console.error('Service action error:', error);
      alert('Failed to perform action');
    }
  };

  const formatUptime = (seconds) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    return `${days}d ${hours}h`;
  };


  if (loading || !systemInfo) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '200px' }}>
        <div className="moxnas-spinner"></div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.875rem', fontWeight: '600' }}>
          <FaTachometerAlt />
          Dashboard
        </h1>
        <div className="moxnas-status moxnas-status-info">{systemInfo.hostname}</div>
      </div>

      {/* System Overview Cards */}
      <div className="moxnas-grid moxnas-grid-cols-4" style={{ marginBottom: '2rem' }}>
        <div className="moxnas-stats-card" style={{ background: 'linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%)' }}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.5rem' }}>
            <FaMicrochip size={24} style={{ marginRight: '0.5rem' }} />
            <span style={{ fontSize: '0.875rem', opacity: 0.9 }}>CPU Usage</span>
          </div>
          <div className="moxnas-stats-value">{systemInfo.cpu_usage?.toFixed(1)}%</div>
          <div className="moxnas-progress">
            <div 
              className="moxnas-progress-bar" 
              style={{ width: `${systemInfo.cpu_usage || 0}%`, backgroundColor: 'rgba(255, 255, 255, 0.3)' }}
            ></div>
          </div>
        </div>

        <div className="moxnas-stats-card" style={{ background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)' }}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.5rem' }}>
            <FaMemory size={24} style={{ marginRight: '0.5rem' }} />
            <span style={{ fontSize: '0.875rem', opacity: 0.9 }}>Memory Usage</span>
          </div>
          <div className="moxnas-stats-value">{systemInfo.memory_usage?.percent?.toFixed(1)}%</div>
          <div className="moxnas-progress">
            <div 
              className="moxnas-progress-bar" 
              style={{ width: `${systemInfo.memory_usage?.percent || 0}%`, backgroundColor: 'rgba(255, 255, 255, 0.3)' }}
            ></div>
          </div>
        </div>

        <div className="moxnas-stats-card" style={{ background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)' }}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.5rem' }}>
            <FaHdd size={24} style={{ marginRight: '0.5rem' }} />
            <span style={{ fontSize: '0.875rem', opacity: 0.9 }}>Disk Usage</span>
          </div>
          <div className="moxnas-stats-value">{systemInfo.disk_usage?.percent?.toFixed(1)}%</div>
          <div className="moxnas-progress">
            <div 
              className="moxnas-progress-bar" 
              style={{ width: `${systemInfo.disk_usage?.percent || 0}%`, backgroundColor: 'rgba(255, 255, 255, 0.3)' }}
            ></div>
          </div>
        </div>

        <div className="moxnas-stats-card" style={{ background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)' }}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.5rem' }}>
            <FaClock size={24} style={{ marginRight: '0.5rem' }} />
            <span style={{ fontSize: '0.875rem', opacity: 0.9 }}>System Uptime</span>
          </div>
          <div className="moxnas-stats-value" style={{ fontSize: '1.5rem' }}>{formatUptime(systemInfo.uptime)}</div>
        </div>
      </div>

      {/* Services Status */}
      <div className="moxnas-grid moxnas-grid-cols-1" style={{ marginBottom: '2rem' }}>
        <div className="moxnas-card">
          <div className="moxnas-card-header">
            <h3 className="moxnas-card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FaServer />
              Services Status
            </h3>
          </div>
          <div className="moxnas-card-body">
            <table className="moxnas-table">
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Port</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {Array.isArray(services) ? services.map((service) => (
                  <tr key={service.id}>
                    <td>
                      <strong>{service.name.toUpperCase()}</strong>
                    </td>
                    <td>{service.port}</td>
                    <td>
                      <span className={`moxnas-status ${service.running ? 'moxnas-status-success' : 'moxnas-status-error'}`}>
                        {service.running ? 'Running' : 'Stopped'}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.25rem' }}>
                        <button 
                          className="moxnas-btn moxnas-btn-success"
                          onClick={() => handleServiceAction(service.id, 'start')}
                          style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                        >
                          <FaPlay />
                        </button>
                        <button 
                          className="moxnas-btn moxnas-btn-warning"
                          onClick={() => handleServiceAction(service.id, 'restart')}
                          style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                        >
                          <FaRedo />
                        </button>
                        <button 
                          className="moxnas-btn moxnas-btn-danger"
                          onClick={() => handleServiceAction(service.id, 'stop')}
                          style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                        >
                          <FaStop />
                        </button>
                      </div>
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan="4" style={{ textAlign: 'center', padding: '1rem' }}>
                      No services data available
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Network Interfaces */}
      <div className="moxnas-grid moxnas-grid-cols-1">
        <div className="moxnas-card">
          <div className="moxnas-card-header">
            <h3 className="moxnas-card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FaNetworkWired />
              Network Interfaces
            </h3>
          </div>
          <div className="moxnas-card-body">
            {Array.isArray(systemInfo.network_interfaces) ? systemInfo.network_interfaces.map((interface_, index) => (
              <div key={index} style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                padding: '1rem 0',
                borderBottom: index < systemInfo.network_interfaces.length - 1 ? '1px solid var(--border-light)' : 'none'
              }}>
                <div>
                  <strong>{interface_.name}</strong>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  {Array.isArray(interface_.addresses) ? interface_.addresses.map((addr, addrIndex) => (
                    <span key={addrIndex} className="moxnas-status moxnas-status-info">
                      {addr.ip}/{addr.netmask}
                    </span>
                  )) : (
                    <span className="moxnas-status moxnas-status-info">No addresses</span>
                  )}
                </div>
              </div>
            )) : (
              <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--text-secondary)' }}>
                No network interfaces available
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;