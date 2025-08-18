import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';

import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeContextProvider, useThemeContext } from './context/ThemeContext';

import Navbar from './components/navigation/Navbar';
import Sidebar from './components/navigation/Sidebar';

import Dashboard from './pages/Dashboard';
import Storage from './pages/Storage';
import Shares from './pages/Shares';
import Network from './pages/Network';
import Users from './pages/Users';
import Services from './pages/Services';
import Settings from './pages/Settings';
import Login from './components/auth/Login';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      retryDelay: 1000,
      staleTime: 5 * 60 * 1000,
      cacheTime: 10 * 60 * 1000,
    },
  },
});

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return <Box display="flex" justifyContent="center" alignItems="center" height="100vh">Loading...</Box>;
  }
  
  return user ? children : <Navigate to="/login" replace />;
};

const AppContent = () => {
  const { user } = useAuth();
  const { darkMode } = useThemeContext();

  const theme = createTheme({
    palette: {
      mode: darkMode ? 'dark' : 'light',
      primary: {
        main: '#1976d2',
        dark: '#115293',
        light: '#42a5f5',
      },
      secondary: {
        main: '#dc004e',
      },
      background: {
        default: darkMode ? '#0a0e27' : '#f5f5f5',
        paper: darkMode ? '#1e2139' : '#ffffff',
      },
      text: {
        primary: darkMode ? '#ffffff' : '#000000',
        secondary: darkMode ? '#b0b3b8' : '#666666',
      },
    },
    typography: {
      fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
      h4: {
        fontWeight: 600,
      },
      h5: {
        fontWeight: 600,
      },
      h6: {
        fontWeight: 600,
      },
    },
    components: {
      MuiDrawer: {
        styleOverrides: {
          paper: {
            backgroundColor: darkMode ? '#1e2139' : '#ffffff',
            borderRight: `1px solid ${darkMode ? '#2a2d47' : '#e0e0e0'}`,
          },
        },
      },
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundColor: darkMode ? '#1e2139' : '#ffffff',
            color: darkMode ? '#ffffff' : '#000000',
            boxShadow: `0 1px 3px ${darkMode ? 'rgba(0,0,0,0.3)' : 'rgba(0,0,0,0.1)'}`,
          },
        },
      },
    },
  });

  if (!user) {
    return <Login />;
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', height: '100vh' }}>
        <Navbar />
        <Sidebar />
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            p: 3,
            mt: 8,
            ml: { sm: '240px' },
            backgroundColor: 'background.default',
            minHeight: '100vh',
          }}
        >
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/storage"
              element={
                <ProtectedRoute>
                  <Storage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/shares"
              element={
                <ProtectedRoute>
                  <Shares />
                </ProtectedRoute>
              }
            />
            <Route
              path="/network"
              element={
                <ProtectedRoute>
                  <Network />
                </ProtectedRoute>
              }
            />
            <Route
              path="/users"
              element={
                <ProtectedRoute>
                  <Users />
                </ProtectedRoute>
              }
            />
            <Route
              path="/services"
              element={
                <ProtectedRoute>
                  <Services />
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute>
                  <Settings />
                </ProtectedRoute>
              }
            />
          </Routes>
        </Box>
      </Box>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: darkMode ? '#1e2139' : '#ffffff',
            color: darkMode ? '#ffffff' : '#000000',
            border: `1px solid ${darkMode ? '#2a2d47' : '#e0e0e0'}`,
          },
        }}
      />
    </ThemeProvider>
  );
};

const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <ThemeContextProvider>
          <AuthProvider>
            <AppContent />
          </AuthProvider>
        </ThemeContextProvider>
      </Router>
    </QueryClientProvider>
  );
};

export default App;