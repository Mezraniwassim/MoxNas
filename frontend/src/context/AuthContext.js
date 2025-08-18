import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';
import Cookies from 'js-cookie';
import toast from 'react-hot-toast';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const token = Cookies.get('sessionid');
      if (!token) {
        setLoading(false);
        return;
      }

      const response = await axios.get('/api/auth/user/', {
        withCredentials: true,
      });
      
      setUser(response.data);
    } catch (error) {
      console.error('Auth check failed:', error);
      Cookies.remove('sessionid');
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    try {
      setLoading(true);
      
      const csrfResponse = await axios.get('/api/auth/csrf/');
      const csrfToken = csrfResponse.data.csrfToken;
      
      const response = await axios.post(
        '/api/auth/login/',
        { username, password },
        {
          headers: {
            'X-CSRFToken': csrfToken,
          },
          withCredentials: true,
        }
      );

      if (response.status === 200) {
        setUser(response.data.user);
        toast.success('Login successful');
        return { success: true };
      }
    } catch (error) {
      console.error('Login failed:', error);
      const message = error.response?.data?.error || 'Login failed';
      toast.error(message);
      return { success: false, error: message };
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      await axios.post('/api/auth/logout/', {}, {
        withCredentials: true,
      });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setUser(null);
      Cookies.remove('sessionid');
      toast.success('Logged out successfully');
    }
  };

  const value = {
    user,
    loading,
    login,
    logout,
    checkAuth,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};