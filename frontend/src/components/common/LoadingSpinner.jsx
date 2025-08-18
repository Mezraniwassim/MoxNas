import React from 'react';
import { Box, CircularProgress, Typography } from '@mui/material';

const LoadingSpinner = ({ message = 'Loading...', size = 40, showMessage = true }) => {
  return (
    <Box
      display="flex"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      p={3}
    >
      <CircularProgress size={size} />
      {showMessage && (
        <Typography variant="body1" color="text.secondary" mt={2}>
          {message}
        </Typography>
      )}
    </Box>
  );
};

export default LoadingSpinner;