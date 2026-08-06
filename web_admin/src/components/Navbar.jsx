import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, 
  History, 
  Sliders, 
  BrainCircuit, 
  AlertTriangle, 
  Users, 
  Camera, 
  Settings, 
  FileText, 
  LogOut 
} from 'lucide-react';
import api from '../api/client';
import ConfirmModal from './ConfirmModal';

export default function Navbar() {
  const navigate = useNavigate();
  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const username = localStorage.getItem('username') || 'Admin';
  const role = localStorage.getItem('user_role') || 'pengawas';

  const allNavItems = [
    { to: "/dashboard", label: "Live Dashboard", icon: LayoutDashboard, roles: ['admin', 'pengawas'] },
    { to: "/history", label: "History Inspeksi", icon: History, roles: ['admin', 'pengawas'] },
    { to: "/rules", label: "Setting Rule", icon: Sliders, roles: ['admin'] },
    { to: "/models", label: "Model AI", icon: BrainCircuit, roles: ['admin'] },
    { to: "/ng-history", label: "History NG", icon: AlertTriangle, roles: ['admin', 'pengawas'] },
    { to: "/users", label: "User & PIN", icon: Users, roles: ['admin'] },
    { to: "/camera", label: "Kamera", icon: Camera, roles: ['admin', 'pengawas'] },
    { to: "/sison-config", label: "Config Sison", icon: Settings, roles: ['admin', 'pengawas'] },
    { to: "/logs", label: "Audit Logs", icon: FileText, roles: ['admin', 'pengawas'] },
  ];

  const visibleNavItems = allNavItems.filter(item => item.roles.includes(role));

  const handleLogout = async () => {
    try {
      await api.post('/api/admin/logout');
    } catch (e) {
      console.warn("Logout log fail", e);
    }
    localStorage.removeItem('admin_token');
    localStorage.removeItem('user_role');
    localStorage.removeItem('username');
    navigate('/login');
  };

  return (
    <>
      <header className="mb-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between py-4 px-6 mb-6 glass-card rounded-2xl border border-white/10 gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-blue-600/20 border border-blue-500/30 text-blue-400">
              <Camera className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-wide">
                Inspeksi Kamera <span className="text-blue-500">Admin</span>
              </h1>
              <p className="text-xs text-slate-400">System Monitoring & Operational Portal</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right hidden sm:block">
              <p className="text-sm font-semibold text-white">{username}</p>
              <span className={`inline-block text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                role === 'admin' ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
              }`}>
                {role}
              </span>
            </div>
            <button
              onClick={() => setShowLogoutModal(true)}
              className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-xl hover:bg-rose-500 hover:text-white transition-all"
            >
              <LogOut className="w-4 h-4" />
              Keluar
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <nav className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
          {visibleNavItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all border ${
                    isActive
                      ? 'bg-blue-600 text-white border-blue-500 shadow-lg shadow-blue-600/30'
                      : 'bg-white/5 text-slate-300 border-white/10 hover:bg-white/10 hover:text-white'
                  }`
                }
              >
                <Icon className="w-4 h-4" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
      </header>

      <ConfirmModal
        isOpen={showLogoutModal}
        title="Konfirmasi Keluar"
        message="Apakah Anda yakin ingin keluar dari Admin Dashboard?"
        confirmText="Keluar"
        isDanger={true}
        onConfirm={handleLogout}
        onCancel={() => setShowLogoutModal(false)}
      />
    </>
  );
}
