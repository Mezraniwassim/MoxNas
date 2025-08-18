import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Box,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Folder as FolderIcon,
  Share as ShareIcon
} from '@mui/icons-material';

const Shares = () => {
  const [shares, setShares] = useState([]);

  useEffect(() => {
    fetchShares();
  }, []);

  const fetchShares = async () => {
    // Mock data - replace with actual API call
    setShares([
      {
        id: 1,
        name: 'Documents',
        path: '/tank/documents',
        type: 'SMB',
        enabled: true,
        readonly: false,
        guest_access: false
      },
      {
        id: 2,
        name: 'Media',
        path: '/tank/media',
        type: 'NFS',
        enabled: true,
        readonly: true,
        guest_access: true
      },
      {
        id: 3,
        name: 'Backup',
        path: '/tank/backup',
        type: 'FTP',
        enabled: false,
        readonly: false,
        guest_access: false
      }
    ]);
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'SMB':
        return <ShareIcon />;
      case 'NFS':
        return <FolderIcon />;
      case 'FTP':
        return <ShareIcon />;
      default:
        return <ShareIcon />;
    }
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">File Shares</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
        >
          Create Share
        </Button>
      </Box>

      <Paper sx={{ p: 2 }}>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Path</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Access</TableCell>
                <TableCell>Guest Access</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {shares.map((share) => (
                <TableRow key={share.id}>
                  <TableCell>
                    <Box display="flex" alignItems="center">
                      {getTypeIcon(share.type)}
                      <Box ml={1}>{share.name}</Box>
                    </Box>
                  </TableCell>
                  <TableCell>{share.path}</TableCell>
                  <TableCell>
                    <Chip
                      label={share.type}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={share.enabled ? 'Enabled' : 'Disabled'}
                      color={share.enabled ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={share.readonly ? 'Read-only' : 'Read/Write'}
                      color={share.readonly ? 'warning' : 'primary'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={share.guest_access ? 'Allowed' : 'Not Allowed'}
                      color={share.guest_access ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <IconButton size="small" color="primary">
                      <EditIcon />
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
      </Paper>
    </Container>
  );
};

export default Shares;