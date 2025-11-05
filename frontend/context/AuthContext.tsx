'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

interface User {
  user_id: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  isLoggedIn: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loading, setLoading] = useState(false);

  // Load user from localStorage on mount
  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
        setIsLoggedIn(true);
      } catch (error) {
        console.error('Failed to parse stored user:', error);
      }
    }
  }, []);

  const getApiUrl = () => {
    if (typeof window !== 'undefined') {
      const isVercel = window.location.hostname !== 'localhost';
      return isVercel
        ? 'http://13.211.209.140:8000'
        : 'http://localhost:8000';
    }
    return 'http://localhost:8000';
  };

  const login = async (email: string, password: string) => {
    setLoading(true);
    try {
      const apiUrl = getApiUrl();
      const formData = new FormData();
      formData.append('email', email);
      formData.append('password', password);

      const response = await fetch(`${apiUrl}/login/`, {
        method: 'POST',
        body: formData,
        headers: {
          'ngrok-skip-browser-warning': 'true',
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Login failed');
      }

      const data = await response.json();
      const userData = { user_id: data.user_id, email: data.email };

      setUser(userData);
      setIsLoggedIn(true);
      localStorage.setItem('user', JSON.stringify(userData));
    } catch (error: any) {
      throw new Error(error.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const register = async (email: string, password: string) => {
    setLoading(true);
    try {
      const apiUrl = getApiUrl();
      const formData = new FormData();
      formData.append('email', email);
      formData.append('password', password);

      const response = await fetch(`${apiUrl}/register/`, {
        method: 'POST',
        body: formData,
        headers: {
          'ngrok-skip-browser-warning': 'true',
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Registration failed');
      }

      const data = await response.json();
      const userData = { user_id: data.user_id, email: data.email };

      setUser(userData);
      setIsLoggedIn(true);
      localStorage.setItem('user', JSON.stringify(userData));
    } catch (error: any) {
      throw new Error(error.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    setIsLoggedIn(false);
    localStorage.removeItem('user');
  };

  return (
    <AuthContext.Provider value={{ user, isLoggedIn, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
