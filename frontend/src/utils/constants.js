export const STORAGE_TYPES = {
  HDD: 'hdd',
  SSD: 'ssd',
  NVME: 'nvme',
  USB: 'usb',
  OPTICAL: 'optical',
};

export const POOL_TYPES = {
  STRIPE: 'stripe',
  MIRROR: 'mirror',
  RAIDZ1: 'raidz1',
  RAIDZ2: 'raidz2',
  RAIDZ3: 'raidz3',
};

export const POOL_STATUS = {
  ONLINE: 'online',
  DEGRADED: 'degraded',
  OFFLINE: 'offline',
  FAULTED: 'faulted',
  REMOVED: 'removed',
  UNAVAIL: 'unavail',
};

export const DISK_STATUS = {
  HEALTHY: 'healthy',
  WARNING: 'warning',
  CRITICAL: 'critical',
  FAILED: 'failed',
  UNKNOWN: 'unknown',
};

export const SERVICE_STATUS = {
  RUNNING: 'running',
  STOPPED: 'stopped',
  FAILED: 'failed',
  STARTING: 'starting',
  STOPPING: 'stopping',
};

export const SHARE_TYPES = {
  SMB: 'smb',
  NFS: 'nfs',
  FTP: 'ftp',
  SFTP: 'sftp',
};

export const SHARE_PERMISSIONS = {
  READ: 'read',
  WRITE: 'write',
  FULL: 'full',
  NONE: 'none',
};

export const USER_ROLES = {
  ADMIN: 'admin',
  USER: 'user',
  GUEST: 'guest',
};

export const NETWORK_INTERFACE_TYPES = {
  ETHERNET: 'ethernet',
  WIFI: 'wifi',
  LOOPBACK: 'loopback',
  BRIDGE: 'bridge',
  BOND: 'bond',
  VLAN: 'vlan',
};

export const ALERT_LEVELS = {
  INFO: 'info',
  WARNING: 'warning',
  ERROR: 'error',
  CRITICAL: 'critical',
};

export const LOG_LEVELS = {
  DEBUG: 'debug',
  INFO: 'info',
  WARNING: 'warning',
  ERROR: 'error',
  CRITICAL: 'critical',
};

export const SYSTEM_SERVICES = [
  { name: 'smbd', display: 'Samba', description: 'SMB/CIFS file sharing service' },
  { name: 'nmbd', display: 'NetBIOS', description: 'NetBIOS name service' },
  { name: 'nfs-server', display: 'NFS Server', description: 'Network File System server' },
  { name: 'vsftpd', display: 'FTP Server', description: 'Very Secure FTP daemon' },
  { name: 'ssh', display: 'SSH', description: 'Secure Shell daemon' },
  { name: 'snmpd', display: 'SNMP', description: 'Simple Network Management Protocol daemon' },
  { name: 'rsync', display: 'Rsync', description: 'Remote synchronization daemon' },
];

export const TEMPERATURE_THRESHOLDS = {
  CPU: {
    WARNING: 70,
    CRITICAL: 80,
  },
  DISK: {
    WARNING: 50,
    CRITICAL: 60,
  },
};

export const USAGE_THRESHOLDS = {
  STORAGE: {
    WARNING: 80,
    CRITICAL: 90,
  },
  MEMORY: {
    WARNING: 85,
    CRITICAL: 95,
  },
  CPU: {
    WARNING: 80,
    CRITICAL: 90,
  },
};

export const DEFAULT_PORTS = {
  SSH: 22,
  FTP: 21,
  SFTP: 22,
  SMB: 445,
  NFS: 2049,
  HTTP: 80,
  HTTPS: 443,
  SNMP: 161,
  TELNET: 23,
};

export const REFRESH_INTERVALS = {
  FAST: 5000,    // 5 seconds
  NORMAL: 10000,  // 10 seconds
  SLOW: 30000,   // 30 seconds
  VERY_SLOW: 60000, // 1 minute
};

export const FILE_SYSTEMS = {
  EXT4: 'ext4',
  XFS: 'xfs',
  BTRFS: 'btrfs',
  ZFS: 'zfs',
  NTFS: 'ntfs',
  FAT32: 'fat32',
  EXFAT: 'exfat',
};

export const RAID_LEVELS = {
  RAID0: 'raid0',
  RAID1: 'raid1',
  RAID5: 'raid5',
  RAID6: 'raid6',
  RAID10: 'raid10',
};

export const BACKUP_TYPES = {
  FULL: 'full',
  INCREMENTAL: 'incremental',
  DIFFERENTIAL: 'differential',
  MIRROR: 'mirror',
};

export const BACKUP_STATUS = {
  IDLE: 'idle',
  RUNNING: 'running',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
};

export const NOTIFICATION_TYPES = {
  EMAIL: 'email',
  WEBHOOK: 'webhook',
  SNMP: 'snmp',
  SYSLOG: 'syslog',
};

export const TIME_ZONES = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Australia/Sydney',
];

export const LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'es', name: 'Español' },
  { code: 'fr', name: 'Français' },
  { code: 'de', name: 'Deutsch' },
  { code: 'it', name: 'Italiano' },
  { code: 'pt', name: 'Português' },
  { code: 'ru', name: 'Русский' },
  { code: 'zh', name: '中文' },
  { code: 'ja', name: '日本語' },
  { code: 'ko', name: '한국어' },
];

export const CHART_COLORS = [
  '#1976d2',
  '#dc004e',
  '#ed6c02',
  '#2e7d32',
  '#9c27b0',
  '#d32f2f',
  '#1565c0',
  '#c62828',
  '#ad1457',
  '#6a1b9a',
];

export const STATUS_COLORS = {
  success: '#4caf50',
  warning: '#ff9800',
  error: '#f44336',
  info: '#2196f3',
  default: '#9e9e9e',
};