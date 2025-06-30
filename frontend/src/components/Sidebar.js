import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  FaTachometerAlt, 
  FaHdd, 
  FaFolderOpen, 
  FaNetworkWired, 
  FaUsers, 
  FaCog, 
  FaChartLine,
  FaServer,
  FaCube,
  FaBars
} from 'react-icons/fa';

const Sidebar = ({ collapsed, onToggle }) => {
  const location = useLocation();

  const menuItems = [
    { 
      section: 'Dashboard',
      items: [
        { path: '/', label: 'Dashboard', icon: <FaTachometerAlt /> },
      ]
    },
    { 
      section: 'Storage',
      items: [
        { path: '/storage', label: 'Storage', icon: <FaHdd /> },
        { path: '/shares', label: 'Shares', icon: <FaFolderOpen /> },
      ]
    },
    { 
      section: 'Network',
      items: [
        { path: '/network', label: 'Network', icon: <FaNetworkWired /> },
      ]
    },
    { 
      section: 'Accounts',
      items: [
        { path: '/credentials', label: 'Credentials', icon: <FaUsers /> },
      ]
    },
    { 
      section: 'Virtualization',
      items: [
        { path: '/proxmox', label: 'Proxmox', icon: <FaCube /> },
      ]
    },
    { 
      section: 'System',
      items: [
        { path: '/reporting', label: 'Reporting', icon: <FaChartLine /> },
        { path: '/system', label: 'System', icon: <FaCog /> },
      ]
    },
  ];

  return (
    <div className={`moxnas-sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="moxnas-sidebar-header" style={{ padding: '1rem', borderBottom: '1px solid #334155' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          {!collapsed && (
            <div style={{ display: 'flex', alignItems: 'center', color: '#fff' }}>
              <FaServer style={{ marginRight: '0.5rem', fontSize: '1.5rem' }} />
              <span style={{ fontSize: '1.25rem', fontWeight: '600' }}>MoxNAS</span>
            </div>
          )}
          <button 
            onClick={onToggle}
            style={{ 
              background: 'none', 
              border: 'none', 
              color: '#cbd5e1', 
              cursor: 'pointer',
              fontSize: '1.2rem'
            }}
          >
            <FaBars />
          </button>
        </div>
      </div>
      
      <nav className="moxnas-nav">
        {menuItems.map((section, sectionIndex) => (
          <div key={sectionIndex} className="moxnas-nav-section">
            {!collapsed && (
              <div className="moxnas-nav-section-title">
                {section.section}
              </div>
            )}
            {section.items.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`moxnas-nav-item ${location.pathname === item.path ? 'active' : ''}`}
                title={collapsed ? item.label : ''}
              >
                <span className="moxnas-nav-icon">{item.icon}</span>
                {!collapsed && <span>{item.label}</span>}
              </Link>
            ))}
          </div>
        ))}
      </nav>
    </div>
  );
};

export default Sidebar;