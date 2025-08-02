import React, { useState, useEffect } from 'react';
import {
    Card,
    CardBody,
    CardHeader,
    Badge,
    Button,
    Alert,
    Progress,
    Row,
    Col,
    Spinner
} from 'reactstrap';
import { FaServer, FaUser, FaClock, FaSignOutAlt, FaSignInAlt, FaCheck, FaTimes } from 'react-icons/fa';
import { api } from '../services/api';
import ProxmoxLogin from './ProxmoxLogin';

const ProxmoxSessionManager = ({ onSessionChange }) => {
    const [sessionStatus, setSessionStatus] = useState(null);
    const [loading, setLoading] = useState(true);
    const [showLogin, setShowLogin] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    useEffect(() => {
        checkSessionStatus();
        // Check session status every 30 seconds
        const interval = setInterval(checkSessionStatus, 30000);
        return () => clearInterval(interval);
    }, []);

    const checkSessionStatus = async () => {
        try {
            const sessionKey = localStorage.getItem('proxmox_session_key');
            
            if (!sessionKey) {
                setSessionStatus({ authenticated: false });
                setLoading(false);
                return;
            }

            const response = await api.get('/api/proxmox-auth/session-status/', {
                params: { session_key: sessionKey }
            });

            setSessionStatus(response.data);
            
            // Notify parent component of session change
            if (onSessionChange) {
                onSessionChange(response.data);
            }

        } catch (err) {
            console.error('Session status check failed:', err);
            setSessionStatus({ authenticated: false });
        } finally {
            setLoading(false);
        }
    };

    const handleLogin = () => {
        setShowLogin(true);
        setError('');
        setSuccess('');
    };

    const handleLoginSuccess = (sessionData) => {
        setSuccess('Successfully connected to Proxmox!');
        setError('');
        checkSessionStatus(); // Refresh session status
        
        // Notify parent component
        if (onSessionChange) {
            onSessionChange({
                authenticated: true,
                ...sessionData.hostInfo
            });
        }
    };

    const handleLogout = async () => {
        try {
            const sessionKey = localStorage.getItem('proxmox_session_key');
            
            if (sessionKey) {
                await api.post('/api/proxmox-auth/logout/', {
                    session_key: sessionKey
                });
            }

            // Clear local storage
            localStorage.removeItem('proxmox_session_key');
            localStorage.removeItem('proxmox_host_info');

            setSessionStatus({ authenticated: false });
            setSuccess('Logged out successfully');
            setError('');

            // Notify parent component
            if (onSessionChange) {
                onSessionChange({ authenticated: false });
            }

        } catch (err) {
            setError('Logout failed');
            console.error('Logout error:', err);
        }
    };

    const formatTimeRemaining = (seconds) => {
        if (seconds <= 0) return 'Expired';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;

        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else if (minutes > 0) {
            return `${minutes}m ${secs}s`;
        } else {
            return `${secs}s`;
        }
    };

    const getSessionProgressColor = (seconds) => {
        const totalSeconds = 7200; // 2 hours
        const percentage = (seconds / totalSeconds) * 100;
        
        if (percentage > 50) return 'success';
        if (percentage > 25) return 'warning';
        return 'danger';
    };

    if (loading) {
        return (
            <Card>
                <CardBody className="text-center">
                    <Spinner color="primary" />
                    <p className="mt-2 mb-0">Checking Proxmox connection...</p>
                </CardBody>
            </Card>
        );
    }

    return (
        <>
            <Card>
                <CardHeader className="d-flex justify-content-between align-items-center">
                    <h6 className="mb-0">
                        <FaServer className="me-2" />
                        Proxmox Connection
                    </h6>
                    <Badge color={sessionStatus?.authenticated ? 'success' : 'secondary'}>
                        {sessionStatus?.authenticated ? 'Connected' : 'Disconnected'}
                    </Badge>
                </CardHeader>
                <CardBody>
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

                    {sessionStatus?.authenticated ? (
                        <div>
                            <Row className="mb-3">
                                <Col sm="6">
                                    <strong>Host:</strong>
                                    <br />
                                    <span className="text-muted">
                                        {sessionStatus.host}
                                    </span>
                                </Col>
                                <Col sm="6">
                                    <strong>User:</strong>
                                    <br />
                                    <span className="text-muted">
                                        <FaUser className="me-1" />
                                        {sessionStatus.username}@{sessionStatus.realm}
                                    </span>
                                </Col>
                            </Row>

                            <Row className="mb-3">
                                <Col sm="6">
                                    <strong>Connected:</strong>
                                    <br />
                                    <span className="text-muted">
                                        <FaClock className="me-1" />
                                        {new Date(sessionStatus.authenticated_at).toLocaleString()}
                                    </span>
                                </Col>
                                <Col sm="6">
                                    <strong>Session Expires:</strong>
                                    <br />
                                    <span className="text-muted">
                                        {formatTimeRemaining(sessionStatus.time_remaining_seconds)}
                                    </span>
                                </Col>
                            </Row>

                            {sessionStatus.time_remaining_seconds > 0 && (
                                <div className="mb-3">
                                    <div className="d-flex justify-content-between align-items-center mb-1">
                                        <small>Session Time Remaining</small>
                                        <small>{Math.round((sessionStatus.time_remaining_seconds / 7200) * 100)}%</small>
                                    </div>
                                    <Progress
                                        value={(sessionStatus.time_remaining_seconds / 7200) * 100}
                                        color={getSessionProgressColor(sessionStatus.time_remaining_seconds)}
                                        className="mb-2"
                                    />
                                </div>
                            )}

                            <div className="d-flex justify-content-between">
                                <Button 
                                    color="info" 
                                    size="sm" 
                                    onClick={checkSessionStatus}
                                >
                                    Refresh Status
                                </Button>
                                <Button 
                                    color="outline-danger" 
                                    size="sm" 
                                    onClick={handleLogout}
                                >
                                    <FaSignOutAlt className="me-1" />
                                    Disconnect
                                </Button>
                            </div>
                        </div>
                    ) : (
                        <div className="text-center">
                            <div className="mb-3">
                                <FaServer size={48} className="text-muted mb-2" />
                                <h5>Not Connected to Proxmox</h5>
                                <p className="text-muted mb-0">
                                    Connect to your Proxmox host to manage storage, containers, and infrastructure.
                                </p>
                            </div>
                            <Button 
                                color="primary" 
                                onClick={handleLogin}
                            >
                                <FaSignInAlt className="me-2" />
                                Connect to Proxmox
                            </Button>
                        </div>
                    )}
                </CardBody>
            </Card>

            <ProxmoxLogin
                isOpen={showLogin}
                toggle={() => setShowLogin(false)}
                onLoginSuccess={handleLoginSuccess}
            />
        </>
    );
};

export default ProxmoxSessionManager;