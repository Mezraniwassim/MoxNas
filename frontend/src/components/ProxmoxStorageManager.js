import React, { useState, useEffect } from 'react';
import { 
    Card, 
    CardBody, 
    CardHeader, 
    Table, 
    Button, 
    Modal, 
    ModalHeader, 
    ModalBody, 
    ModalFooter,
    Form,
    FormGroup,
    Label,
    Input,
    Progress,
    Badge,
    Row,
    Col,
    Nav,
    NavItem,
    NavLink,
    TabContent,
    TabPane,
    Alert,
    Spinner
} from 'reactstrap';
import { api } from '../services/api';

const ProxmoxStorageManager = () => {
    const [activeTab, setActiveTab] = useState('storage');
    const [storages, setStorages] = useState([]);
    const [containers, setContainers] = useState([]);
    const [backups, setBackups] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    
    // Modals
    const [mountModal, setMountModal] = useState(false);
    const [backupModal, setBackupModal] = useState(false);
    const [directoryModal, setDirectoryModal] = useState(false);
    
    // Form data
    const [selectedContainer, setSelectedContainer] = useState('');
    const [selectedStorage, setSelectedStorage] = useState('');
    const [mountPoint, setMountPoint] = useState('');
    const [hostPath, setHostPath] = useState('');
    const [directoryPath, setDirectoryPath] = useState('');
    const [backupStorage, setBackupStorage] = useState('local');
    const [compression, setCompression] = useState('lzo');

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setLoading(true);
        try {
            await Promise.all([
                loadStorages(),
                loadContainers(),
                loadBackups()
            ]);
        } catch (err) {
            setError('Failed to load data');
        } finally {
            setLoading(false);
        }
    };

    const loadStorages = async () => {
        try {
            const response = await api.get('/api/proxmox-storage/');
            setStorages(response.data || []);
        } catch (err) {
            console.error('Failed to load storages:', err);
        }
    };

    const loadContainers = async () => {
        try {
            const response = await api.get('/api/proxmox-containers/');
            setContainers(response.data || []);
        } catch (err) {
            console.error('Failed to load containers:', err);
        }
    };

    const loadBackups = async () => {
        try {
            // Get first host for now - in real app, let user select
            const hosts = await api.get('/api/proxmox-hosts/');
            if (hosts.data && hosts.data.length > 0) {
                const response = await api.get(`/api/proxmox-backups/list_backups/?host_id=${hosts.data[0].id}`);
                setBackups(response.data.backups || []);
            }
        } catch (err) {
            console.error('Failed to load backups:', err);
        }
    };

    const syncStorages = async () => {
        try {
            // Get first host for now
            const hosts = await api.get('/api/proxmox-hosts/');
            if (hosts.data && hosts.data.length > 0) {
                const response = await api.post('/api/proxmox-storage/sync_from_proxmox/', {
                    host_id: hosts.data[0].id
                });
                
                if (response.data.success) {
                    setSuccess(`Synced ${response.data.synced} storage configurations`);
                    loadStorages();
                } else {
                    setError('Failed to sync storages');
                }
            }
        } catch (err) {
            setError('Failed to sync storages');
        }
    };

    const addMount = async () => {
        if (!selectedContainer || !mountPoint) {
            setError('Container and mount point are required');
            return;
        }

        try {
            const response = await api.post('/api/container-storage/add_mount/', {
                container_id: selectedContainer,
                storage_id: selectedStorage,
                mount_point: mountPoint,
                host_path: hostPath
            });

            if (response.data.success) {
                setSuccess('Mount point added successfully');
                setMountModal(false);
                resetForm();
                loadContainers();
            } else {
                setError(response.data.error || 'Failed to add mount');
            }
        } catch (err) {
            setError('Failed to add mount point');
        }
    };

    const createBackup = async () => {
        if (!selectedContainer) {
            setError('Please select a container');
            return;
        }

        try {
            const response = await api.post('/api/proxmox-backups/create_backup/', {
                container_id: selectedContainer,
                storage_id: backupStorage,
                compression: compression
            });

            if (response.data.success) {
                setSuccess(`Backup started with task ID: ${response.data.task_id}`);
                setBackupModal(false);
                resetForm();
                // Refresh backups after a delay
                setTimeout(loadBackups, 2000);
            } else {
                setError(response.data.error || 'Failed to create backup');
            }
        } catch (err) {
            setError('Failed to create backup');
        }
    };

    const createDirectory = async () => {
        if (!selectedStorage || !directoryPath) {
            setError('Storage and directory path are required');
            return;
        }

        try {
            const storage = storages.find(s => s.id == selectedStorage);
            const response = await api.post(`/api/proxmox-storage/${selectedStorage}/create_directory/`, {
                path: directoryPath
            });

            if (response.data.success) {
                setSuccess('Directory created successfully');
                setDirectoryModal(false);
                resetForm();
            } else {
                setError(response.data.error || 'Failed to create directory');
            }
        } catch (err) {
            setError('Failed to create directory');
        }
    };

    const resetForm = () => {
        setSelectedContainer('');
        setSelectedStorage('');
        setMountPoint('');
        setHostPath('');
        setDirectoryPath('');
        setBackupStorage('local');
        setCompression('lzo');
    };

    const formatBytes = (bytes) => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const getStorageTypeColor = (type) => {
        const colors = {
            'dir': 'primary',
            'nfs': 'success',
            'cifs': 'info',
            'lvm': 'warning',
            'zfs': 'secondary',
            'cephfs': 'danger'
        };
        return colors[type] || 'dark';
    };

    if (loading) {
        return (
            <div className="text-center p-4">
                <Spinner color="primary" />
                <p className="mt-2">Loading storage management...</p>
            </div>
        );
    }

    return (
        <div className="proxmox-storage-manager">
            {error && (
                <Alert color="danger" toggle={() => setError('')}>
                    {error}
                </Alert>
            )}
            
            {success && (
                <Alert color="success" toggle={() => setSuccess('')}>
                    {success}
                </Alert>
            )}

            <Nav tabs className="mb-3">
                <NavItem>
                    <NavLink 
                        className={activeTab === 'storage' ? 'active' : ''}
                        onClick={() => setActiveTab('storage')}
                        style={{ cursor: 'pointer' }}
                    >
                        Storage Management
                    </NavLink>
                </NavItem>
                <NavItem>
                    <NavLink 
                        className={activeTab === 'mounts' ? 'active' : ''}
                        onClick={() => setActiveTab('mounts')}
                        style={{ cursor: 'pointer' }}
                    >
                        Container Mounts
                    </NavLink>
                </NavItem>
                <NavItem>
                    <NavLink 
                        className={activeTab === 'backups' ? 'active' : ''}
                        onClick={() => setActiveTab('backups')}
                        style={{ cursor: 'pointer' }}
                    >
                        Backups & Snapshots
                    </NavLink>
                </NavItem>
            </Nav>

            <TabContent activeTab={activeTab}>
                {/* Storage Management Tab */}
                <TabPane tabId="storage">
                    <Card>
                        <CardHeader className="d-flex justify-content-between align-items-center">
                            <h5 className="mb-0">Proxmox Storage</h5>
                            <div>
                                <Button color="success" size="sm" onClick={syncStorages} className="me-2">
                                    Sync from Proxmox
                                </Button>
                                <Button color="primary" size="sm" onClick={() => setDirectoryModal(true)}>
                                    Create Directory
                                </Button>
                            </div>
                        </CardHeader>
                        <CardBody>
                            <Table responsive>
                                <thead>
                                    <tr>
                                        <th>Storage ID</th>
                                        <th>Type</th>
                                        <th>Path/Server</th>
                                        <th>Usage</th>
                                        <th>Content Types</th>
                                        <th>Status</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {storages.map(storage => (
                                        <tr key={storage.id}>
                                            <td>
                                                <strong>{storage.storage_id}</strong>
                                                <br />
                                                <small className="text-muted">
                                                    Host: {storage.host.name}
                                                </small>
                                            </td>
                                            <td>
                                                <Badge color={getStorageTypeColor(storage.type)}>
                                                    {storage.type.toUpperCase()}
                                                </Badge>
                                            </td>
                                            <td>
                                                {storage.type === 'nfs' || storage.type === 'cifs' ? (
                                                    <>
                                                        <strong>{storage.server}</strong>
                                                        <br />
                                                        <small>{storage.export}</small>
                                                    </>
                                                ) : (
                                                    storage.path
                                                )}
                                            </td>
                                            <td>
                                                {storage.total_space > 0 ? (
                                                    <>
                                                        <Progress 
                                                            value={storage.usage_percentage} 
                                                            color={storage.usage_percentage > 80 ? 'danger' : 'success'}
                                                            className="mb-1"
                                                        />
                                                        <small>
                                                            {formatBytes(storage.used_space)} / {formatBytes(storage.total_space)}
                                                            ({storage.usage_percentage.toFixed(1)}%)
                                                        </small>
                                                    </>
                                                ) : (
                                                    <small className="text-muted">No usage data</small>
                                                )}
                                            </td>
                                            <td>
                                                {storage.content_types.map((type, idx) => (
                                                    <Badge key={idx} color="light" className="me-1">
                                                        {type}
                                                    </Badge>
                                                ))}
                                            </td>
                                            <td>
                                                <Badge color={storage.enabled ? 'success' : 'secondary'}>
                                                    {storage.enabled ? 'Enabled' : 'Disabled'}
                                                </Badge>
                                                {storage.shared && (
                                                    <Badge color="info" className="ms-1">Shared</Badge>
                                                )}
                                            </td>
                                            <td>
                                                <Button color="outline-primary" size="sm">
                                                    Browse
                                                </Button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </Table>
                        </CardBody>
                    </Card>
                </TabPane>

                {/* Container Mounts Tab */}
                <TabPane tabId="mounts">
                    <Card>
                        <CardHeader className="d-flex justify-content-between align-items-center">
                            <h5 className="mb-0">Container Storage Mounts</h5>
                            <Button color="primary" onClick={() => setMountModal(true)}>
                                Add Mount Point
                            </Button>
                        </CardHeader>
                        <CardBody>
                            <Row>
                                {containers.map(container => (
                                    <Col md="6" key={container.id} className="mb-3">
                                        <Card className="h-100">
                                            <CardHeader>
                                                <h6 className="mb-0">
                                                    CT{container.vmid} - {container.name}
                                                    <Badge 
                                                        color={container.status === 'running' ? 'success' : 'secondary'} 
                                                        className="ms-2"
                                                    >
                                                        {container.status}
                                                    </Badge>
                                                </h6>
                                            </CardHeader>
                                            <CardBody>
                                                <small className="text-muted">
                                                    Memory: {container.memory}MB | 
                                                    Cores: {container.cores} | 
                                                    Disk: {formatBytes(container.disk_size)}
                                                </small>
                                                {/* Mount points would be listed here if available */}
                                                <div className="mt-2">
                                                    <small className="text-muted">Mount points will be displayed here</small>
                                                </div>
                                            </CardBody>
                                        </Card>
                                    </Col>
                                ))}
                            </Row>
                        </CardBody>
                    </Card>
                </TabPane>

                {/* Backups Tab */}
                <TabPane tabId="backups">
                    <Card>
                        <CardHeader className="d-flex justify-content-between align-items-center">
                            <h5 className="mb-0">Backups & Snapshots</h5>
                            <Button color="primary" onClick={() => setBackupModal(true)}>
                                Create Backup
                            </Button>
                        </CardHeader>
                        <CardBody>
                            <Table responsive>
                                <thead>
                                    <tr>
                                        <th>Backup File</th>
                                        <th>Container</th>
                                        <th>Size</th>
                                        <th>Date</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {backups.length === 0 ? (
                                        <tr>
                                            <td colSpan="5" className="text-center text-muted">
                                                No backups found
                                            </td>
                                        </tr>
                                    ) : (
                                        backups.map((backup, idx) => (
                                            <tr key={idx}>
                                                <td>{backup.filename || 'Unknown'}</td>
                                                <td>{backup.vmid || 'N/A'}</td>
                                                <td>{backup.size ? formatBytes(backup.size) : 'Unknown'}</td>
                                                <td>{backup.ctime || 'Unknown'}</td>
                                                <td>
                                                    <Button color="outline-primary" size="sm" className="me-1">
                                                        Restore
                                                    </Button>
                                                    <Button color="outline-danger" size="sm">
                                                        Delete
                                                    </Button>
                                                </td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </Table>
                        </CardBody>
                    </Card>
                </TabPane>
            </TabContent>

            {/* Add Mount Modal */}
            <Modal isOpen={mountModal} toggle={() => setMountModal(false)}>
                <ModalHeader toggle={() => setMountModal(false)}>
                    Add Storage Mount
                </ModalHeader>
                <ModalBody>
                    <Form>
                        <FormGroup>
                            <Label for="container">Container</Label>
                            <Input
                                type="select"
                                id="container"
                                value={selectedContainer}
                                onChange={(e) => setSelectedContainer(e.target.value)}
                            >
                                <option value="">Select Container</option>
                                {containers.map(container => (
                                    <option key={container.id} value={container.id}>
                                        CT{container.vmid} - {container.name}
                                    </option>
                                ))}
                            </Input>
                        </FormGroup>
                        <FormGroup>
                            <Label for="storage">Storage (Optional)</Label>
                            <Input
                                type="select"
                                id="storage"
                                value={selectedStorage}
                                onChange={(e) => setSelectedStorage(e.target.value)}
                            >
                                <option value="">Select Storage</option>
                                {storages.map(storage => (
                                    <option key={storage.id} value={storage.storage_id}>
                                        {storage.storage_id} ({storage.type})
                                    </option>
                                ))}
                            </Input>
                        </FormGroup>
                        <FormGroup>
                            <Label for="mountPoint">Mount Point in Container</Label>
                            <Input
                                type="text"
                                id="mountPoint"
                                placeholder="/mnt/storage"
                                value={mountPoint}
                                onChange={(e) => setMountPoint(e.target.value)}
                            />
                        </FormGroup>
                        <FormGroup>
                            <Label for="hostPath">Host Path (Optional)</Label>
                            <Input
                                type="text"
                                id="hostPath"
                                placeholder="/host/path/to/storage"
                                value={hostPath}
                                onChange={(e) => setHostPath(e.target.value)}
                            />
                        </FormGroup>
                    </Form>
                </ModalBody>
                <ModalFooter>
                    <Button color="secondary" onClick={() => setMountModal(false)}>
                        Cancel
                    </Button>
                    <Button color="primary" onClick={addMount}>
                        Add Mount
                    </Button>
                </ModalFooter>
            </Modal>

            {/* Create Backup Modal */}
            <Modal isOpen={backupModal} toggle={() => setBackupModal(false)}>
                <ModalHeader toggle={() => setBackupModal(false)}>
                    Create Backup
                </ModalHeader>
                <ModalBody>
                    <Form>
                        <FormGroup>
                            <Label for="backupContainer">Container</Label>
                            <Input
                                type="select"
                                id="backupContainer"
                                value={selectedContainer}
                                onChange={(e) => setSelectedContainer(e.target.value)}
                            >
                                <option value="">Select Container</option>
                                {containers.map(container => (
                                    <option key={container.id} value={container.id}>
                                        CT{container.vmid} - {container.name}
                                    </option>
                                ))}
                            </Input>
                        </FormGroup>
                        <FormGroup>
                            <Label for="backupStorageSelect">Backup Storage</Label>
                            <Input
                                type="select"
                                id="backupStorageSelect"
                                value={backupStorage}
                                onChange={(e) => setBackupStorage(e.target.value)}
                            >
                                {storages
                                    .filter(s => s.content_types.includes('backup'))
                                    .map(storage => (
                                    <option key={storage.id} value={storage.storage_id}>
                                        {storage.storage_id} ({storage.type})
                                    </option>
                                ))}
                            </Input>
                        </FormGroup>
                        <FormGroup>
                            <Label for="compressionSelect">Compression</Label>
                            <Input
                                type="select"
                                id="compressionSelect"
                                value={compression}
                                onChange={(e) => setCompression(e.target.value)}
                            >
                                <option value="lzo">LZO (Fast)</option>
                                <option value="gzip">GZip (Balanced)</option>
                                <option value="zstd">ZSTD (Modern)</option>
                            </Input>
                        </FormGroup>
                    </Form>
                </ModalBody>
                <ModalFooter>
                    <Button color="secondary" onClick={() => setBackupModal(false)}>
                        Cancel
                    </Button>
                    <Button color="primary" onClick={createBackup}>
                        Create Backup
                    </Button>
                </ModalFooter>
            </Modal>

            {/* Create Directory Modal */}
            <Modal isOpen={directoryModal} toggle={() => setDirectoryModal(false)}>
                <ModalHeader toggle={() => setDirectoryModal(false)}>
                    Create Directory
                </ModalHeader>
                <ModalBody>
                    <Form>
                        <FormGroup>
                            <Label for="directoryStorage">Storage</Label>
                            <Input
                                type="select"
                                id="directoryStorage"
                                value={selectedStorage}
                                onChange={(e) => setSelectedStorage(e.target.value)}
                            >
                                <option value="">Select Storage</option>
                                {storages.map(storage => (
                                    <option key={storage.id} value={storage.id}>
                                        {storage.storage_id} ({storage.type})
                                    </option>
                                ))}
                            </Input>
                        </FormGroup>
                        <FormGroup>
                            <Label for="directoryPathInput">Directory Path</Label>
                            <Input
                                type="text"
                                id="directoryPathInput"
                                placeholder="new-directory"
                                value={directoryPath}
                                onChange={(e) => setDirectoryPath(e.target.value)}
                            />
                        </FormGroup>
                    </Form>
                </ModalBody>
                <ModalFooter>
                    <Button color="secondary" onClick={() => setDirectoryModal(false)}>
                        Cancel
                    </Button>
                    <Button color="primary" onClick={createDirectory}>
                        Create Directory
                    </Button>
                </ModalFooter>
            </Modal>
        </div>
    );
};

export default ProxmoxStorageManager;