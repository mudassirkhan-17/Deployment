'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

interface User {
  username: string;
}

interface AuthContextType {
  user: User | null;
  isLoggedIn: boolean;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loading, setLoading] = useState(true); // Start as true while checking session

  // Load user from sessionStorage on mount (per-tab isolation)
  useEffect(() => {
    const storedUser = sessionStorage.getItem('user');
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
        setIsLoggedIn(true);
      } catch (error) {
        console.error('Failed to parse stored user:', error);
      }
    }
    setLoading(false); // Done checking session
  }, []);

  const getApiUrl = () => {
    if (typeof window !== 'undefined') {
      const isVercel = window.location.hostname !== 'localhost';
      return isVercel
        ? 'https://insurance-backend.duckdns.org'
        : 'http://localhost:8000';
    }
    return 'http://localhost:8000';
  };

  const login = async (username: string, password: string) => {
    setLoading(true);
    try {
      const apiUrl = getApiUrl();
      const formData = new FormData();
      formData.append('username', username);
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
      const userData = { username: data.username };

      setUser(userData);
      setIsLoggedIn(true);
      sessionStorage.setItem('user', JSON.stringify(userData));
    } catch (error: any) {
      throw new Error(error.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const register = async (username: string, password: string) => {
    setLoading(true);
    try {
      const apiUrl = getApiUrl();
      const formData = new FormData();
      formData.append('username', username);
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
      const userData = { username: data.username };

      setUser(userData);
      setIsLoggedIn(true);
      sessionStorage.setItem('user', JSON.stringify(userData));
    } catch (error: any) {
      throw new Error(error.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    setIsLoggedIn(false);
    sessionStorage.removeItem('user');
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
