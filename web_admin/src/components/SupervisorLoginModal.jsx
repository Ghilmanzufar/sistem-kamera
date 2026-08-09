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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="w-full max-w-md p-6 sm:p-8 glass-card shadow-2xl border border-white/10 rounded-3xl animate-scaleUp">
        {/* Header */}
        <div className="text-center mb-6">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-amber-500/20 to-orange-500/20 border border-amber-500/30 flex items-center justify-center mx-auto mb-3 text-amber-400 shadow-lg shadow-amber-500/10">
            <ShieldCheck className="w-6 h-6 text-amber-400" />
          </div>
          <h3 className="text-xl font-extrabold text-white tracking-wide">
            Login <span className="text-amber-400">Pengawas / Admin</span>
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Masukkan kredensial untuk membuka seluruh menu konfigurasi & manajemen
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-5 p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-center gap-2.5 text-rose-300 text-xs">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Username Input */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Username Pengawas / Admin</label>
            <div className="relative flex items-center">
              <User className="absolute left-3.5 w-4 h-4 text-slate-500" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Contoh: admin / pengawas"
                autoFocus
                className="w-full bg-slate-900/80 border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-500 outline-none focus:border-amber-500/60 focus:ring-1 focus:ring-amber-500/60 transition-all font-sans"
              />
            </div>
          </div>

          {/* Password Input */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">PIN / Password</label>
            <div className="relative flex items-center">
              <Lock className="absolute left-3.5 w-4 h-4 text-slate-500" />
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Masukkan PIN / Password"
                className="w-full bg-slate-900/80 border border-white/10 rounded-xl pl-10 pr-10 py-2.5 text-xs text-white placeholder-slate-500 outline-none focus:border-amber-500/60 focus:ring-1 focus:ring-amber-500/60 transition-all font-sans"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 text-slate-500 hover:text-slate-300 transition-colors"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-3">
            <button
              type="button"
              onClick={handleClose}
              disabled={loading}
              className="px-4 py-2.5 text-xs font-semibold text-slate-400 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 hover:text-white transition-all cursor-pointer"
            >
              Batal
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2.5 text-xs font-bold text-slate-950 bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-300 hover:to-amber-400 rounded-xl shadow-lg shadow-amber-500/20 transition-all cursor-pointer disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
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
