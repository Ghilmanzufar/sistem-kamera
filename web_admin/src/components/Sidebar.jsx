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
  LogOut,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import api from '../api/client';
import ConfirmModal from './ConfirmModal';

export default function Sidebar({ isCollapsed, setIsCollapsed }) {
  const navigate = useNavigate();
  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const username = localStorage.getItem('username') || 'Admin';
  const role = localStorage.getItem('user_role') || 'pengawas';

  const allNavItems = [
    { to: "/dashboard", label: "Live Dashboard", icon: LayoutDashboard, roles: ['admin', 'pengawas'] },
    { to: "/history", label: "History Inspeksi", icon: History, roles: ['admin', 'pengawas'] },
    { to: "/rules", label: "Setting Rule", icon: Sliders, roles: ['admin'] },
    { to: "/models", label: "Model AI (.pt)", icon: BrainCircuit, roles: ['admin'] },
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
      <aside 
        className={`fixed top-0 left-0 h-screen z-40 bg-slate-900/90 backdrop-blur-xl border-r border-white/10 transition-all duration-300 flex flex-col justify-between p-4 ${
          isCollapsed ? 'w-20' : 'w-64'
        }`}
      >
        {/* Top Header & Branding */}
        <div>
          <div className={`flex items-center pb-6 border-b border-white/10 mb-6 px-1 ${
            isCollapsed ? 'justify-center' : 'justify-between'
          }`}>
            <div className={`overflow-hidden ${isCollapsed ? 'hidden' : 'block'}`}>
              <h1 className="text-base font-bold text-white tracking-wide leading-tight truncate">
                Inspeksi <span className="text-blue-500">Kamera</span>
              </h1>
              <p className="text-[10px] text-slate-400 tracking-wider uppercase font-semibold">Admin System</p>
            </div>

            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="p-2 rounded-xl bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:bg-white/10 transition-all flex items-center justify-center shrink-0"
              title={isCollapsed ? "Buka Sidebar" : "Lipat Sidebar"}
            >
              {isCollapsed ? <ChevronRight className="w-5 h-5 text-blue-400" /> : <ChevronLeft className="w-4 h-4" />}
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1.5 overflow-y-auto max-h-[calc(100vh-230px)] pr-1 scrollbar-thin">
            {visibleNavItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  title={isCollapsed ? item.label : undefined}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3.5 py-3 rounded-xl text-xs font-semibold transition-all border ${
                      isActive
                        ? 'bg-blue-600 text-white border-blue-500 shadow-lg shadow-blue-600/30 font-bold'
                        : 'bg-transparent text-slate-400 border-transparent hover:bg-white/5 hover:text-slate-200'
                    } ${isCollapsed ? 'justify-center px-0' : ''}`
                  }
                >
                  <Icon className="w-5 h-5 shrink-0" />
                  {!isCollapsed && <span className="truncate">{item.label}</span>}
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Bottom User Info & Logout */}
        <div className="pt-4 border-t border-white/10 space-y-3">
          {!isCollapsed && (
            <div className="flex items-center justify-between px-2 py-1.5 rounded-xl bg-black/20 border border-white/5">
              <div className="truncate">
                <p className="text-xs font-semibold text-white truncate">{username}</p>
                <span className={`inline-block text-[9px] uppercase font-bold px-1.5 py-0.2 rounded ${
                  role === 'admin' ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                }`}>
                  {role}
                </span>
              </div>
              <button
                onClick={() => setShowLogoutModal(true)}
                className="p-2 text-rose-400 hover:text-white hover:bg-rose-500 rounded-lg transition-all"
                title="Keluar"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}

          {isCollapsed && (
            <button
              onClick={() => setShowLogoutModal(true)}
              className="w-full flex justify-center py-2.5 text-rose-400 hover:text-white hover:bg-rose-500/20 rounded-xl transition-all"
              title="Keluar"
            >
              <LogOut className="w-5 h-5" />
            </button>
          )}
        </div>
      </aside>

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
