import React, { useState, useEffect } from 'react';
import { 
  Modal, 
  Button, 
  Form, 
  Row, 
  Col, 
  Alert, 
  Spinner, 
  Card,
  Badge,
  ProgressBar
} from 'react-bootstrap';
import { 
  FaServer, 
  FaNetworkWired, 
  FaCheckCircle, 
  FaExclamationTriangle,
  FaInfoCircle,
  FaCog
} from 'react-icons/fa';
import axios from 'axios';

const ProxmoxSetupWizard = ({ show, onClose, onComplete }) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [networkInfo, setNetworkInfo] = useState(null);
  const [formData, setFormData] = useState({
    host: '',
    port: 8006,
    username: 'root',
    password: '',
    realm: 'pam',
    ssl_verify: false
  });
  const [testResult, setTestResult] = useState(null);
  const [saveResult, setSaveResult] = useState(null);

  const totalSteps = 4;

  useEffect(() => {
    if (show) {
      loadNetworkInfo();
    }
  }, [show]);

  const loadNetworkInfo = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/core/setup/network-info/');
      if (response.data.success) {
        setNetworkInfo(response.data.data);
        setFormData(prev => ({
          ...prev,
          host: response.data.data.recommended_proxmox_host || ''
        }));
      }
    } catch (error) {
      console.error('Failed to load network info:', error);
    } finally {
      setLoading(false);
    }
  };

  const testConnection = async () => {
    try {
      setLoading(true);
      setTestResult(null);
      
      const response = await axios.post('/api/core/setup/test-proxmox/', formData);
      
      if (response.data.success) {
        setTestResult({
          success: true,
          message: response.data.message,
          data: response.data.data
        });
      } else {
        setTestResult({
          success: false,
          message: response.data.error
        });
      }
    } catch (error) {
      setTestResult({
        success: false,
        message: error.response?.data?.error || 'Connection test failed'
      });
    } finally {
      setLoading(false);
    }
  };

  const saveConfiguration = async () => {
    try {
      setLoading(true);
      setSaveResult(null);
      
      const response = await axios.post('/api/core/setup/save-proxmox/', formData);
      
      if (response.data.success) {
        setSaveResult({
          success: true,
          message: response.data.message,
          restart_required: response.data.restart_required
        });
      } else {
        setSaveResult({
          success: false,
          message: response.data.error
        });
      }
    } catch (error) {
      setSaveResult({
        success: false,
        message: error.response?.data?.error || 'Failed to save configuration'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleNext = () => {
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleFinish = () => {
    onComplete();
    onClose();
  };

  const renderStep1 = () => (
    <div>
      <div className="text-center mb-4">
        <FaNetworkWired size={48} className="text-primary mb-3" />
        <h4>Network Detection</h4>
        <p className="text-muted">Detecting your network configuration...</p>
      </div>

      {loading && (
        <div className="text-center">
          <Spinner animation="border" variant="primary" />
          <p className="mt-2">Detecting network...</p>
        </div>
      )}

      {networkInfo && (
        <Card className="mb-3">
          <Card.Body>
            <h6><FaInfoCircle className="me-2" />Network Information</h6>
            <Row>
              <Col md={6}>
                <small className="text-muted">Container IP:</small>
                <br />
                <strong>{networkInfo.container_ip}</strong>
              </Col>
              <Col md={6}>
                <small className="text-muted">Gateway IP:</small>
                <br />
                <strong>{networkInfo.gateway_ip}</strong>
              </Col>
            </Row>
            <Row className="mt-2">
              <Col md={6}>
                <small className="text-muted">Hostname:</small>
                <br />
                <strong>{networkInfo.hostname}</strong>
              </Col>
              <Col md={6}>
                <small className="text-muted">Environment:</small>
                <br />
                <Badge bg={networkInfo.is_container ? 'info' : 'secondary'}>
                  {networkInfo.is_container ? 'Container' : 'Host'}
                </Badge>
              </Col>
            </Row>
          </Card.Body>
        </Card>
      )}

      {networkInfo && (
        <Alert variant="info">
          <FaInfoCircle className="me-2" />
          <strong>Recommended Proxmox Host:</strong> {networkInfo.recommended_proxmox_host}
          <br />
          <small>This is typically your Proxmox host IP when running in a container.</small>
        </Alert>
      )}
    </div>
  );

  const renderStep2 = () => (
    <div>
      <div className="text-center mb-4">
        <FaServer size={48} className="text-primary mb-3" />
        <h4>Proxmox Configuration</h4>
        <p className="text-muted">Enter your Proxmox server details</p>
      </div>

      <Form>
        <Row>
          <Col md={8}>
            <Form.Group className="mb-3">
              <Form.Label>Proxmox Host/IP *</Form.Label>
              <Form.Control
                type="text"
                placeholder="192.168.1.100"
                value={formData.host}
                onChange={(e) => setFormData({...formData, host: e.target.value})}
                required
              />
              <Form.Text className="text-muted">
                Use your Proxmox server IP address, not localhost
              </Form.Text>
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
              <Form.Label>Username *</Form.Label>
              <Form.Control
                type="text"
                value={formData.username}
                onChange={(e) => setFormData({...formData, username: e.target.value})}
                required
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
                <option value="pam">PAM (Linux Users)</option>
                <option value="pve">PVE (Proxmox Users)</option>
              </Form.Select>
            </Form.Group>
          </Col>
        </Row>

        <Form.Group className="mb-3">
          <Form.Label>Password *</Form.Label>
          <Form.Control
            type="password"
            value={formData.password}
            onChange={(e) => setFormData({...formData, password: e.target.value})}
            required
          />
        </Form.Group>

        <Form.Check
          className="mb-3"
          type="checkbox"
          label="Verify SSL Certificate (uncheck for self-signed certificates)"
          checked={formData.ssl_verify}
          onChange={(e) => setFormData({...formData, ssl_verify: e.target.checked})}
        />
      </Form>

      {networkInfo && (
        <Alert variant="warning">
          <FaExclamationTriangle className="me-2" />
          <strong>Container Environment Detected</strong>
          <br />
          Make sure to use your Proxmox host IP ({networkInfo.gateway_ip}), not localhost or 127.0.0.1
        </Alert>
      )}
    </div>
  );

  const renderStep3 = () => (
    <div>
      <div className="text-center mb-4">
        <FaCheckCircle size={48} className="text-primary mb-3" />
        <h4>Connection Test</h4>
        <p className="text-muted">Testing connection to your Proxmox server</p>
      </div>

      <Card className="mb-3">
        <Card.Body>
          <h6>Connection Details</h6>
          <Row>
            <Col md={6}>
              <small className="text-muted">Host:</small>
              <br />
              <strong>{formData.host}:{formData.port}</strong>
            </Col>
            <Col md={6}>
              <small className="text-muted">User:</small>
              <br />
              <strong>{formData.username}@{formData.realm}</strong>
            </Col>
          </Row>
          <Row className="mt-2">
            <Col md={6}>
              <small className="text-muted">SSL Verify:</small>
              <br />
              <Badge bg={formData.ssl_verify ? 'success' : 'warning'}>
                {formData.ssl_verify ? 'Enabled' : 'Disabled'}
              </Badge>
            </Col>
            <Col md={6}>
              <small className="text-muted">Protocol:</small>
              <br />
              <strong>HTTPS</strong>
            </Col>
          </Row>
        </Card.Body>
      </Card>

      <div className="text-center mb-3">
        <Button 
          variant="primary" 
          onClick={testConnection}
          disabled={loading || !formData.host || !formData.username || !formData.password}
        >
          {loading ? (
            <>
              <Spinner size="sm" className="me-2" />
              Testing Connection...
            </>
          ) : (
            'Test Connection'
          )}
        </Button>
      </div>

      {testResult && (
        <Alert variant={testResult.success ? 'success' : 'danger'}>
          {testResult.success ? (
            <>
              <FaCheckCircle className="me-2" />
              <strong>Success!</strong> {testResult.message}
              {testResult.data && testResult.data.nodes && (
                <div className="mt-2">
                  <small>Found nodes: {testResult.data.nodes.map(n => n.node).join(', ')}</small>
                </div>
              )}
            </>
          ) : (
            <>
              <FaExclamationTriangle className="me-2" />
              <strong>Connection Failed:</strong> {testResult.message}
            </>
          )}
        </Alert>
      )}
    </div>
  );

  const renderStep4 = () => (
    <div>
      <div className="text-center mb-4">
        <FaCog size={48} className="text-primary mb-3" />
        <h4>Save Configuration</h4>
        <p className="text-muted">Save your Proxmox settings and complete setup</p>
      </div>

      {!saveResult && (
        <div className="text-center mb-3">
          <Button 
            variant="success" 
            onClick={saveConfiguration}
            disabled={loading || !testResult?.success}
          >
            {loading ? (
              <>
                <Spinner size="sm" className="me-2" />
                Saving Configuration...
              </>
            ) : (
              'Save Configuration'
            )}
          </Button>
          
          {!testResult?.success && (
            <div className="mt-2">
              <small className="text-muted">
                Please complete the connection test first
              </small>
            </div>
          )}
        </div>
      )}

      {saveResult && (
        <Alert variant={saveResult.success ? 'success' : 'danger'}>
          {saveResult.success ? (
            <>
              <FaCheckCircle className="me-2" />
              <strong>Configuration Saved!</strong> {saveResult.message}
              {saveResult.restart_required && (
                <div className="mt-2">
                  <small>MoxNAS will need to restart to apply the new settings.</small>
                </div>
              )}
            </>
          ) : (
            <>
              <FaExclamationTriangle className="me-2" />
              <strong>Save Failed:</strong> {saveResult.message}
            </>
          )}
        </Alert>
      )}

      {saveResult?.success && (
        <div className="text-center">
          <h5 className="text-success">🎉 Setup Complete!</h5>
          <p>Your Proxmox integration is now configured and ready to use.</p>
          
          <Card className="mt-3">
            <Card.Body>
              <h6>What's Next?</h6>
              <ul className="text-start">
                <li>Go to the Proxmox tab to manage containers</li>
                <li>Create new MoxNAS containers</li>
                <li>Monitor and control existing containers</li>
                <li>Sync container information from Proxmox</li>
              </ul>
            </Card.Body>
          </Card>
        </div>
      )}
    </div>
  );

  const renderCurrentStep = () => {
    switch (currentStep) {
      case 1: return renderStep1();
      case 2: return renderStep2();
      case 3: return renderStep3();
      case 4: return renderStep4();
      default: return renderStep1();
    }
  };

  return (
    <Modal show={show} onHide={onClose} size="lg" backdrop="static">
      <Modal.Header closeButton>
        <Modal.Title>
          <FaServer className="me-2" />
          Proxmox Setup Wizard
        </Modal.Title>
      </Modal.Header>
      
      <Modal.Body>
        <ProgressBar 
          now={(currentStep / totalSteps) * 100} 
          className="mb-4"
          variant="primary"
        />
        
        <div className="text-center mb-3">
          <small className="text-muted">
            Step {currentStep} of {totalSteps}
          </small>
        </div>

        {renderCurrentStep()}
      </Modal.Body>

      <Modal.Footer>
        <Button 
          variant="secondary" 
          onClick={handlePrevious}
          disabled={currentStep === 1}
        >
          Previous
        </Button>
        
        <div className="flex-grow-1"></div>
        
        {currentStep < totalSteps && (
          <Button 
            variant="primary" 
            onClick={handleNext}
            disabled={
              (currentStep === 2 && (!formData.host || !formData.username || !formData.password)) ||
              (currentStep === 3 && !testResult?.success)
            }
          >
            Next
          </Button>
        )}
        
        {currentStep === totalSteps && saveResult?.success && (
          <Button variant="success" onClick={handleFinish}>
            Finish
          </Button>
        )}
      </Modal.Footer>
    </Modal>
  );
};

export default ProxmoxSetupWizard;