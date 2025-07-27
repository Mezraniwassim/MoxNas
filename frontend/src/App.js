import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './styles/moxnas-theme.css';

// Import components with error boundaries
const Sidebar = React.lazy(() => import('./components/Sidebar'));
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const Storage = React.lazy(() => import('./pages/Storage'));
const Shares = React.lazy(() => import('./pages/Shares'));
const Network = React.lazy(() => import('./pages/Network'));
const Credentials = React.lazy(() => import('./pages/Credentials'));
const Proxmox = React.lazy(() => import('./pages/Proxmox'));
const System = React.lazy(() => import('./pages/System'));
const Reporting = React.lazy(() => import('./pages/Reporting'));

function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <Router>
      <div className="moxnas-layout">
        <React.Suspense fallback={<div>Loading sidebar...</div>}>
          <Sidebar 
            collapsed={sidebarCollapsed} 
            onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} 
          />
        </React.Suspense>
        <div className={`moxnas-main ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
          <div className="moxnas-topnav">
            <h1 className="moxnas-topnav-title">MoxNAS</h1>
            <div className="moxnas-topnav-actions">
              <div className="moxnas-status moxnas-status-success">
                System Online
              </div>
            </div>
          </div>
          <div className="moxnas-content">
            <React.Suspense fallback={<div>Loading page...</div>}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/storage" element={<Storage />} />
                <Route path="/shares" element={<Shares />} />
                <Route path="/network" element={<Network />} />
                <Route path="/credentials" element={<Credentials />} />
                <Route path="/proxmox" element={<Proxmox />} />
                <Route path="/system" element={<System />} />
                <Route path="/reporting" element={<Reporting />} />
              </Routes>
            </React.Suspense>
          </div>
        </div>
      </div>
    </Router>
  );
}

export default App;