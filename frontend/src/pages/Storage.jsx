import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Container,
  Typography,
  Grid,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Chip,
  LinearProgress,
  Box,
  Tabs,
  Tab,
  Card,
  CardContent,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
  Storage as StorageIcon,
  HardDrive as HardDriveIcon,
  Settings as SettingsIcon,
  Delete as DeleteIcon,
  Visibility as VisibilityIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { storageAPI } from '../services/api';
import toast from 'react-hot-toast';

function TabPanel({ children, value, index, ...other }) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`storage-tabpanel-${index}`}
      aria-labelledby={`storage-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

const Storage = () => {
  const [tabValue, setTabValue] = useState(0);
  const [createPoolOpen, setCreatePoolOpen] = useState(false);
  const [createMountPointOpen, setCreateMountPointOpen] = useState(false);
  const [selectedDisks, setSelectedDisks] = useState([]);
  const [poolConfig, setPoolConfig] = useState({
    name: '',
    type: 'mirror',
    disks: [],
  });

  const { data: pools, isLoading: poolsLoading, refetch: refetchPools } = useQuery({
    queryKey: ['storagePools'],
    queryFn: storageAPI.getPools,
    select: (response) => response.data,
  });

  const { data: disks, isLoading: disksLoading, refetch: refetchDisks } = useQuery({
    queryKey: ['storageDisks'],
    queryFn: storageAPI.getDisks,
    select: (response) => response.data,
  });

  const { data: mountPoints, isLoading: mountPointsLoading, refetch: refetchMountPoints } = useQuery({
    queryKey: ['storageMountPoints'],
    queryFn: storageAPI.getMountPoints,
    select: (response) => response.data,
  });

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  const getStatusColor = (status) => {
    const statusMap = {
      online: 'success',
      healthy: 'success',
      degraded: 'warning',
      warning: 'warning',
      critical: 'error',
      failed: 'error',
      offline: 'error',
    };
    return statusMap[status?.toLowerCase()] || 'default';
  };

  const handleCreatePool = async () => {
    try {
      await storageAPI.createPool(poolConfig);
      toast.success('Storage pool created successfully');
      setCreatePoolOpen(false);
      setPoolConfig({ name: '', type: 'mirror', disks: [] });
      refetchPools();
    } catch (error) {
      toast.error('Failed to create storage pool');
    }
  };

  const handleScanDisks = async () => {
    try {
      await storageAPI.scanDisks();
      toast.success('Disk scan completed');
      refetchDisks();
    } catch (error) {
      toast.error('Failed to scan disks');
    }
  };

  const PoolsTab = () => (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h6" fontWeight={600}>
          Storage Pools
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreatePoolOpen(true)}
        >
          Create Pool
        </Button>
      </Box>

      {poolsLoading ? (
        <Box display="flex" justifyContent="center" p={3}>
          <CircularProgress />
        </Box>
      ) : pools?.length > 0 ? (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Size</TableCell>
                <TableCell>Used</TableCell>
                <TableCell>Available</TableCell>
                <TableCell>Usage</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {pools.map((pool) => (
                <TableRow key={pool.id}>
                  <TableCell fontWeight={500}>{pool.name}</TableCell>
                  <TableCell>{pool.type}</TableCell>
                  <TableCell>
                    <Chip
                      label={pool.status}
                      color={getStatusColor(pool.status)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{formatBytes(pool.total_size)}</TableCell>
                  <TableCell>{formatBytes(pool.used_size)}</TableCell>
                  <TableCell>{formatBytes(pool.available_size)}</TableCell>
                  <TableCell>
                    <Box display="flex" alignItems="center" gap={1}>
                      <LinearProgress
                        variant="determinate"
                        value={pool.usage_percentage || 0}
                        sx={{ width: 80, height: 6, borderRadius: 1 }}
                        color={pool.usage_percentage > 80 ? 'error' : 'primary'}
                      />
                      <Typography variant="caption">
                        {pool.usage_percentage || 0}%
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <IconButton size="small" color="primary">
                      <SettingsIcon />
                    </IconButton>
                    <IconButton size="small" color="error">
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        <Alert severity="info">No storage pools found. Create your first pool to get started.</Alert>
      )}
    </Box>
  );

  const DisksTab = () => (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h6" fontWeight={600}>
          Physical Disks
        </Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={handleScanDisks}
        >
          Scan Disks
        </Button>
      </Box>

      {disksLoading ? (
        <Box display="flex" justifyContent="center" p={3}>
          <CircularProgress />
        </Box>
      ) : disks?.length > 0 ? (
        <Grid container spacing={3}>
          {disks.map((disk) => (
            <Grid item xs={12} md={6} lg={4} key={disk.id}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                    <Box display="flex" alignItems="center" gap={1}>
                      <HardDriveIcon color="primary" />
                      <Typography variant="h6" fontWeight={500}>
                        {disk.device_name}
                      </Typography>
                    </Box>
                    <Chip
                      label={disk.status}
                      color={getStatusColor(disk.status)}
                      size="small"
                    />
                  </Box>
                  
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {disk.model}
                  </Typography>
                  
                  <Box display="flex" justifyContent="space-between" mb={1}>
                    <Typography variant="body2">Size:</Typography>
                    <Typography variant="body2" fontWeight={500}>
                      {formatBytes(disk.size)}
                    </Typography>
                  </Box>
                  
                  <Box display="flex" justifyContent="space-between" mb={1}>
                    <Typography variant="body2">Type:</Typography>
                    <Typography variant="body2" fontWeight={500}>
                      {disk.type?.toUpperCase()}
                    </Typography>
                  </Box>
                  
                  <Box display="flex" justifyContent="space-between" mb={2}>
                    <Typography variant="body2">Temperature:</Typography>
                    <Typography 
                      variant="body2" 
                      fontWeight={500}
                      color={disk.temperature > 50 ? 'error.main' : 'text.primary'}
                    >
                      {disk.temperature}°C
                    </Typography>
                  </Box>
                  
                  <Box display="flex" gap={1}>
                    <Button size="small" variant="outlined" startIcon={<VisibilityIcon />}>
                      SMART
                    </Button>
                    {disk.status === 'warning' && (
                      <IconButton size="small" color="warning">
                        <WarningIcon />
                      </IconButton>
                    )}
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      ) : (
        <Alert severity="info">No disks found. Click "Scan Disks" to detect storage devices.</Alert>
      )}
    </Box>
  );

  const MountPointsTab = () => (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h6" fontWeight={600}>
          Mount Points
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateMountPointOpen(true)}
        >
          Add Mount Point
        </Button>
      </Box>

      {mountPointsLoading ? (
        <Box display="flex" justifyContent="center" p={3}>
          <CircularProgress />
        </Box>
      ) : mountPoints?.length > 0 ? (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Path</TableCell>
                <TableCell>Pool</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Size</TableCell>
                <TableCell>Used</TableCell>
                <TableCell>Available</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {mountPoints.map((mp) => (
                <TableRow key={mp.id}>
                  <TableCell fontWeight={500}>{mp.path}</TableCell>
                  <TableCell>{mp.pool}</TableCell>
                  <TableCell>{mp.type}</TableCell>
                  <TableCell>{formatBytes(mp.total_size)}</TableCell>
                  <TableCell>{formatBytes(mp.used_size)}</TableCell>
                  <TableCell>{formatBytes(mp.available_size)}</TableCell>
                  <TableCell>
                    <IconButton size="small" color="error">
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        <Alert severity="info">No mount points configured.</Alert>
      )}
    </Box>
  );

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight={600}>
          Storage Management
        </Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={() => {
            refetchPools();
            refetchDisks();
            refetchMountPoints();
          }}
        >
          Refresh All
        </Button>
      </Box>

      <Paper sx={{ width: '100%' }}>
        <Tabs
          value={tabValue}
          onChange={(e, newValue) => setTabValue(newValue)}
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab label="Storage Pools" icon={<StorageIcon />} iconPosition="start" />
          <Tab label="Disks" icon={<HardDriveIcon />} iconPosition="start" />
          <Tab label="Mount Points" icon={<SettingsIcon />} iconPosition="start" />
        </Tabs>

        <TabPanel value={tabValue} index={0}>
          <PoolsTab />
        </TabPanel>
        <TabPanel value={tabValue} index={1}>
          <DisksTab />
        </TabPanel>
        <TabPanel value={tabValue} index={2}>
          <MountPointsTab />
        </TabPanel>
      </Paper>

      <Dialog open={createPoolOpen} onClose={() => setCreatePoolOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create Storage Pool</DialogTitle>
        <DialogContent>
          <Box display="flex" flexDirection="column" gap={2} pt={1}>
            <TextField
              label="Pool Name"
              value={poolConfig.name}
              onChange={(e) => setPoolConfig({ ...poolConfig, name: e.target.value })}
              fullWidth
            />
            <FormControl fullWidth>
              <InputLabel>Pool Type</InputLabel>
              <Select
                value={poolConfig.type}
                onChange={(e) => setPoolConfig({ ...poolConfig, type: e.target.value })}
              >
                <MenuItem value="stripe">Stripe (RAID 0)</MenuItem>
                <MenuItem value="mirror">Mirror (RAID 1)</MenuItem>
                <MenuItem value="raidz1">RAID-Z1 (RAID 5)</MenuItem>
                <MenuItem value="raidz2">RAID-Z2 (RAID 6)</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreatePoolOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreatePool}>
            Create Pool
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default Storage;