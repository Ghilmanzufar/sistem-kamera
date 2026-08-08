import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';

import Sidebar from './components/Sidebar';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import History from './pages/History';
import Rules from './pages/Rules';
import Models from './pages/Models';
import Users from './pages/Users';
import Camera from './pages/Camera';
import SisonConfig from './pages/SisonConfig';
import Logs from './pages/Logs';
import { initTheme } from './utils/theme';

function isTokenValid(token) {
  if (!token) return false;
  try {
    const parts = token.split('.');
    if (parts.length !== 2) return true;
    const payloadB64 = parts[0];
    const padding = '='.repeat((4 - (payloadB64.length % 4)) % 4);
    const base64 = payloadB64.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = JSON.parse(atob(base64 + padding));
    if (jsonPayload.exp && Date.now() / 1000 > jsonPayload.exp) {
      localStorage.removeItem('admin_token');
      localStorage.removeItem('user_role');
      localStorage.removeItem('username');
      return false;
    }
    return true;
  } catch {
    return false;
  }
}

// Layout wrapper with Left Sidebar
function MainLayout() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const token = localStorage.getItem('admin_token');
  
  if (!token || !isTokenValid(token)) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen app-bg-gradient flex">
      {/* Left Sidebar */}
      <Sidebar isCollapsed={isCollapsed} setIsCollapsed={setIsCollapsed} />

      {/* Main Content Area */}
      <div className={`flex-1 transition-all duration-300 p-4 sm:p-6 lg:p-8 min-w-0 ${
        isCollapsed ? 'ml-20' : 'ml-64'
      }`}>
        <main className="w-full glass-container p-6 lg:p-10 shadow-2xl">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

// Protected Route for Pengawas / Admin Only
function PengawasOnlyRoute() {
  const rawRole = (localStorage.getItem('user_role') || 'pengawas').toLowerCase();
  if (rawRole === 'operator') {
    return <Navigate to="/history" replace />;
  }
  return <Outlet />;
}

function DefaultHomeRedirect() {
  const rawRole = (localStorage.getItem('user_role') || 'pengawas').toLowerCase();
  if (rawRole === 'operator') {
    return <Navigate to="/history" replace />;
  }
  return <Navigate to="/dashboard" replace />;
}

import ErrorBoundary from './components/ErrorBoundary';
import ErrorPage from './pages/ErrorPage';

export default function App() {
  useEffect(() => {
    initTheme();
  }, []);

  return (
    <ErrorBoundary>
      <BrowserRouter basename="/admin">
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: 'rgba(15, 23, 42, 0.9)',
              color: '#fff',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              backdropFilter: 'blur(12px)',
            },
          }}
        />
        <Routes>
          <Route path="/login" element={<Login />} />

          {/* Dedicated Error Information Page */}
          <Route path="/error" element={<ErrorPage />} />

          {/* Authenticated Layout */}
          <Route element={<MainLayout />}>
            <Route path="/" element={<DefaultHomeRedirect />} />
            
            {/* History Inspeksi bisa diakses oleh Pengawas & Operator */}
            <Route path="/history" element={<History />} />

            {/* Fitur & Halaman Pengawas (Full Access) */}
            <Route element={<PengawasOnlyRoute />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/camera" element={<Camera />} />
              <Route path="/sison-config" element={<SisonConfig />} />
              <Route path="/logs" element={<Logs />} />
              <Route path="/rules" element={<Rules />} />
              <Route path="/models" element={<Models />} />
              <Route path="/users" element={<Users />} />
            </Route>

            {/* 404 Inside Layout */}
            <Route path="*" element={<ErrorPage type="404" />} />
          </Route>

          {/* Global Fallback Route */}
          <Route path="*" element={<ErrorPage type="404" />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
