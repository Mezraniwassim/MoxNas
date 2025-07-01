import React from 'react';
import { Container, Row, Col, Card } from 'react-bootstrap';
import { FaChartLine } from 'react-icons/fa';

const Reporting = () => {
  return (
    <Container fluid>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h1><FaChartLine className="me-2" />Reporting</h1>
      </div>

      <Row>
        <Col md={6}>
          <Card>
            <Card.Header>
              <h5>CPU Usage</h5>
            </Card.Header>
            <Card.Body>
              <div className="text-center text-muted py-4">
                Real-time CPU monitoring coming soon
              </div>
            </Card.Body>
          </Card>
        </Col>
        <Col md={6}>
          <Card>
            <Card.Header>
              <h5>Memory Usage</h5>
            </Card.Header>
            <Card.Body>
              <div className="text-center text-muted py-4">
                Real-time memory monitoring coming soon
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Row className="mt-4">
        <Col>
          <Card>
            <Card.Header>
              <h5>System Logs</h5>
            </Card.Header>
            <Card.Body>
              <div className="text-center text-muted py-4">
                <FaChartLine size={48} className="mb-3" />
                <h4>Advanced Reporting Coming Soon</h4>
                <p>Detailed system monitoring and reporting features will be available in future updates.</p>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default Reporting;