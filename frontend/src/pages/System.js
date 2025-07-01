import React from 'react';
import { Container, Row, Col, Card, Button } from 'react-bootstrap';
import { FaCog, FaRedo, FaPowerOff, FaDownload } from 'react-icons/fa';

const System = () => {
  return (
    <Container fluid>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h1><FaCog className="me-2" />System</h1>
      </div>

      <Row>
        <Col md={4}>
          <Card className="text-center">
            <Card.Body>
              <FaRedo size={32} className="text-warning mb-3" />
              <h6>Restart Services</h6>
              <p className="text-muted small">Restart all MoxNAS services</p>
              <Button variant="warning" size="sm">
                <FaRedo className="me-1" />Restart
              </Button>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          <Card className="text-center">
            <Card.Body>
              <FaPowerOff size={32} className="text-danger mb-3" />
              <h6>Reboot System</h6>
              <p className="text-muted small">Restart the entire container</p>
              <Button variant="danger" size="sm">
                <FaPowerOff className="me-1" />Reboot
              </Button>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          <Card className="text-center">
            <Card.Body>
              <FaDownload size={32} className="text-info mb-3" />
              <h6>Export Config</h6>
              <p className="text-muted small">Download system configuration</p>
              <Button variant="info" size="sm">
                <FaDownload className="me-1" />Export
              </Button>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default System;