import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Button, Table, Modal, Form, Nav, Badge, Alert } from 'react-bootstrap';
import { FaServer, FaPlus, FaEdit, FaTrash, FaPlay, FaStop, FaSync, FaCube } from 'react-icons/fa';
import { proxmoxAPI } from '../services/api';

const Proxmox = () => {
  const [nodes, setNodes] = useState([]);
  const [containers, setContainers] = useState([]);
  const [activeTab, setActiveTab] = useState('containers');
  const [loading, setLoading] = useState(true);
  const [showNodeModal, setShowNodeModal] = useState(false);
  const [showContainerModal, setShowContainerModal] = useState(false);
  const [editingNode, setEditingNode] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [nodesResponse, containersResponse] = await Promise.all([
        proxmoxAPI.getNodes(),
        proxmoxAPI.getContainers()
      ]);
      
      setNodes(nodesResponse.data.results || nodesResponse.data);
      setContainers(containersResponse.data.results || containersResponse.data);
      setLoading(false);
    } catch (error) {
      console.error('Error loading data:', error);
      setNodes([]);
      setContainers([]);
      setLoading(false);
    }
  };

  const handleSaveNode = async (formData) => {
    try {
      if (editingNode) {
        await proxmoxAPI.updateNode(editingNode.id, formData);
      } else {
        await proxmoxAPI.createNode(formData);
      }
      
      setShowNodeModal(false);
      setEditingNode(null);
      loadData();
    } catch (error) {
      console.error('Error saving node:', error);
      alert('Failed to save node');
    }
  };

  const handleTestConnection = async (nodeId) => {
    try {
      const response = await proxmoxAPI.testConnection(nodeId);
      if (response.data.success) {
        alert(`Connection successful! Found ${response.data.nodes} nodes.`);
      } else {
        alert(`Connection failed: ${response.data.message}`);
      }
    } catch (error) {
      alert('Connection test failed');
    }
  };

  const handleCreateContainer = async (formData) => {
    try {
      const response = await proxmoxAPI.createMoxNASContainer(formData);
      if (response.data.success) {
        alert(`Container ${formData.vmid} created successfully!`);
        setShowContainerModal(false);
        loadData();
      } else {
        alert(`Failed to create container: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error creating container:', error);
      alert('Failed to create container');
    }
  };

  const handleContainerAction = async (containerId, action) => {
    try {
      let response;
      if (action === 'start') {
        response = await proxmoxAPI.startContainer(containerId);
      } else if (action === 'stop') {
        response = await proxmoxAPI.stopContainer(containerId);
      }
      
      if (response.data.success) {
        alert(response.data.message);
        loadData();
      } else {
        alert(`Action failed: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Container action error:', error);
      alert('Action failed');
    }
  };

  const NodeModal = () => {
    const [formData, setFormData] = useState({
      name: '',
      host: '',
      port: 8006,
      username: 'root',
      password: '',
      realm: 'pam',
      ssl_verify: false,
      enabled: true
    });

    useEffect(() => {
      if (editingNode) {
        setFormData({...editingNode, password: ''});
      }
    }, [editingNode]);

    const handleSubmit = (e) => {
      e.preventDefault();
      handleSaveNode(formData);
    };

    return (
      <Modal show={showNodeModal} onHide={() => setShowNodeModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>{editingNode ? 'Edit Proxmox Node' : 'Add Proxmox Node'}</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSubmit}>
          <Modal.Body>
            <Form.Group className="mb-3">
              <Form.Label>Name *</Form.Label>
              <Form.Control
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                required
              />
            </Form.Group>
            
            <Row>
              <Col md={8}>
                <Form.Group className="mb-3">
                  <Form.Label>Host/IP *</Form.Label>
                  <Form.Control
                    type="text"
                    value={formData.host}
                    onChange={(e) => setFormData({...formData, host: e.target.value})}
                    required
                  />
                </Form.Group>
              </Col>
              <Col md={4}>
                <Form.Group className="mb-3">
                  <Form.Label>Port</Form.Label>
                  <Form.Control
                    type="number"
                    value={formData.port}
                    onChange={(e) => setFormData({...formData, port: parseInt(e.target.value)})}
                  />
                </Form.Group>
              </Col>
            </Row>

            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Username</Form.Label>
                  <Form.Control
                    type="text"
                    value={formData.username}
                    onChange={(e) => setFormData({...formData, username: e.target.value})}
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Realm</Form.Label>
                  <Form.Select
                    value={formData.realm}
                    onChange={(e) => setFormData({...formData, realm: e.target.value})}
                  >
                    <option value="pam">PAM</option>
                    <option value="pve">PVE</option>
                  </Form.Select>
                </Form.Group>
              </Col>
            </Row>

            <Form.Group className="mb-3">
              <Form.Label>Password {editingNode ? '(leave blank to keep current)' : '*'}</Form.Label>
              <Form.Control
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({...formData, password: e.target.value})}
                required={!editingNode}
              />
            </Form.Group>

            <Form.Check
              className="mb-2"
              type="checkbox"
              label="Verify SSL Certificate"
              checked={formData.ssl_verify}
              onChange={(e) => setFormData({...formData, ssl_verify: e.target.checked})}
            />

            <Form.Check
              type="checkbox"
              label="Enabled"
              checked={formData.enabled}
              onChange={(e) => setFormData({...formData, enabled: e.target.checked})}
            />
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowNodeModal(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit">
              {editingNode ? 'Update' : 'Add'} Node
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    );
  };

  const ContainerModal = () => {
    const [formData, setFormData] = useState({
      vmid: '',
      hostname: '',
      node_id: '',
      memory: 2048,
      cores: 2,
      disk_size: 8,
      template: 'ubuntu-22.04-standard'
    });

    const handleSubmit = (e) => {
      e.preventDefault();
      handleCreateContainer(formData);
    };

    return (
      <Modal show={showContainerModal} onHide={() => setShowContainerModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>Create MoxNAS Container</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSubmit}>
          <Modal.Body>
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Container ID *</Form.Label>
                  <Form.Control
                    type="number"
                    value={formData.vmid}
                    onChange={(e) => setFormData({...formData, vmid: e.target.value})}
                    required
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Hostname</Form.Label>
                  <Form.Control
                    type="text"
                    value={formData.hostname}
                    onChange={(e) => setFormData({...formData, hostname: e.target.value})}
                    placeholder={`moxnas-${formData.vmid}`}
                  />
                </Form.Group>
              </Col>
            </Row>

            <Form.Group className="mb-3">
              <Form.Label>Proxmox Node *</Form.Label>
              <Form.Select
                value={formData.node_id}
                onChange={(e) => setFormData({...formData, node_id: e.target.value})}
                required
              >
                <option value="">Select a node...</option>
                {nodes.filter(node => node.enabled).map(node => (
                  <option key={node.id} value={node.id}>
                    {node.name} ({node.host})
                  </option>
                ))}
              </Form.Select>
            </Form.Group>

            <Row>
              <Col md={4}>
                <Form.Group className="mb-3">
                  <Form.Label>Memory (MB)</Form.Label>
                  <Form.Control
                    type="number"
                    value={formData.memory}
                    onChange={(e) => setFormData({...formData, memory: parseInt(e.target.value)})}
                  />
                </Form.Group>
              </Col>
              <Col md={4}>
                <Form.Group className="mb-3">
                  <Form.Label>CPU Cores</Form.Label>
                  <Form.Control
                    type="number"
                    value={formData.cores}
                    onChange={(e) => setFormData({...formData, cores: parseInt(e.target.value)})}
                  />
                </Form.Group>
              </Col>
              <Col md={4}>
                <Form.Group className="mb-3">
                  <Form.Label>Disk (GB)</Form.Label>
                  <Form.Control
                    type="number"
                    value={formData.disk_size}
                    onChange={(e) => setFormData({...formData, disk_size: parseInt(e.target.value)})}
                  />
                </Form.Group>
              </Col>
            </Row>

            <Form.Group className="mb-3">
              <Form.Label>Template</Form.Label>
              <Form.Control
                type="text"
                value={formData.template}
                onChange={(e) => setFormData({...formData, template: e.target.value})}
              />
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowContainerModal(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit">
              Create Container
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

  return (
    <Container fluid>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h1><FaServer className="me-2" />Proxmox Management</h1>
      </div>

      <Nav variant="tabs" className="mb-4">
        <Nav.Item>
          <Nav.Link 
            active={activeTab === 'containers'} 
            onClick={() => setActiveTab('containers')}
          >
            <FaCube className="me-2" />Containers
          </Nav.Link>
        </Nav.Item>
        <Nav.Item>
          <Nav.Link 
            active={activeTab === 'nodes'} 
            onClick={() => setActiveTab('nodes')}
          >
            <FaServer className="me-2" />Nodes
          </Nav.Link>
        </Nav.Item>
      </Nav>

      {activeTab === 'containers' && (
        <Card>
          <Card.Header className="d-flex justify-content-between align-items-center">
            <h5>LXC Containers</h5>
            <div>
              <Button 
                variant="outline-secondary" 
                size="sm" 
                className="me-2"
                onClick={() => proxmoxAPI.syncContainers().then(() => loadData())}
              >
                <FaSync className="me-1" />Sync
              </Button>
              <Button 
                variant="primary"
                onClick={() => setShowContainerModal(true)}
                disabled={nodes.filter(n => n.enabled).length === 0}
              >
                <FaPlus className="me-2" />Create Container
              </Button>
            </div>
          </Card.Header>
          <Card.Body>
            {nodes.filter(n => n.enabled).length === 0 && (
              <Alert variant="warning">
                <strong>No Proxmox nodes configured!</strong> Add a Proxmox node first to manage containers.
              </Alert>
            )}
            
            {containers.length > 0 ? (
              <Table responsive>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Node</th>
                    <th>Status</th>
                    <th>Resources</th>
                    <th>IP Address</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {containers.map((container) => (
                    <tr key={container.id}>
                      <td><strong>{container.vmid}</strong></td>
                      <td>{container.name}</td>
                      <td>{container.node_name}</td>
                      <td>
                        <Badge bg={container.status === 'running' ? 'success' : 'secondary'}>
                          {container.status}
                        </Badge>
                      </td>
                      <td>
                        {container.memory} MB / {container.cores} cores / {container.disk_size} GB
                      </td>
                      <td>{container.ip_address || '-'}</td>
                      <td>
                        <div className="btn-group btn-group-sm">
                          <Button 
                            variant="outline-success"
                            onClick={() => handleContainerAction(container.id, 'start')}
                            disabled={container.status === 'running'}
                          >
                            <FaPlay />
                          </Button>
                          <Button 
                            variant="outline-danger"
                            onClick={() => handleContainerAction(container.id, 'stop')}
                            disabled={container.status !== 'running'}
                          >
                            <FaStop />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            ) : (
              <div className="text-center text-muted py-5">
                <FaCube size={48} className="mb-3" />
                <h4>No Containers Found</h4>
                <p>Create your first MoxNAS container to get started</p>
              </div>
            )}
          </Card.Body>
        </Card>
      )}

      {activeTab === 'nodes' && (
        <Card>
          <Card.Header className="d-flex justify-content-between align-items-center">
            <h5>Proxmox Nodes</h5>
            <Button 
              variant="primary"
              onClick={() => {
                setEditingNode(null);
                setShowNodeModal(true);
              }}
            >
              <FaPlus className="me-2" />Add Node
            </Button>
          </Card.Header>
          <Card.Body>
            {nodes.length > 0 ? (
              <Table responsive>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Host</th>
                    <th>Port</th>
                    <th>Username</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {nodes.map((node) => (
                    <tr key={node.id}>
                      <td><strong>{node.name}</strong></td>
                      <td>{node.host}</td>
                      <td>{node.port}</td>
                      <td>{node.username}@{node.realm}</td>
                      <td>
                        <Badge bg={node.enabled ? 'success' : 'secondary'}>
                          {node.enabled ? 'Enabled' : 'Disabled'}
                        </Badge>
                      </td>
                      <td>
                        <div className="btn-group btn-group-sm">
                          <Button 
                            variant="outline-info"
                            onClick={() => handleTestConnection(node.id)}
                          >
                            Test
                          </Button>
                          <Button 
                            variant="outline-primary"
                            onClick={() => {
                              setEditingNode(node);
                              setShowNodeModal(true);
                            }}
                          >
                            <FaEdit />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            ) : (
              <div className="text-center text-muted py-5">
                <FaServer size={48} className="mb-3" />
                <h4>No Proxmox Nodes Configured</h4>
                <p>Add your Proxmox host to manage LXC containers</p>
                <Button 
                  variant="primary"
                  onClick={() => {
                    setEditingNode(null);
                    setShowNodeModal(true);
                  }}
                >
                  <FaPlus className="me-2" />Add First Node
                </Button>
              </div>
            )}
          </Card.Body>
        </Card>
      )}

      <NodeModal />
      <ContainerModal />
    </Container>
  );
};

export default Proxmox;