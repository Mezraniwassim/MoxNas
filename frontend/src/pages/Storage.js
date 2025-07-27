import React, { useState, useEffect } from 'react';
import { FaHdd, FaPlus, FaEdit, FaTrash, FaDatabase } from 'react-icons/fa';
import { storageAPI } from '../services/api';

const Storage = () => {
  const [datasets, setDatasets] = useState([]);
  const [mountPoints, setMountPoints] = useState([]);
  const [showDatasetModal, setShowDatasetModal] = useState(false);
  const [editingDataset, setEditingDataset] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [datasetsResponse, mountsResponse] = await Promise.all([
        storageAPI.getDatasets(),
        storageAPI.getMountPoints()
      ]);
      
      setDatasets(datasetsResponse.data?.results || datasetsResponse.data || []);
      setMountPoints(mountsResponse.data?.results || mountsResponse.data || []);
      setLoading(false);
    } catch (error) {
      console.error('Error loading storage data:', error);
      setLoading(false);
    }
  };

  const handleSaveDataset = async (formData) => {
    try {
      if (editingDataset) {
        await storageAPI.updateDataset(editingDataset.id, formData);
      } else {
        await storageAPI.createDataset(formData);
      }
      
      setShowDatasetModal(false);
      setEditingDataset(null);
      loadData();
    } catch (error) {
      console.error('Error saving dataset:', error);
      alert('Failed to save dataset');
    }
  };

  const handleDeleteDataset = async (datasetId) => {
    if (window.confirm('Are you sure you want to delete this dataset?')) {
      try {
        await storageAPI.deleteDataset(datasetId);
        loadData();
      } catch (error) {
        console.error('Error deleting dataset:', error);
        alert('Failed to delete dataset');
      }
    }
  };

  const formatBytes = (bytes) => {
    if (!bytes) return 'N/A';
    const gb = bytes / (1024 ** 3);
    return `${gb.toFixed(1)} GB`;
  };

  const DatasetModal = () => {
    const [formData, setFormData] = useState({
      name: '',
      path: '/mnt/storage/',
      description: '',
      compression: false
    });

    useEffect(() => {
      if (editingDataset) {
        setFormData(editingDataset);
      } else {
        setFormData({
          name: '',
          path: '/mnt/storage/',
          description: '',
          compression: false
        });
      }
    }, []);

    const handleSubmit = (e) => {
      e.preventDefault();
      handleSaveDataset(formData);
    };

    if (!showDatasetModal) return null;

    return (
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000
      }}>
        <div className="moxnas-card" style={{ width: '500px', maxWidth: '90vw' }}>
          <div className="moxnas-card-header">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 className="moxnas-card-title">{editingDataset ? 'Edit Dataset' : 'Add New Dataset'}</h3>
              <button
                onClick={() => setShowDatasetModal(false)}
                style={{ background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer' }}
              >
                ×
              </button>
            </div>
          </div>
          <div className="moxnas-card-body">
            <form onSubmit={handleSubmit}>
              <div className="moxnas-form-group">
                <label className="moxnas-label">Dataset Name</label>
                <input
                  className="moxnas-input"
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  required
                />
              </div>
              <div className="moxnas-form-group">
                <label className="moxnas-label">Path</label>
                <input
                  className="moxnas-input"
                  type="text"
                  value={formData.path}
                  onChange={(e) => setFormData({...formData, path: e.target.value})}
                  required
                />
              </div>
              <div className="moxnas-form-group">
                <label className="moxnas-label">Description</label>
                <textarea
                  className="moxnas-input"
                  rows={2}
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                />
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                <input
                  type="checkbox"
                  id="compression"
                  checked={formData.compression}
                  onChange={(e) => setFormData({...formData, compression: e.target.checked})}
                />
                <label htmlFor="compression">Enable compression (if supported)</label>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                <button 
                  type="button"
                  className="moxnas-btn moxnas-btn-secondary" 
                  onClick={() => setShowDatasetModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="moxnas-btn moxnas-btn-primary">
                  {editingDataset ? 'Update' : 'Create'} Dataset
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
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
          <FaHdd />
          Storage
        </h1>
        <button 
          className="moxnas-btn moxnas-btn-primary"
          onClick={() => {
            setEditingDataset(null);
            setShowDatasetModal(true);
          }}
        >
          <FaPlus style={{ marginRight: '0.5rem' }} />
          Add Dataset
        </button>
      </div>

      {/* Storage Overview */}
      <div className="moxnas-grid moxnas-grid-cols-2" style={{ marginBottom: '2rem' }}>
        {mountPoints.map((mount, index) => (
          <div key={index} className="moxnas-card">
            <div className="moxnas-card-header">
              <h3 className="moxnas-card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FaHdd />
                {mount.path}
              </h3>
            </div>
            <div className="moxnas-card-body">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--primary-blue)' }}>
                    {formatBytes(mount.usage_info?.total)}
                  </div>
                  <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Total</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--success)' }}>
                    {formatBytes(mount.usage_info?.free)}
                  </div>
                  <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Available</div>
                </div>
              </div>
              {mount.usage_info && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                    <span style={{ fontSize: '0.875rem' }}>Usage</span>
                    <span style={{ fontSize: '0.875rem', fontWeight: '500' }}>
                      {mount.usage_info.percent.toFixed(1)}%
                    </span>
                  </div>
                  <div className="moxnas-progress">
                    <div 
                      className={`moxnas-progress-bar ${mount.usage_info.percent > 90 ? 'danger' : mount.usage_info.percent > 75 ? 'warning' : 'success'}`}
                      style={{ width: `${mount.usage_info.percent}%` }}
                    ></div>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Datasets */}
      <div className="moxnas-card">
        <div className="moxnas-card-header">
          <h3 className="moxnas-card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FaDatabase />
            Datasets
          </h3>
        </div>
        <div className="moxnas-card-body">
          {datasets.length > 0 ? (
            <table className="moxnas-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Path</th>
                  <th>Size</th>
                  <th>Used</th>
                  <th>Available</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {datasets.map((dataset) => (
                  <tr key={dataset.id}>
                    <td>
                      <div>
                        <strong>{dataset.name}</strong>
                        {dataset.description && (
                          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                            {dataset.description}
                          </div>
                        )}
                      </div>
                    </td>
                    <td>
                      <code style={{ 
                        backgroundColor: 'var(--bg-tertiary)', 
                        padding: '0.25rem 0.5rem', 
                        borderRadius: '0.25rem',
                        fontSize: '0.875rem'
                      }}>
                        {dataset.path}
                      </code>
                    </td>
                    <td>{formatBytes(dataset.size_info?.total)}</td>
                    <td>{formatBytes(dataset.size_info?.used)}</td>
                    <td>{formatBytes(dataset.size_info?.free)}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.25rem' }}>
                        <button 
                          className="moxnas-btn moxnas-btn-secondary"
                          onClick={() => {
                            setEditingDataset(dataset);
                            setShowDatasetModal(true);
                          }}
                          style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                        >
                          <FaEdit />
                        </button>
                        <button 
                          className="moxnas-btn moxnas-btn-danger"
                          onClick={() => handleDeleteDataset(dataset.id)}
                          style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                        >
                          <FaTrash />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div style={{ 
              textAlign: 'center', 
              padding: '3rem 0', 
              color: 'var(--text-secondary)' 
            }}>
              <FaDatabase size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
              <h4>No Datasets Configured</h4>
              <p style={{ marginBottom: '1.5rem' }}>Datasets help organize your storage into logical units</p>
              <button 
                className="moxnas-btn moxnas-btn-primary"
                onClick={() => {
                  setEditingDataset(null);
                  setShowDatasetModal(true);
                }}
              >
                <FaPlus style={{ marginRight: '0.5rem' }} />
                Create First Dataset
              </button>
            </div>
          )}
        </div>
      </div>

      <DatasetModal />
    </div>
  );
};

export default Storage;