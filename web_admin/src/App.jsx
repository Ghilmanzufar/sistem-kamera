import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';

import Sidebar from './components/Sidebar';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import History from './pages/History';
import Rules from './pages/Rules';
import Models from './pages/Models';
import NgHistory from './pages/NgHistory';
import Users from './pages/Users';
import Camera from './pages/Camera';
import SisonConfig from './pages/SisonConfig';
import Logs from './pages/Logs';

// Layout wrapper with Left Sidebar
function MainLayout() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const token = localStorage.getItem('admin_token');
  
  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-slate-100 flex">
      {/* Left Sidebar */}
      <Sidebar isCollapsed={isCollapsed} setIsCollapsed={setIsCollapsed} />

      {/* Main Content Area */}
      <div className={`flex-1 transition-all duration-300 p-6 lg:p-8 min-w-0 ${
        isCollapsed ? 'ml-20' : 'ml-64'
      }`}>
        <main className="max-w-7xl mx-auto glass-container p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

// Protected Route for Admin Only
function AdminOnlyRoute() {
  const role = localStorage.getItem('user_role') || 'pengawas';
  if (role !== 'admin') {
    return <Navigate to="/dashboard" replace />;
  }
  return <Outlet />;
}

export default function App() {
  return (
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

        {/* Authenticated Layout */}
        <Route element={<MainLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/history" element={<History />} />
          <Route path="/ng-history" element={<NgHistory />} />
          <Route path="/camera" element={<Camera />} />
          <Route path="/sison-config" element={<SisonConfig />} />
          <Route path="/logs" element={<Logs />} />

          {/* Admin Only Pages */}
          <Route element={<AdminOnlyRoute />}>
            <Route path="/rules" element={<Rules />} />
            <Route path="/models" element={<Models />} />
            <Route path="/users" element={<Users />} />
          </Route>
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
