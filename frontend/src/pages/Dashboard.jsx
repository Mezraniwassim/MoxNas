import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Container,
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  LinearProgress,
  CircularProgress,
  Chip,
  Button,
  IconButton,
  Switch,
  FormControlLabel,
  Alert,
} from '@mui/material';
import {
  Storage as StorageIcon,
  Share as ShareIcon,
  People as PeopleIcon,
  Computer as ComputerIcon,
  Memory as MemoryIcon,
  Speed as SpeedIcon,
  NetworkCheck as NetworkIcon,
  Refresh as RefreshIcon,
  PlayArrow,
  Stop,
  Restart,
} from '@mui/icons-material';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { systemAPI, servicesAPI } from '../services/api';
import { format, subMinutes } from 'date-fns';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const Dashboard = () => {
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(5000);

  const { data: systemStats, isLoading: statsLoading, refetch: refetchStats } = useQuery({
    queryKey: ['systemStats'],
    queryFn: systemAPI.getSystemStats,
    refetchInterval: autoRefresh ? refreshInterval : false,
    select: (response) => response.data,
  });

  const { data: systemInfo, isLoading: infoLoading } = useQuery({
    queryKey: ['systemInfo'],
    queryFn: systemAPI.getSystemInfo,
    refetchInterval: autoRefresh ? 30000 : false,
    select: (response) => response.data,
  });

  const { data: services, isLoading: servicesLoading, refetch: refetchServices } = useQuery({
    queryKey: ['services'],
    queryFn: servicesAPI.getServices,
    refetchInterval: autoRefresh ? 10000 : false,
    select: (response) => response.data,
  });

  const generateChartData = () => {
    const now = new Date();
    const labels = Array.from({ length: 10 }, (_, i) =>
      format(subMinutes(now, 9 - i), 'HH:mm')
    );

    return {
      labels,
      datasets: [
        {
          label: 'CPU Usage (%)',
          data: systemStats?.cpu?.history || Array(10).fill(0),
          borderColor: 'rgb(75, 192, 192)',
          backgroundColor: 'rgba(75, 192, 192, 0.1)',
          tension: 0.4,
          fill: true,
        },
        {
          label: 'Memory Usage (%)',
          data: systemStats?.memory?.history || Array(10).fill(0),
          borderColor: 'rgb(255, 99, 132)',
          backgroundColor: 'rgba(255, 99, 132, 0.1)',
          tension: 0.4,
          fill: true,
        },
      ],
    };
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: false,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        ticks: {
          callback: function(value) {
            return value + '%';
          },
        },
      },
    },
    interaction: {
      intersect: false,
    },
  };

  const StatCard = ({ title, value, subtitle, icon, color = 'primary', progress }) => (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Typography color="text.secondary" variant="h6" fontWeight={500}>
            {title}
          </Typography>
          <Box color={`${color}.main`}>
            {icon}
          </Box>
        </Box>
        <Typography variant="h4" component="h2" fontWeight={600} gutterBottom>
          {value}
        </Typography>
        {subtitle && (
          <Typography variant="body2" color="text.secondary">
            {subtitle}
          </Typography>
        )}
        {progress !== undefined && (
          <Box mt={2}>
            <LinearProgress
              variant="determinate"
              value={progress}
              sx={{ height: 8, borderRadius: 1 }}
              color={systemStats?.cpu?.percent > 80 ? 'error' : 'primary'}
            />
            <Typography variant="caption" color="text.secondary" mt={1}>
              {progress}% used
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );

  const ServiceCard = ({ service }) => (
    <Card>
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Typography variant="h6" fontWeight={500}>
            {service.name}
          </Typography>
          <Chip
            label={service.status}
            color={service.status === 'running' ? 'success' : 'error'}
            size="small"
          />
        </Box>
        <Typography variant="body2" color="text.secondary" mb={2}>
          {service.description}
        </Typography>
        <Box display="flex" gap={1}>
          <IconButton
            size="small"
            color="primary"
            disabled={service.status === 'running'}
          >
            <PlayArrow />
          </IconButton>
          <IconButton
            size="small"
            color="error"
            disabled={service.status === 'stopped'}
          >
            <Stop />
          </IconButton>
          <IconButton size="small" color="warning">
            <Restart />
          </IconButton>
        </Box>
      </CardContent>
    </Card>
  );

  if (statsLoading && !systemStats) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="50vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight={600}>
          Dashboard
        </Typography>
        <Box display="flex" alignItems="center" gap={2}>
          <FormControlLabel
            control={
              <Switch
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
            }
            label="Auto Refresh"
          />
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={() => {
              refetchStats();
              refetchServices();
            }}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="CPU Usage"
            value={`${systemStats?.cpu?.percent || 0}%`}
            subtitle={`Load: ${systemStats?.cpu?.load || '0.00'}`}
            icon={<SpeedIcon fontSize="large" />}
            color="primary"
            progress={systemStats?.cpu?.percent || 0}
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Memory"
            value={`${((systemStats?.memory?.used || 0) / (1024 ** 3)).toFixed(1)} GB`}
            subtitle={`of ${((systemStats?.memory?.total || 0) / (1024 ** 3)).toFixed(1)} GB`}
            icon={<MemoryIcon fontSize="large" />}
            color="secondary"
            progress={systemStats?.memory?.percent || 0}
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Storage"
            value={`${((systemStats?.storage?.used || 0) / (1024 ** 3)).toFixed(1)} GB`}
            subtitle={`of ${((systemStats?.storage?.total || 0) / (1024 ** 3)).toFixed(1)} GB`}
            icon={<StorageIcon fontSize="large" />}
            color="warning"
            progress={systemStats?.storage?.percent || 0}
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Network"
            value={`${((systemStats?.network?.rx || 0) / (1024 ** 2)).toFixed(1)} MB/s`}
            subtitle={`↑ ${((systemStats?.network?.tx || 0) / (1024 ** 2)).toFixed(1)} MB/s`}
            icon={<NetworkIcon fontSize="large" />}
            color="success"
          />
        </Grid>

        <Grid item xs={12} lg={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" fontWeight={600} gutterBottom>
              System Performance
            </Typography>
            <Box height={300}>
              <Line data={generateChartData()} options={chartOptions} />
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} lg={4}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" fontWeight={600} gutterBottom>
              System Information
            </Typography>
            <Box>
              <Typography variant="body2" gutterBottom>
                <strong>Hostname:</strong> {systemInfo?.hostname || 'moxnas'}
              </Typography>
              <Typography variant="body2" gutterBottom>
                <strong>Version:</strong> {systemInfo?.version || 'MoxNAS 1.0.0'}
              </Typography>
              <Typography variant="body2" gutterBottom>
                <strong>Uptime:</strong> {systemInfo?.uptime || '0 days, 0 hours'}
              </Typography>
              <Typography variant="body2" gutterBottom>
                <strong>Kernel:</strong> {systemInfo?.kernel || 'Linux 6.x'}
              </Typography>
              <Typography variant="body2">
                <strong>Architecture:</strong> {systemInfo?.arch || 'x86_64'}
              </Typography>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" fontWeight={600} gutterBottom>
              Services Status
            </Typography>
            {servicesLoading ? (
              <Box display="flex" justifyContent="center" p={3}>
                <CircularProgress />
              </Box>
            ) : services?.length > 0 ? (
              <Grid container spacing={2}>
                {services.slice(0, 6).map((service) => (
                  <Grid item xs={12} sm={6} md={4} key={service.name}>
                    <ServiceCard service={service} />
                  </Grid>
                ))}
              </Grid>
            ) : (
              <Alert severity="info">No services configured</Alert>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
};

export default Dashboard;