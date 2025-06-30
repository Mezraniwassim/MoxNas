import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Button, Table, Modal, Form, Nav, Badge, Alert } from 'react-bootstrap';
import { FaUsers, FaUserPlus, FaEdit, FaTrash, FaLock, FaShieldAlt } from 'react-icons/fa';
import { usersAPI } from '../services/api';

const Credentials = () => {
  const [users, setUsers] = useState([]);
  const [groups, setGroups] = useState([]);
  const [acls, setACLs] = useState([]);
  const [activeTab, setActiveTab] = useState('users');
  const [loading, setLoading] = useState(true);
  const [showUserModal, setShowUserModal] = useState(false);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [showACLModal, setShowACLModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [editingGroup, setEditingGroup] = useState(null);
  const [editingACL, setEditingACL] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [usersResponse, groupsResponse, aclResponse] = await Promise.all([
        usersAPI.getUsers(),
        usersAPI.getGroups(),
        usersAPI.getACLs()
      ]);
      
      setUsers(usersResponse.data.results || usersResponse.data);
      setGroups(groupsResponse.data.results || groupsResponse.data);
      setACLs(aclResponse.data.results || aclResponse.data);
      setLoading(false);
    } catch (error) {
      console.error('Error loading data:', error);
      setUsers([]);
      setGroups([]);
      setACLs([]);
      setLoading(false);
    }
  };

  const handleSaveUser = async (formData) => {
    try {
      if (editingUser) {
        await usersAPI.updateUser(editingUser.id, formData);
      } else {
        await usersAPI.createUser(formData);
      }
      
      setShowUserModal(false);
      setEditingUser(null);
      loadData();
    } catch (error) {
      console.error('Error saving user:', error);
      alert('Failed to save user');
    }
  };

  const handleDeleteUser = async (userId) => {
    if (window.confirm('Are you sure you want to delete this user?')) {
      try {
        await usersAPI.deleteUser(userId);
        loadData();
      } catch (error) {
        console.error('Error deleting user:', error);
        alert('Failed to delete user');
      }
    }
  };

  const handleSaveGroup = async (formData) => {
    try {
      if (editingGroup) {
        await usersAPI.updateGroup(editingGroup.id, formData);
      } else {
        await usersAPI.createGroup(formData);
      }
      
      setShowGroupModal(false);
      setEditingGroup(null);
      loadData();
    } catch (error) {
      console.error('Error saving group:', error);
      alert('Failed to save group');
    }
  };

  const UserModal = () => {
    const [formData, setFormData] = useState({
      username: '',
      email: '',
      first_name: '',
      last_name: '',
      full_name: '',
      password: '',
      home_directory: '/mnt/storage/users/',
      shell: '/bin/bash',
      samba_enabled: true,
      nfs_enabled: true,
      ftp_enabled: true,
      ssh_enabled: false,
      is_active: true
    });

    useEffect(() => {
      if (editingUser) {
        setFormData({...editingUser, password: ''});
      }
    }, [editingUser]);

    const handleSubmit = (e) => {
      e.preventDefault();
      const submitData = {...formData};
      if (!submitData.password && editingUser) {
        delete submitData.password;
      }
      handleSaveUser(submitData);
    };

    return (
      <Modal show={showUserModal} onHide={() => setShowUserModal(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>{editingUser ? 'Edit User' : 'Add New User'}</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSubmit}>
          <Modal.Body>
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Username *</Form.Label>
                  <Form.Control
                    type="text"
                    value={formData.username}
                    onChange={(e) => setFormData({...formData, username: e.target.value})}
                    required
                    disabled={editingUser}
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Email</Form.Label>
                  <Form.Control
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                  />
                </Form.Group>
              </Col>
            </Row>
            
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>First Name</Form.Label>
                  <Form.Control
                    type="text"
                    value={formData.first_name}
                    onChange={(e) => setFormData({...formData, first_name: e.target.value})}
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Last Name</Form.Label>
                  <Form.Control
                    type="text"
                    value={formData.last_name}
                    onChange={(e) => setFormData({...formData, last_name: e.target.value})}
                  />
                </Form.Group>
              </Col>
            </Row>

            <Form.Group className="mb-3">
              <Form.Label>Password {editingUser ? '(leave blank to keep current)' : '*'}</Form.Label>
              <Form.Control
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({...formData, password: e.target.value})}
                required={!editingUser}
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Home Directory</Form.Label>
              <Form.Control
                type="text"
                value={formData.home_directory}
                onChange={(e) => setFormData({...formData, home_directory: e.target.value})}
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Shell</Form.Label>
              <Form.Select
                value={formData.shell}
                onChange={(e) => setFormData({...formData, shell: e.target.value})}
              >
                <option value="/bin/bash">Bash</option>
                <option value="/bin/sh">Shell</option>
                <option value="/usr/sbin/nologin">No Login</option>
              </Form.Select>
            </Form.Group>

            <h6>Service Access</h6>
            <Row>
              <Col md={3}>
                <Form.Check
                  type="checkbox"
                  label="SMB/CIFS"
                  checked={formData.samba_enabled}
                  onChange={(e) => setFormData({...formData, samba_enabled: e.target.checked})}
                />
              </Col>
              <Col md={3}>
                <Form.Check
                  type="checkbox"
                  label="NFS"
                  checked={formData.nfs_enabled}
                  onChange={(e) => setFormData({...formData, nfs_enabled: e.target.checked})}
                />
              </Col>
              <Col md={3}>
                <Form.Check
                  type="checkbox"
                  label="FTP"
                  checked={formData.ftp_enabled}
                  onChange={(e) => setFormData({...formData, ftp_enabled: e.target.checked})}
                />
              </Col>
              <Col md={3}>
                <Form.Check
                  type="checkbox"
                  label="SSH"
                  checked={formData.ssh_enabled}
                  onChange={(e) => setFormData({...formData, ssh_enabled: e.target.checked})}
                />
              </Col>
            </Row>

            <Form.Check
              className="mt-3"
              type="checkbox"
              label="Account Active"
              checked={formData.is_active}
              onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
            />
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowUserModal(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit">
              {editingUser ? 'Update' : 'Create'} User
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    );
  };

  const renderUsers = () => (
    <Card>
      <Card.Header className="d-flex justify-content-between align-items-center">
        <h5>Users</h5>
        <Button 
          variant="primary"
          onClick={() => {
            setEditingUser(null);
            setShowUserModal(true);
          }}
        >
          <FaUserPlus className="me-2" />Add User
        </Button>
      </Card.Header>
      <Card.Body>
        {users.length > 0 ? (
          <Table responsive>
            <thead>
              <tr>
                <th>Username</th>
                <th>Name</th>
                <th>Email</th>
                <th>Home Directory</th>
                <th>Services</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td><strong>{user.username}</strong></td>
                  <td>{user.full_name || `${user.first_name} ${user.last_name}`.trim() || '-'}</td>
                  <td>{user.email || '-'}</td>
                  <td><code>{user.home_directory}</code></td>
                  <td>
                    {user.samba_enabled && <Badge bg="info" className="me-1">SMB</Badge>}
                    {user.nfs_enabled && <Badge bg="success" className="me-1">NFS</Badge>}
                    {user.ftp_enabled && <Badge bg="warning" className="me-1">FTP</Badge>}
                    {user.ssh_enabled && <Badge bg="secondary" className="me-1">SSH</Badge>}
                  </td>
                  <td>
                    <Badge bg={user.is_active ? 'success' : 'secondary'}>
                      {user.is_active ? 'Active' : 'Disabled'}
                    </Badge>
                  </td>
                  <td>
                    <div className="btn-group btn-group-sm">
                      <Button 
                        variant="outline-primary"
                        onClick={() => {
                          setEditingUser(user);
                          setShowUserModal(true);
                        }}
                      >
                        <FaEdit />
                      </Button>
                      <Button 
                        variant="outline-danger"
                        onClick={() => handleDeleteUser(user.id)}
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
            <FaUsers size={48} className="mb-3" />
            <h4>No Users Created</h4>
            <p>Create your first user account to access MoxNAS services</p>
            <Button 
              variant="primary"
              onClick={() => {
                setEditingUser(null);
                setShowUserModal(true);
              }}
            >
              <FaUserPlus className="me-2" />Create First User
            </Button>
          </div>
        )}
      </Card.Body>
    </Card>
  );

  const renderGroups = () => (
    <Card>
      <Card.Header>
        <h5>Groups</h5>
      </Card.Header>
      <Card.Body>
        <Alert variant="info">
          <strong>Group Management:</strong> Groups help organize users and manage permissions efficiently.
        </Alert>
        {groups.length === 0 && (
          <div className="text-center text-muted py-4">
            <p>No groups created yet.</p>
          </div>
        )}
      </Card.Body>
    </Card>
  );

  const renderACLs = () => (
    <Card>
      <Card.Header>
        <h5><FaShieldAlt className="me-2" />Access Control Lists</h5>
      </Card.Header>
      <Card.Body>
        <Alert variant="info">
          <strong>ACL Management:</strong> Control fine-grained permissions for files and directories.
        </Alert>
        {acls.length === 0 && (
          <div className="text-center text-muted py-4">
            <p>No ACL rules configured.</p>
          </div>
        )}
      </Card.Body>
    </Card>
  );

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
        <h1><FaUsers className="me-2" />Credentials</h1>
      </div>

      <Nav variant="tabs" className="mb-4">
        <Nav.Item>
          <Nav.Link 
            active={activeTab === 'users'} 
            onClick={() => setActiveTab('users')}
          >
            <FaUsers className="me-2" />Users
          </Nav.Link>
        </Nav.Item>
        <Nav.Item>
          <Nav.Link 
            active={activeTab === 'groups'} 
            onClick={() => setActiveTab('groups')}
          >
            Groups
          </Nav.Link>
        </Nav.Item>
        <Nav.Item>
          <Nav.Link 
            active={activeTab === 'acl'} 
            onClick={() => setActiveTab('acl')}
          >
            <FaShieldAlt className="me-2" />Access Control
          </Nav.Link>
        </Nav.Item>
      </Nav>

      {activeTab === 'users' && renderUsers()}
      {activeTab === 'groups' && renderGroups()}
      {activeTab === 'acl' && renderACLs()}

      <UserModal />
    </Container>
  );
};

export default Credentials;