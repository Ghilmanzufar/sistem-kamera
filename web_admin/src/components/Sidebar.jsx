import React, { useState, useEffect } from 'react';
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
  Activity, 
  LogOut,
  ChevronLeft,
  ChevronRight,
  Sun,
  Moon
} from 'lucide-react';
import api from '../api/client';
import ConfirmModal from './ConfirmModal';
import { getStoredTheme, toggleTheme } from '../utils/theme';

export default function Sidebar({ isCollapsed, setIsCollapsed }) {
  const navigate = useNavigate();
  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [themeMode, setThemeMode] = useState(getStoredTheme());
  const username = localStorage.getItem('username') || 'Admin';
  
  const rawRole = (localStorage.getItem('user_role') || 'pengawas').toLowerCase();
  const effectiveRole = (rawRole === 'admin' || rawRole === 'pengawas') ? 'pengawas' : rawRole;

  useEffect(() => {
    setThemeMode(getStoredTheme());
  }, []);

  const handleThemeToggle = () => {
    const next = toggleTheme();
    setThemeMode(next);
  };

  const allNavItems = [
    { to: "/dashboard", label: "Live Dashboard", icon: LayoutDashboard, roles: ['pengawas', 'admin'] },
    { to: "/history", label: "History Inspeksi", icon: History, roles: ['pengawas', 'admin', 'operator'] },
    { to: "/camera", label: "Kamera Manajemen", icon: Camera, roles: ['pengawas', 'admin'] },
    { to: "/models", label: "Model AI", icon: BrainCircuit, roles: ['pengawas', 'admin'] },
    { to: "/rules", label: "Setting Rule", icon: Sliders, roles: ['pengawas', 'admin'] },
    { to: "/users", label: "User Manajemen", icon: Users, roles: ['pengawas', 'admin'] },
    { to: "/sison-config", label: "Config Sison", icon: Settings, roles: ['pengawas', 'admin'] },
    { to: "/system-health", label: "Status Sistem", icon: Activity, roles: ['pengawas', 'admin'] },
    { to: "/logs", label: "Audit Logs", icon: FileText, roles: ['pengawas', 'admin'] },
  ];

  const visibleNavItems = allNavItems.filter(item => 
    item.roles.includes(rawRole) || item.roles.includes(effectiveRole)
  );

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
        {/* Top Header & Branding with Logo on Top */}
        <div>
          <div className={`flex pb-5 border-b border-white/10 mb-6 px-1 ${
            isCollapsed ? 'flex-col items-center gap-3 justify-center' : 'items-center justify-between'
          }`}>
            <div className={`flex flex-col items-center gap-2 overflow-hidden ${isCollapsed ? 'justify-center' : 'flex-1'}`}>
              <img
                src="LOGO_SUGITY.png"
                alt="Logo Sugity"
                className={`w-auto object-contain drop-shadow-md transition-all ${
                  isCollapsed ? 'h-7' : 'h-10 mx-auto'
                }`}
              />
              {!isCollapsed && (
                <h1 className="text-sm font-extrabold text-white tracking-wide text-center leading-tight">
                  Kamera <span className="text-blue-500">Inspeksi</span>
                </h1>
              )}
            </div>

            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className={`p-1.5 rounded-xl bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:bg-white/10 transition-all flex items-center justify-center shrink-0 cursor-pointer ${
                isCollapsed ? '' : 'self-start'
              }`}
              title={isCollapsed ? "Buka Sidebar" : "Lipat Sidebar"}
            >
              {isCollapsed ? <ChevronRight className="w-4 h-4 text-blue-400" /> : <ChevronLeft className="w-4 h-4" />}
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

        {/* Bottom User Info, Theme Switcher & Logout */}
        <div className="pt-4 border-t border-white/10 space-y-3">
          {!isCollapsed && (
            <div className="flex items-center justify-between px-2 py-1.5 rounded-xl bg-black/20 border border-white/5">
              <div className="truncate">
                <p className="text-xs font-semibold text-white truncate">{username}</p>
                <span className={`inline-block text-[9px] uppercase font-bold px-1.5 py-0.5 rounded ${
                  effectiveRole === 'pengawas' ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30' : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                }`}>
                  {rawRole}
                </span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={handleThemeToggle}
                  className="p-2 text-amber-400 hover:text-amber-300 hover:bg-amber-500/10 rounded-lg transition-all"
                  title={themeMode === 'light' ? 'Ganti ke Mode Gelap' : 'Ganti ke Mode Terang'}
                >
                  {themeMode === 'light' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
                </button>
                <button
                  onClick={() => setShowLogoutModal(true)}
                  className="p-2 text-rose-400 hover:text-white hover:bg-rose-500 rounded-lg transition-all"
                  title="Keluar"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {isCollapsed && (
            <div className="space-y-2">
              <button
                onClick={handleThemeToggle}
                className="w-full flex justify-center py-2.5 text-amber-400 hover:text-amber-300 hover:bg-amber-500/10 rounded-xl transition-all"
                title={themeMode === 'light' ? 'Ganti ke Mode Gelap' : 'Ganti ke Mode Terang'}
              >
                {themeMode === 'light' ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
              </button>
              <button
                onClick={() => setShowLogoutModal(true)}
                className="w-full flex justify-center py-2.5 text-rose-400 hover:text-white hover:bg-rose-500/20 rounded-xl transition-all"
                title="Keluar"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </div>
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
