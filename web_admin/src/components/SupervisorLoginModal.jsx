import React, { useState } from 'react';
import { Lock, User, Eye, EyeOff, AlertCircle, Loader2, ShieldCheck } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api/client';

export default function SupervisorLoginModal({ isOpen, onClose, onSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError('Username dan PIN / Password wajib diisi!');
      return;
    }

    setError('');
    setLoading(true);

    try {
      const res = await api.post('/api/admin-login', { username: username.trim(), password: password.trim() });
      if (res.data && res.data.token) {
        const role = (res.data.role || '').toLowerCase();
        if (role === 'operator') {
          setError('Akun ini adalah Operator. Masukkan akun Pengawas atau Admin!');
          return;
        }

        // Simpan token pengawas
        localStorage.setItem('admin_token', res.data.token);
        localStorage.setItem('user_role', res.data.role);
        localStorage.setItem('username', res.data.username);

        toast.success(`Berhasil masuk sebagai ${role === 'admin' ? 'Super Admin' : 'Pengawas'}`);
        setUsername('');
        setPassword('');
        if (onSuccess) onSuccess(res.data);
      }
    } catch (err) {
      if (err.response && err.response.data && err.response.data.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Gagal login: Periksa koneksi ke server.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setError('');
    setUsername('');
    setPassword('');
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/85 backdrop-blur-lg animate-fadeIn">
      <div className="w-full max-w-xl p-8 sm:p-12 glass-card shadow-2xl border border-white/15 rounded-3xl animate-scaleUp">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-3xl bg-gradient-to-tr from-amber-500/20 to-orange-500/20 border-2 border-amber-500/40 flex items-center justify-center mx-auto mb-4 text-amber-400 shadow-xl shadow-amber-500/15">
            <ShieldCheck className="w-9 h-9 text-amber-400" />
          </div>
          <h3 className="text-2xl sm:text-3xl font-black text-white tracking-wide">
            Login <span className="text-amber-400">Pengawas / Admin</span>
          </h3>
          <p className="text-sm text-slate-300 mt-2 max-w-md mx-auto leading-relaxed">
            Masukkan kredensial pengawas atau admin untuk membuka akses ke seluruh menu konfigurasi & manajemen sistem
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-4 bg-rose-500/15 border-2 border-rose-500/40 rounded-2xl flex items-center gap-3 text-rose-200 text-sm font-medium shadow-lg shadow-rose-950/30">
            <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Username Input */}
          <div>
            <label className="block text-sm font-bold text-slate-200 mb-2">Username Pengawas / Admin</label>
            <div className="relative flex items-center">
              <User className="absolute left-4 w-5 h-5 text-slate-400" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Masukkan username (contoh: admin)"
                autoFocus
                className="w-full bg-slate-900/90 border-2 border-white/15 rounded-2xl pl-12 pr-4 py-3.5 sm:py-4 text-sm sm:text-base text-white placeholder-slate-500 outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-400/30 transition-all font-sans"
              />
            </div>
          </div>

          {/* Password Input */}
          <div>
            <label className="block text-sm font-bold text-slate-200 mb-2">PIN / Password</label>
            <div className="relative flex items-center">
              <Lock className="absolute left-4 w-5 h-5 text-slate-400" />
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Masukkan PIN / Password"
                className="w-full bg-slate-900/90 border-2 border-white/15 rounded-2xl pl-12 pr-12 py-3.5 sm:py-4 text-sm sm:text-base text-white placeholder-slate-500 outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-400/30 transition-all font-sans"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 text-slate-400 hover:text-white transition-colors cursor-pointer p-1"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-4 pt-4 border-t border-white/10">
            <button
              type="button"
              onClick={handleClose}
              disabled={loading}
              className="px-6 py-3.5 text-sm font-bold text-slate-300 bg-white/5 border border-white/15 rounded-2xl hover:bg-white/10 hover:text-white transition-all cursor-pointer"
            >
              Batal
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center justify-center gap-2.5 px-8 py-3.5 text-sm sm:text-base font-extrabold text-slate-950 bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-300 hover:to-amber-400 rounded-2xl shadow-xl shadow-amber-500/25 transition-all cursor-pointer disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Memverifikasi...</span>
                </>
              ) : (
                <span>Masuk Pengawas →</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
