import React from 'react';
import { Container, Card, Table, Badge } from 'react-bootstrap';
import { FaNetworkWired } from 'react-icons/fa';

const Network = () => {
  const services = [
    { name: 'MoxNAS Web Interface', port: 8080, protocol: 'TCP', status: 'Active' },
    { name: 'SMB/CIFS', port: 445, protocol: 'TCP', status: 'Configurable' },
    { name: 'NFS', port: 2049, protocol: 'TCP/UDP', status: 'Configurable' },
    { name: 'FTP', port: 21, protocol: 'TCP', status: 'Configurable' },
    { name: 'SSH', port: 22, protocol: 'TCP', status: 'Active' },
    { name: 'SNMP', port: 161, protocol: 'UDP', status: 'Configurable' },
    { name: 'iSCSI', port: 3260, protocol: 'TCP', status: 'Configurable' },
  ];

  return (
    <Container fluid>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h1><FaNetworkWired className="me-2" />Network</h1>
      </div>

      <Card>
        <Card.Header>
          <h5>Service Ports</h5>
        </Card.Header>
        <Card.Body>
          <div className="alert alert-info">
            <h6><i className="fas fa-info-circle me-2"></i>Network Configuration</h6>
            <p className="mb-0">Network configuration is managed by the LXC container host. To modify network settings, please configure them at the Proxmox host level.</p>
          </div>
          
          <Table responsive>
            <thead>
              <tr>
                <th>Service</th>
                <th>Port</th>
                <th>Protocol</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {services.map((service, index) => (
                <tr key={index}>
                  <td>{service.name}</td>
                  <td>{service.port}</td>
                  <td>{service.protocol}</td>
                  <td>
                    <Badge bg={service.status === 'Active' ? 'success' : 'secondary'}>
                      {service.status}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card.Body>
      </Card>
    </Container>
  );
};

export default Network;