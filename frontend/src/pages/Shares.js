import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Button, Table, Modal, Form, Badge, Nav, Alert } from 'react-bootstrap';
import { FaFolderOpen, FaPlus, FaEdit, FaTrash, FaNetworkWired, FaUpload, FaCloud, FaSync, FaPlay } from 'react-icons/fa';
import { storageAPI, servicesAPI } from '../services/api';

const Shares = () => {
  const [shares, setShares] = useState([]);
  const [cloudTasks, setCloudTasks] = useState([]);
  const [rsyncTasks, setRsyncTasks] = useState([]);
  const [activeTab, setActiveTab] = useState('shares');
  const [showShareModal, setShowShareModal] = useState(false);
  const [showCloudModal, setShowCloudModal] = useState(false);
  const [showRsyncModal, setShowRsyncModal] = useState(false);
  const [editingShare, setEditingShare] = useState(null);
  const [editingCloudTask, setEditingCloudTask] = useState(null);
  const [editingRsyncTask, setEditingRsyncTask] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [sharesResponse, cloudResponse, rsyncResponse] = await Promise.all([
        storageAPI.getShares(),
        servicesAPI.getCloudSyncTasks(),
        servicesAPI.getRsyncTasks()
      ]);
      
      setShares(sharesResponse.data);
      setCloudTasks(cloudResponse.data.results || cloudResponse.data);
      setRsyncTasks(rsyncResponse.data.results || rsyncResponse.data);
      setLoading(false);
    } catch (error) {
      console.error('Error loading data:', error);
      setLoading(false);
    }
  };

  const handleSaveShare = async (formData) => {
    try {
      if (editingShare) {
        await storageAPI.updateShare(editingShare.id, formData);
      } else {
        await storageAPI.createShare(formData);
      }
      
      setShowShareModal(false);
      setEditingShare(null);
      loadData();
    } catch (error) {
      console.error('Error saving share:', error);
      alert('Failed to save share');
    }
  };

  const handleDeleteShare = async (shareId) => {
    if (window.confirm('Are you sure you want to delete this share?')) {
      try {
        await storageAPI.deleteShare(shareId);
        loadData();
      } catch (error) {
        console.error('Error deleting share:', error);
        alert('Failed to delete share');
      }
    }
  };

  // Cloud Sync Functions
  const handleSaveCloudTask = async (formData) => {
    try {
      if (editingCloudTask) {
        await servicesAPI.updateCloudSyncTask(editingCloudTask.id, formData);
      } else {
        await servicesAPI.createCloudSyncTask(formData);
      }
      
      setShowCloudModal(false);
      setEditingCloudTask(null);
      loadData();
    } catch (error) {
      console.error('Error saving cloud task:', error);
      alert('Failed to save cloud sync task');
    }
  };

  const handleDeleteCloudTask = async (taskId) => {
    if (window.confirm('Are you sure you want to delete this cloud sync task?')) {
      try {
        await servicesAPI.deleteCloudSyncTask(taskId);
        loadData();
      } catch (error) {
        console.error('Error deleting cloud task:', error);
        alert('Failed to delete cloud sync task');
      }
    }
  };

  const handleRunCloudTask = async (taskId) => {
    try {
      await servicesAPI.runCloudSyncTask(taskId);
      alert('Cloud sync task started successfully');
      loadData();
    } catch (error) {
      console.error('Error running cloud task:', error);
      alert('Failed to start cloud sync task');
    }
  };

  // Rsync Functions
  const handleSaveRsyncTask = async (formData) => {
    try {
      if (editingRsyncTask) {
        await servicesAPI.updateRsyncTask(editingRsyncTask.id, formData);
      } else {
        await servicesAPI.createRsyncTask(formData);
      }
      
      setShowRsyncModal(false);
      setEditingRsyncTask(null);
      loadData();
    } catch (error) {
      console.error('Error saving rsync task:', error);
      alert('Failed to save rsync task');
    }
  };

  const handleDeleteRsyncTask = async (taskId) => {
    if (window.confirm('Are you sure you want to delete this rsync task?')) {
      try {
        await servicesAPI.deleteRsyncTask(taskId);
        loadData();
      } catch (error) {
        console.error('Error deleting rsync task:', error);
        alert('Failed to delete rsync task');
      }
    }
  };

  const handleRunRsyncTask = async (taskId) => {
    try {
      await servicesAPI.runRsyncTask(taskId);
      alert('Rsync task started successfully');
      loadData();
    } catch (error) {
      console.error('Error running rsync task:', error);
      alert('Failed to start rsync task');
    }
  };

  const ShareModal = () => {
    const [formData, setFormData] = useState({
      name: '',
      path: '/mnt/storage/',
      protocol: 'smb',
      description: '',
      read_only: false,
      guest_ok: false,
      enabled: true
    });

    useEffect(() => {
      if (editingShare) {
        setFormData(editingShare);
      } else {
        setFormData({
          name: '',
          path: '/mnt/storage/',
          protocol: 'smb',
          description: '',
          read_only: false,
          guest_ok: false,
          enabled: true
        });
      }
    }, [editingShare]);

    const handleSubmit = (e) => {
      e.preventDefault();
      handleSaveShare(formData);
    };

    return (
      <Modal show={showShareModal} onHide={() => setShowShareModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>{editingShare ? 'Edit Share' : 'Add New Share'}</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSubmit}>
          <Modal.Body>
            <Form.Group className="mb-3">
              <Form.Label>Share Name</Form.Label>
              <Form.Control
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                required
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Path</Form.Label>
              <Form.Control
                type="text"
                value={formData.path}
                onChange={(e) => setFormData({...formData, path: e.target.value})}
                required
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Protocol</Form.Label>
              <Form.Select
                value={formData.protocol}
                onChange={(e) => setFormData({...formData, protocol: e.target.value})}
                required
              >
                <option value="smb">SMB/CIFS</option>
                <option value="nfs">NFS</option>
                <option value="ftp">FTP</option>
              </Form.Select>
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Description</Form.Label>
              <Form.Control
                as="textarea"
                rows={2}
                value={formData.description}
                onChange={(e) => setFormData({...formData, description: e.target.value})}
              />
            </Form.Group>
            <Form.Check
              className="mb-2"
              type="checkbox"
              label="Read-only access"
              checked={formData.read_only}
              onChange={(e) => setFormData({...formData, read_only: e.target.checked})}
            />
            <Form.Check
              className="mb-2"
              type="checkbox"
              label="Allow guest access"
              checked={formData.guest_ok}
              onChange={(e) => setFormData({...formData, guest_ok: e.target.checked})}
            />
            <Form.Check
              type="checkbox"
              label="Enabled"
              checked={formData.enabled}
              onChange={(e) => setFormData({...formData, enabled: e.target.checked})}
            />
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowShareModal(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit">
              {editingShare ? 'Update' : 'Create'} Share
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    );
  };

  const CloudSyncModal = () => {
    const [formData, setFormData] = useState({
      name: '',
      description: '',
      provider: 'aws_s3',
      local_path: '/mnt/storage/',
      remote_path: '',
      direction: 'push',
      schedule: 'manual',
      enabled: true,
      compression: false,
      encryption: false
    });

    useEffect(() => {
      if (editingCloudTask) {
        setFormData(editingCloudTask);
      } else {
        setFormData({
          name: '',
          description: '',
          provider: 'aws_s3',
          local_path: '/mnt/storage/',
          remote_path: '',
          direction: 'push',
          schedule: 'manual',
          enabled: true,
          compression: false,
          encryption: false
        });
      }
    }, [editingCloudTask]);

    const handleSubmit = (e) => {
      e.preventDefault();
      handleSaveCloudTask(formData);
    };

    return (
      <Modal show={showCloudModal} onHide={() => setShowCloudModal(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>{editingCloudTask ? 'Edit Cloud Sync Task' : 'Add Cloud Sync Task'}</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSubmit}>
          <Modal.Body>
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Task Name *</Form.Label>
                  <Form.Control
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    required
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Provider *</Form.Label>
                  <Form.Select
                    value={formData.provider}
                    onChange={(e) => setFormData({...formData, provider: e.target.value})}
                    required
                  >
                    <option value="aws_s3">Amazon S3</option>
                    <option value="azure_blob">Azure Blob Storage</option>
                    <option value="google_drive">Google Drive</option>
                    <option value="dropbox">Dropbox</option>
                    <option value="backblaze_b2">Backblaze B2</option>
                    <option value="ftp">FTP Server</option>
                    <option value="sftp">SFTP Server</option>
                  </Form.Select>
                </Form.Group>
              </Col>
            </Row>

            <Form.Group className="mb-3">
              <Form.Label>Description</Form.Label>
              <Form.Control
                as="textarea"
                rows={2}
                value={formData.description}
                onChange={(e) => setFormData({...formData, description: e.target.value})}
              />
            </Form.Group>

            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Local Path *</Form.Label>
                  <Form.Control
                    type="text"
                    value={formData.local_path}
                    onChange={(e) => setFormData({...formData, local_path: e.target.value})}
                    required
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Remote Path *</Form.Label>
                  <Form.Control
                    type="text"
                    value={formData.remote_path}
                    onChange={(e) => setFormData({...formData, remote_path: e.target.value})}
                    required
                  />
                </Form.Group>
              </Col>
            </Row>

            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Direction</Form.Label>
                  <Form.Select
                    value={formData.direction}
                    onChange={(e) => setFormData({...formData, direction: e.target.value})}
                  >
                    <option value="push">Push to Cloud</option>
                    <option value="pull">Pull from Cloud</option>
                    <option value="sync">Bidirectional Sync</option>
                  </Form.Select>
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Schedule</Form.Label>
                  <Form.Select
                    value={formData.schedule}
                    onChange={(e) => setFormData({...formData, schedule: e.target.value})}
                  >
                    <option value="manual">Manual Only</option>
                    <option value="hourly">Every Hour</option>
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </Form.Select>
                </Form.Group>
              </Col>
            </Row>

            <Row>
              <Col md={4}>
                <Form.Check
                  type="checkbox"
                  label="Enable Compression"
                  checked={formData.compression}
                  onChange={(e) => setFormData({...formData, compression: e.target.checked})}
                />
              </Col>
              <Col md={4}>
                <Form.Check
                  type="checkbox"
                  label="Enable Encryption"
                  checked={formData.encryption}
                  onChange={(e) => setFormData({...formData, encryption: e.target.checked})}
                />
              </Col>
              <Col md={4}>
                <Form.Check
                  type="checkbox"
                  label="Enabled"
                  checked={formData.enabled}
                  onChange={(e) => setFormData({...formData, enabled: e.target.checked})}
                />
              </Col>
            </Row>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowCloudModal(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit">
              {editingCloudTask ? 'Update' : 'Create'} Task
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    );
  };

  const RsyncModal = () => {
    const [formData, setFormData] = useState({
      name: '',
      description: '',
      source_path: '/mnt/storage/',
      destination_path: '',
      remote_host: '',
      remote_user: '',
      direction: 'push',
      schedule: 'manual',
      enabled: true,
      preserve_permissions: true,
      preserve_timestamps: true,
      compress: false,
      delete_destination: false
    });

    useEffect(() => {
      if (editingRsyncTask) {
        setFormData(editingRsyncTask);
      } else {
        setFormData({
          name: '',
          description: '',
          source_path: '/mnt/storage/',
          destination_path: '',
          remote_host: '',
          remote_user: '',
          direction: 'push',
          schedule: 'manual',
          enabled: true,
          preserve_permissions: true,
          preserve_timestamps: true,
          compress: false,
          delete_destination: false
        });
      }
    }, [editingRsyncTask]);

    const handleSubmit = (e) => {
      e.preventDefault();
      handleSaveRsyncTask(formData);
    };

    return (
      <Modal show={showRsyncModal} onHide={() => setShowRsyncModal(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>{editingRsyncTask ? 'Edit Rsync Task' : 'Add Rsync Task'}</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSubmit}>
          <Modal.Body>
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Task Name *</Form.Label>
                  <Form.Control
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    required
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Direction</Form.Label>
                  <Form.Select
                    value={formData.direction}
                    onChange={(e) => setFormData({...formData, direction: e.target.value})}
                  >
                    <option value="push">Push to Remote</option>
                    <option value="pull">Pull from Remote</option>
                  </Form.Select>
                </Form.Group>
              </Col>
            </Row>

            <Form.Group className="mb-3">
              <Form.Label>Description</Form.Label>
              <Form.Control
                as="textarea"
                rows={2}
                value={formData.description}
                onChange={(e) => setFormData({...formData, description: e.target.value})}
              />
            </Form.Group>

            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Source Path *</Form.Label>
                  <Form.Control
                    type="text"
                    value={formData.source_path}
                    onChange={(e) => setFormData({...formData, source_path: e.target.value})}
                    required
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Destination Path *</Form.Label>
                  <Form.Control
                    type="text"
                    value={formData.destination_path}
                    onChange={(e) => setFormData({...formData, destination_path: e.target.value})}
                    required
                  />
                </Form.Group>
              </Col>
            </Row>

            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Remote Host</Form.Label>
                  <Form.Control
                    type="text"
                    value={formData.remote_host}
                    onChange={(e) => setFormData({...formData, remote_host: e.target.value})}
                    placeholder="example.com"
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Remote User</Form.Label>
                  <Form.Control
                    type="text"
                    value={formData.remote_user}
                    onChange={(e) => setFormData({...formData, remote_user: e.target.value})}
                    placeholder="username"
                  />
                </Form.Group>
              </Col>
            </Row>

            <Form.Group className="mb-3">
              <Form.Label>Schedule</Form.Label>
              <Form.Select
                value={formData.schedule}
                onChange={(e) => setFormData({...formData, schedule: e.target.value})}
              >
                <option value="manual">Manual Only</option>
                <option value="hourly">Every Hour</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </Form.Select>
            </Form.Group>

            <Row>
              <Col md={3}>
                <Form.Check
                  type="checkbox"
                  label="Preserve Permissions"
                  checked={formData.preserve_permissions}
                  onChange={(e) => setFormData({...formData, preserve_permissions: e.target.checked})}
                />
              </Col>
              <Col md={3}>
                <Form.Check
                  type="checkbox"
                  label="Preserve Timestamps"
                  checked={formData.preserve_timestamps}
                  onChange={(e) => setFormData({...formData, preserve_timestamps: e.target.checked})}
                />
              </Col>
              <Col md={3}>
                <Form.Check
                  type="checkbox"
                  label="Compress"
                  checked={formData.compress}
                  onChange={(e) => setFormData({...formData, compress: e.target.checked})}
                />
              </Col>
              <Col md={3}>
                <Form.Check
                  type="checkbox"
                  label="Enabled"
                  checked={formData.enabled}
                  onChange={(e) => setFormData({...formData, enabled: e.target.checked})}
                />
              </Col>
            </Row>

            <Alert variant="warning" className="mt-3">
              <small><strong>Warning:</strong> Delete Destination will remove files from destination that don't exist in source.</small>
            </Alert>
            <Form.Check
              type="checkbox"
              label="Delete files in destination that don't exist in source"
              checked={formData.delete_destination}
              onChange={(e) => setFormData({...formData, delete_destination: e.target.checked})}
            />
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowRsyncModal(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit">
              {editingRsyncTask ? 'Update' : 'Create'} Task
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    );
  };

  if (loading) {
    return (
      <Container>
        <div className="text-center mt-5">
          <div className="spinner-border" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
        </div>
      </Container>
    );
  }

  const renderCloudSyncTasks = () => (
    <Card>
      <Card.Header className="d-flex justify-content-between align-items-center">
        <h5><FaCloud className="me-2" />Cloud Sync Tasks</h5>
        <Button 
          variant="primary"
          onClick={() => {
            setEditingCloudTask(null);
            setShowCloudModal(true);
          }}
        >
          <FaPlus className="me-2" />Add Cloud Sync
        </Button>
      </Card.Header>
      <Card.Body>
        {cloudTasks.length > 0 ? (
          <Table responsive>
            <thead>
              <tr>
                <th>Name</th>
                <th>Provider</th>
                <th>Direction</th>
                <th>Local Path</th>
                <th>Schedule</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {cloudTasks.map((task) => (
                <tr key={task.id}>
                  <td>
                    <strong>{task.name}</strong>
                    {task.description && (
                      <><br /><small className="text-muted">{task.description}</small></>
                    )}
                  </td>
                  <td><Badge bg="info">{task.provider_display}</Badge></td>
                  <td><Badge bg="primary">{task.direction_display}</Badge></td>
                  <td><code>{task.local_path}</code></td>
                  <td><Badge bg="secondary">{task.schedule_display}</Badge></td>
                  <td>
                    <Badge bg={task.enabled ? 'success' : 'secondary'}>
                      {task.enabled ? 'Active' : 'Disabled'}
                    </Badge>
                    {task.last_status && (
                      <><br /><Badge bg={task.last_status === 'success' ? 'success' : 'danger'} className="mt-1">
                        {task.last_status}
                      </Badge></>
                    )}
                  </td>
                  <td>
                    <div className="btn-group btn-group-sm">
                      <Button 
                        variant="outline-success"
                        onClick={() => handleRunCloudTask(task.id)}
                        disabled={!task.enabled}
                      >
                        <FaPlay />
                      </Button>
                      <Button 
                        variant="outline-primary"
                        onClick={() => {
                          setEditingCloudTask(task);
                          setShowCloudModal(true);
                        }}
                      >
                        <FaEdit />
                      </Button>
                      <Button 
                        variant="outline-danger"
                        onClick={() => handleDeleteCloudTask(task.id)}
                      >
                        <FaTrash />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : (
          <div className="text-center text-muted py-5">
            <FaCloud size={48} className="mb-3" />
            <h4>No Cloud Sync Tasks</h4>
            <p>Create cloud sync tasks to backup or synchronize your data with cloud providers</p>
            <Button 
              variant="primary"
              onClick={() => {
                setEditingCloudTask(null);
                setShowCloudModal(true);
              }}
            >
              <FaPlus className="me-2" />Create First Cloud Sync Task
            </Button>
          </div>
        )}
      </Card.Body>
    </Card>
  );

  const renderRsyncTasks = () => (
    <Card>
      <Card.Header className="d-flex justify-content-between align-items-center">
        <h5><FaSync className="me-2" />Rsync Tasks</h5>
        <Button 
          variant="primary"
          onClick={() => {
            setEditingRsyncTask(null);
            setShowRsyncModal(true);
          }}
        >
          <FaPlus className="me-2" />Add Rsync Task
        </Button>
      </Card.Header>
      <Card.Body>
        {rsyncTasks.length > 0 ? (
          <Table responsive>
            <thead>
              <tr>
                <th>Name</th>
                <th>Direction</th>
                <th>Source</th>
                <th>Destination</th>
                <th>Schedule</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rsyncTasks.map((task) => (
                <tr key={task.id}>
                  <td>
                    <strong>{task.name}</strong>
                    {task.description && (
                      <><br /><small className="text-muted">{task.description}</small></>
                    )}
                  </td>
                  <td><Badge bg="primary">{task.direction_display}</Badge></td>
                  <td><code>{task.source_path}</code></td>
                  <td>
                    <code>{task.remote_host ? `${task.remote_user}@${task.remote_host}:` : ''}{task.destination_path}</code>
                  </td>
                  <td><Badge bg="secondary">{task.schedule_display}</Badge></td>
                  <td>
                    <Badge bg={task.enabled ? 'success' : 'secondary'}>
                      {task.enabled ? 'Active' : 'Disabled'}
                    </Badge>
                    {task.last_status && (
                      <><br /><Badge bg={task.last_status === 'success' ? 'success' : 'danger'} className="mt-1">
                        {task.last_status}
                      </Badge></>
                    )}
                  </td>
                  <td>
                    <div className="btn-group btn-group-sm">
                      <Button 
                        variant="outline-success"
                        onClick={() => handleRunRsyncTask(task.id)}
                        disabled={!task.enabled}
                      >
                        <FaPlay />
                      </Button>
                      <Button 
                        variant="outline-primary"
                        onClick={() => {
                          setEditingRsyncTask(task);
                          setShowRsyncModal(true);
                        }}
                      >
                        <FaEdit />
                      </Button>
                      <Button 
                        variant="outline-danger"
                        onClick={() => handleDeleteRsyncTask(task.id)}
                      >
                        <FaTrash />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : (
          <div className="text-center text-muted py-5">
            <FaSync size={48} className="mb-3" />
            <h4>No Rsync Tasks</h4>
            <p>Create rsync tasks to synchronize data with remote servers</p>
            <Button 
              variant="primary"
              onClick={() => {
                setEditingRsyncTask(null);
                setShowRsyncModal(true);
              }}
            >
              <FaPlus className="me-2" />Create First Rsync Task
            </Button>
          </div>
        )}
      </Card.Body>
    </Card>
  );

  const renderShares = () => (
    <>
      {/* Shares Table */}
      <Card className="mb-4">
        <Card.Header className="d-flex justify-content-between align-items-center">
          <h5>Configured Shares</h5>
          <Button 
            variant="primary"
            onClick={() => {
              setEditingShare(null);
              setShowShareModal(true);
            }}
          >
            <FaPlus className="me-2" />Add Share
          </Button>
        </Card.Header>
        <Card.Body>
          {shares.length > 0 ? (
            <Table responsive>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Path</th>
                  <th>Protocol</th>
                  <th>Permissions</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {shares.map((share) => (
                  <tr key={share.id}>
                    <td>
                      <strong>{share.name}</strong>
                      {share.description && (
                        <><br /><small className="text-muted">{share.description}</small></>
                      )}
                    </td>
                    <td><code>{share.path}</code></td>
                    <td>
                      <Badge bg="info">{share.protocol_display}</Badge>
                    </td>
                    <td>
                      <Badge bg={share.read_only ? 'warning' : 'success'}>
                        {share.read_only ? 'Read-Only' : 'Read-Write'}
                      </Badge>
                      {share.guest_ok && (
                        <Badge bg="secondary" className="ms-1">Guest OK</Badge>
                      )}
                    </td>
                    <td>
                      <Badge bg={share.enabled ? 'success' : 'secondary'}>
                        {share.enabled ? 'Active' : 'Disabled'}
                      </Badge>
                    </td>
                    <td>
                      <div className="btn-group btn-group-sm">
                        <Button 
                          variant="outline-primary"
                          onClick={() => {
                            setEditingShare(share);
                            setShowShareModal(true);
                          }}
                        >
                          <FaEdit />
                        </Button>
                        <Button 
                          variant="outline-danger"
                          onClick={() => handleDeleteShare(share.id)}
                        >
                          <FaTrash />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          ) : (
            <div className="text-center text-muted py-5">
              <FaFolderOpen size={48} className="mb-3" />
              <h4>No Shares Configured</h4>
              <p>Create your first share to start serving files over the network</p>
              <Button 
                variant="primary"
                onClick={() => {
                  setEditingShare(null);
                  setShowShareModal(true);
                }}
              >
                <FaPlus className="me-2" />Create First Share
              </Button>
            </div>
          )}
        </Card.Body>
      </Card>

      {/* Protocol Information */}
      <Row>
        <Col md={4}>
          <Card className="text-center">
            <Card.Body>
              <FaFolderOpen size={32} className="text-primary mb-3" />
              <h5>SMB/CIFS</h5>
              <p className="text-muted">Windows file sharing protocol</p>
              <small className="text-muted">Port 445</small>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          <Card className="text-center">
            <Card.Body>
              <FaNetworkWired size={32} className="text-success mb-3" />
              <h5>NFS</h5>
              <p className="text-muted">Network File System for Unix/Linux</p>
              <small className="text-muted">Port 2049</small>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          <Card className="text-center">
            <Card.Body>
              <FaUpload size={32} className="text-info mb-3" />
              <h5>FTP</h5>
              <p className="text-muted">File Transfer Protocol</p>
              <small className="text-muted">Port 21</small>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </>
  );

  return (
    <Container fluid>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h1><FaFolderOpen className="me-2" />Shares & Sync</h1>
      </div>

      <Nav variant="tabs" className="mb-4">
        <Nav.Item>
          <Nav.Link 
            active={activeTab === 'shares'} 
            onClick={() => setActiveTab('shares')}
          >
            <FaFolderOpen className="me-2" />Network Shares
          </Nav.Link>
        </Nav.Item>
        <Nav.Item>
          <Nav.Link 
            active={activeTab === 'cloud'} 
            onClick={() => setActiveTab('cloud')}
          >
            <FaCloud className="me-2" />Cloud Sync
          </Nav.Link>
        </Nav.Item>
        <Nav.Item>
          <Nav.Link 
            active={activeTab === 'rsync'} 
            onClick={() => setActiveTab('rsync')}
          >
            <FaSync className="me-2" />Rsync Tasks
          </Nav.Link>
        </Nav.Item>
      </Nav>

      {activeTab === 'shares' && renderShares()}
      {activeTab === 'cloud' && renderCloudSyncTasks()}
      {activeTab === 'rsync' && renderRsyncTasks()}

      <ShareModal />
      <CloudSyncModal />
      <RsyncModal />
    </Container>
  );
};

export default Shares;