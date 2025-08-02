import React, { useState, useEffect } from 'react';
import {
    Modal,
    ModalHeader,
    ModalBody,
    ModalFooter,
    Form,
    FormGroup,
    Label,
    Input,
    Button,
    Alert,
    Spinner,
    Card,
    CardBody,
    CardHeader,
    Badge,
    Row,
    Col,
    InputGroup,
    InputGroupText
} from 'reactstrap';
import { FaServer, FaUser, FaLock, FaEye, FaEyeSlash, FaPlug, FaCheck, FaTimes } from 'react-icons/fa';
import { api } from '../services/api';

const ProxmoxLogin = ({ isOpen, toggle, onLoginSuccess }) => {
    const [formData, setFormData] = useState({
        host: '',
        port: 8006,
        username: 'root',
        password: '',
        realm: 'pam',
        verify_ssl: false,
        remember_host: false
    });
    
    const [savedHosts, setSavedHosts] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [testingConnection, setTestingConnection] = useState(false);
    const [connectionResult, setConnectionResult] = useState(null);

    useEffect(() => {
        if (isOpen) {
            loadSavedHosts();
            setError('');
            setSuccess('');
            setConnectionResult(null);
        }
    }, [isOpen]);

    const loadSavedHosts = async () => {
        try {
            const response = await api.get('/api/proxmox-auth/saved-hosts/');
            if (response.data.success) {
                setSavedHosts(response.data.hosts || []);
            }
        } catch (err) {
            console.error('Failed to load saved hosts:', err);
        }
    };

    const handleInputChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
        setError('');
        setConnectionResult(null);
    };

    const selectSavedHost = (host) => {
        setFormData(prev => ({
            ...prev,
            host: host.host,
            port: host.port,
            username: host.username.split('@')[0], // Remove realm from username
            realm: host.realm,
            verify_ssl: host.ssl_verify,
            password: '' // Always require password input
        }));
        setError('');
        setConnectionResult(null);
    };

    const testConnection = async () => {
        if (!formData.host || !formData.username || !formData.password) {
            setError('Please fill in all required fields');
            return;
        }

        setTestingConnection(true);
        setError('');
        
        try {
            const response = await api.post('/api/proxmox-auth/login/', {
                ...formData,
                test_only: true // Add this to just test, not create session
            });

            if (response.data.success) {
                setConnectionResult({
                    success: true,
                    message: 'Connection successful!'
                });
            } else {
                setConnectionResult({
                    success: false,
                    message: response.data.message || 'Connection failed'
                });
            }
        } catch (err) {
            setConnectionResult({
                success: false,
                message: err.response?.data?.message || 'Connection test failed'
            });
        } finally {
            setTestingConnection(false);
        }
    };

    const handleLogin = async (e) => {
        e.preventDefault();
        
        if (!formData.host || !formData.username || !formData.password) {
            setError('Please fill in all required fields');
            return;
        }

        setLoading(true);
        setError('');
        setSuccess('');

        try {
            const response = await api.post('/api/proxmox-auth/login/', formData);

            if (response.data.success) {
                const sessionData = {
                    sessionKey: response.data.session_key,
                    hostInfo: response.data.host_info,
                    connectionTest: response.data.connection_test
                };

                // Store session key for future requests
                localStorage.setItem('proxmox_session_key', response.data.session_key);
                localStorage.setItem('proxmox_host_info', JSON.stringify(response.data.host_info));

                setSuccess('Login successful! You can now manage your Proxmox infrastructure.');
                
                // Call success callback
                if (onLoginSuccess) {
                    onLoginSuccess(sessionData);
                }

                // Close modal after short delay
                setTimeout(() => {
                    toggle();
                    resetForm();
                }, 1500);

            } else {
                setError(response.data.message || 'Login failed');
            }
        } catch (err) {
            const errorMsg = err.response?.data?.message || 'Login failed. Please check your credentials.';
            setError(errorMsg);
        } finally {
            setLoading(false);
        }
    };

    const resetForm = () => {
        setFormData({
            host: '',
            port: 8006,
            username: 'root',
            password: '',
            realm: 'pam',
            verify_ssl: false,
            remember_host: false
        });
        setError('');
        setSuccess('');
        setConnectionResult(null);
    };

    return (
        <Modal isOpen={isOpen} toggle={toggle} size="lg">
            <ModalHeader toggle={toggle}>
                <FaServer className="me-2" />
                Connect to Proxmox Host
            </ModalHeader>
            <ModalBody>
                {error && (
                    <Alert color="danger" className="mb-3">
                        <FaTimes className="me-2" />
                        {error}
                    </Alert>
                )}

                {success && (
                    <Alert color="success" className="mb-3">
                        <FaCheck className="me-2" />
                        {success}
                    </Alert>
                )}

                {connectionResult && (
                    <Alert color={connectionResult.success ? 'success' : 'danger'} className="mb-3">
                        {connectionResult.success ? <FaCheck className="me-2" /> : <FaTimes className="me-2" />}
                        {connectionResult.message}
                    </Alert>
                )}

                <Row>
                    <Col md="8">
                        <Form onSubmit={handleLogin}>
                            <Row>
                                <Col md="8">
                                    <FormGroup>
                                        <Label for="host">
                                            <FaServer className="me-1" />
                                            Host/IP Address *
                                        </Label>
                                        <Input
                                            type="text"
                                            name="host"
                                            id="host"
                                            placeholder="192.168.1.100 or proxmox.local"
                                            value={formData.host}
                                            onChange={handleInputChange}
                                            required
                                        />
                                    </FormGroup>
                                </Col>
                                <Col md="4">
                                    <FormGroup>
                                        <Label for="port">Port</Label>
                                        <Input
                                            type="number"
                                            name="port"
                                            id="port"
                                            value={formData.port}
                                            onChange={handleInputChange}
                                            min="1"
                                            max="65535"
                                        />
                                    </FormGroup>
                                </Col>
                            </Row>

                            <Row>
                                <Col md="6">
                                    <FormGroup>
                                        <Label for="username">
                                            <FaUser className="me-1" />
                                            Username *
                                        </Label>
                                        <Input
                                            type="text"
                                            name="username"
                                            id="username"
                                            value={formData.username}
                                            onChange={handleInputChange}
                                            required
                                        />
                                    </FormGroup>
                                </Col>
                                <Col md="6">
                                    <FormGroup>
                                        <Label for="realm">Realm</Label>
                                        <Input
                                            type="select"
                                            name="realm"
                                            id="realm"
                                            value={formData.realm}
                                            onChange={handleInputChange}
                                        >
                                            <option value="pam">PAM (Local)</option>
                                            <option value="pve">PVE (Proxmox VE)</option>
                                            <option value="ad">Active Directory</option>
                                            <option value="ldap">LDAP</option>
                                        </Input>
                                    </FormGroup>
                                </Col>
                            </Row>

                            <FormGroup>
                                <Label for="password">
                                    <FaLock className="me-1" />
                                    Password *
                                </Label>
                                <InputGroup>
                                    <Input
                                        type={showPassword ? "text" : "password"}
                                        name="password"
                                        id="password"
                                        value={formData.password}
                                        onChange={handleInputChange}
                                        required
                                    />
                                    <InputGroupText 
                                        style={{ cursor: 'pointer' }}
                                        onClick={() => setShowPassword(!showPassword)}
                                    >
                                        {showPassword ? <FaEyeSlash /> : <FaEye />}
                                    </InputGroupText>
                                </InputGroup>
                            </FormGroup>

                            <Row>
                                <Col md="6">
                                    <FormGroup check>
                                        <Input
                                            type="checkbox"
                                            name="verify_ssl"
                                            id="verify_ssl"
                                            checked={formData.verify_ssl}
                                            onChange={handleInputChange}
                                        />
                                        <Label check for="verify_ssl">
                                            Verify SSL Certificate
                                        </Label>
                                    </FormGroup>
                                </Col>
                                <Col md="6">
                                    <FormGroup check>
                                        <Input
                                            type="checkbox"
                                            name="remember_host"
                                            id="remember_host"
                                            checked={formData.remember_host}
                                            onChange={handleInputChange}
                                        />
                                        <Label check for="remember_host">
                                            Remember this host
                                        </Label>
                                    </FormGroup>
                                </Col>
                            </Row>
                        </Form>
                    </Col>

                    <Col md="4">
                        <Card>
                            <CardHeader>
                                <h6 className="mb-0">Saved Hosts</h6>
                            </CardHeader>
                            <CardBody>
                                {savedHosts.length === 0 ? (
                                    <small className="text-muted">No saved hosts</small>
                                ) : (
                                    savedHosts.map((host, idx) => (
                                        <div 
                                            key={idx}
                                            className="d-flex justify-content-between align-items-center mb-2 p-2 border rounded"
                                            style={{ cursor: 'pointer' }}
                                            onClick={() => selectSavedHost(host)}
                                        >
                                            <div>
                                                <strong>{host.host}:{host.port}</strong>
                                                <br />
                                                <small className="text-muted">
                                                    {host.username}
                                                </small>
                                            </div>
                                            <Badge color="primary" pill>
                                                {host.realm}
                                            </Badge>
                                        </div>
                                    ))
                                )}
                            </CardBody>
                        </Card>
                    </Col>
                </Row>
            </ModalBody>
            <ModalFooter>
                <Button color="secondary" onClick={toggle} disabled={loading}>
                    Cancel
                </Button>
                <Button 
                    color="info" 
                    onClick={testConnection} 
                    disabled={loading || testingConnection}
                    className="me-2"
                >
                    {testingConnection ? (
                        <>
                            <Spinner size="sm" className="me-2" />
                            Testing...
                        </>
                    ) : (
                        <>
                            <FaPlug className="me-2" />
                            Test Connection
                        </>
                    )}
                </Button>
                <Button 
                    color="primary" 
                    onClick={handleLogin} 
                    disabled={loading || testingConnection}
                >
                    {loading ? (
                        <>
                            <Spinner size="sm" className="me-2" />
                            Connecting...
                        </>
                    ) : (
                        <>
                            <FaServer className="me-2" />
                            Connect
                        </>
                    )}
                </Button>
            </ModalFooter>
        </Modal>
    );
};

export default ProxmoxLogin;