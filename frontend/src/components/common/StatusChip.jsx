import React from 'react';
import { Chip } from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  RadioButtonUnchecked as DefaultIcon,
} from '@mui/icons-material';

const StatusChip = ({ 
  status, 
  size = 'small', 
  variant = 'filled',
  showIcon = true,
  customColors = {},
  customLabels = {},
}) => {
  const getStatusConfig = (status) => {
    const statusLower = status?.toLowerCase() || '';
    
    const defaultConfigs = {
      // Success states
      online: { color: 'success', icon: CheckCircleIcon, label: 'Online' },
      healthy: { color: 'success', icon: CheckCircleIcon, label: 'Healthy' },
      running: { color: 'success', icon: CheckCircleIcon, label: 'Running' },
      active: { color: 'success', icon: CheckCircleIcon, label: 'Active' },
      enabled: { color: 'success', icon: CheckCircleIcon, label: 'Enabled' },
      connected: { color: 'success', icon: CheckCircleIcon, label: 'Connected' },
      up: { color: 'success', icon: CheckCircleIcon, label: 'Up' },
      
      // Warning states
      warning: { color: 'warning', icon: WarningIcon, label: 'Warning' },
      degraded: { color: 'warning', icon: WarningIcon, label: 'Degraded' },
      reconnecting: { color: 'warning', icon: WarningIcon, label: 'Reconnecting' },
      maintenance: { color: 'warning', icon: WarningIcon, label: 'Maintenance' },
      
      // Error states
      error: { color: 'error', icon: ErrorIcon, label: 'Error' },
      critical: { color: 'error', icon: ErrorIcon, label: 'Critical' },
      failed: { color: 'error', icon: ErrorIcon, label: 'Failed' },
      offline: { color: 'error', icon: ErrorIcon, label: 'Offline' },
      stopped: { color: 'error', icon: ErrorIcon, label: 'Stopped' },
      disabled: { color: 'error', icon: ErrorIcon, label: 'Disabled' },
      disconnected: { color: 'error', icon: ErrorIcon, label: 'Disconnected' },
      down: { color: 'error', icon: ErrorIcon, label: 'Down' },
      
      // Info states
      info: { color: 'info', icon: InfoIcon, label: 'Info' },
      pending: { color: 'info', icon: InfoIcon, label: 'Pending' },
      starting: { color: 'info', icon: InfoIcon, label: 'Starting' },
      stopping: { color: 'info', icon: InfoIcon, label: 'Stopping' },
      loading: { color: 'info', icon: InfoIcon, label: 'Loading' },
      
      // Default/unknown states
      unknown: { color: 'default', icon: DefaultIcon, label: 'Unknown' },
      default: { color: 'default', icon: DefaultIcon, label: status || 'Unknown' },
    };
    
    // Merge with custom colors and labels
    const config = defaultConfigs[statusLower] || defaultConfigs.default;
    
    return {
      ...config,
      color: customColors[statusLower] || config.color,
      label: customLabels[statusLower] || config.label,
    };
  };
  
  const config = getStatusConfig(status);
  const IconComponent = config.icon;
  
  return (
    <Chip
      label={config.label}
      color={config.color}
      size={size}
      variant={variant}
      icon={showIcon ? <IconComponent /> : undefined}
      sx={{
        fontWeight: 500,
        '& .MuiChip-icon': {
          fontSize: size === 'small' ? '16px' : '20px',
        },
      }}
    />
  );
};

export default StatusChip;