import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Alert,
  AlertTitle,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({
      error: error,
      errorInfo: errorInfo,
    });

    if (process.env.NODE_ENV === 'development') {
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    }

    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    
    if (this.props.onRetry) {
      this.props.onRetry();
    }
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          minHeight="400px"
          p={3}
        >
          <Paper
            elevation={3}
            sx={{
              p: 4,
              maxWidth: 600,
              width: '100%',
              textAlign: 'center',
            }}
          >
            <ErrorIcon color="error" sx={{ fontSize: 64, mb: 2 }} />
            
            <Typography variant="h5" gutterBottom color="error">
              {this.props.title || 'Something went wrong'}
            </Typography>
            
            <Typography variant="body1" color="text.secondary" paragraph>
              {this.props.message || 
                'An unexpected error occurred. Please try refreshing the page or contact support if the problem persists.'}
            </Typography>

            <Box display="flex" justifyContent="center" gap={2} mb={3}>
              <Button
                variant="contained"
                startIcon={<RefreshIcon />}
                onClick={this.handleRetry}
              >
                Try Again
              </Button>
              
              {this.props.showReloadButton && (
                <Button
                  variant="outlined"
                  onClick={() => window.location.reload()}
                >
                  Reload Page
                </Button>
              )}
            </Box>

            {(this.state.error || this.state.errorInfo) && 
             (this.props.showErrorDetails || process.env.NODE_ENV === 'development') && (
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography variant="subtitle2">Error Details</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Box textAlign="left">
                    {this.state.error && (
                      <Alert severity="error" sx={{ mb: 2 }}>
                        <AlertTitle>Error Message</AlertTitle>
                        <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                          {this.state.error.toString()}
                        </Typography>
                      </Alert>
                    )}
                    
                    {this.state.errorInfo && this.state.errorInfo.componentStack && (
                      <Alert severity="info">
                        <AlertTitle>Component Stack</AlertTitle>
                        <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', fontSize: '0.75rem' }}>
                          {this.state.errorInfo.componentStack}
                        </Typography>
                      </Alert>
                    )}
                  </Box>
                </AccordionDetails>
              </Accordion>
            )}
          </Paper>
        </Box>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;