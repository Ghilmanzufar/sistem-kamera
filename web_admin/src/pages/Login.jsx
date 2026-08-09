import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Camera, Lock, User as UserIcon, AlertCircle, HelpCircle } from 'lucide-react';
import api from '../api/client';

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('admin_token');
    const role = localStorage.getItem('user_role');
    if (token) {
      navigate(role === 'operator' ? '/history' : '/dashboard');
    }
  }, [navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await api.post('/api/admin-login', { username, password });
      if (res.data && res.data.token) {
        localStorage.setItem('admin_token', res.data.token);
        localStorage.setItem('user_role', res.data.role);
        localStorage.setItem('username', res.data.username);
        navigate(res.data.role === 'operator' ? '/history' : '/dashboard');
      }
    } catch (err) {
      if (err.response && err.response.data && err.response.data.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Gagal terhubung ke server FastAPI');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen app-bg-gradient flex items-center justify-center p-4 sm:p-6">
      <div className="w-full max-w-xl p-8 sm:p-12 glass-card border border-white/15 rounded-3xl shadow-2xl backdrop-blur-xl">
        <div className="text-center mb-8">
          <img
            src="LOGO_SUGITY.png"
            alt="Logo Sugity"
            className="h-20 w-auto mx-auto mb-4 object-contain drop-shadow-md"
          />
          <h1 className="text-3xl font-black text-white tracking-wide">
            Admin <span className="text-blue-500">Dashboard</span>
          </h1>
          <p className="text-sm text-slate-300 mt-1.5 font-medium">Sistem Inspeksi Kamera Produksi</p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-2xl bg-rose-500/15 border-2 border-rose-500/30 text-rose-300 text-sm font-medium flex items-center gap-3 shadow-lg shadow-rose-950/20">
            <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-bold tracking-wide text-slate-200 mb-2">
              Username
            </label>
            <div className="relative flex items-center">
              <UserIcon className="w-5 h-5 absolute left-4 text-slate-400" />
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Masukkan username"
                className="w-full pl-12 pr-4 py-3.5 sm:py-4 bg-slate-900/90 border-2 border-white/15 rounded-2xl text-white placeholder-slate-500 focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-400/30 transition-all text-sm sm:text-base font-sans"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-bold tracking-wide text-slate-200">
                PIN / Password
              </label>
              <Link
                to="/forgot-password"
                className="text-xs font-semibold text-blue-400 hover:text-blue-300 transition-colors flex items-center gap-1"
              >
                <HelpCircle className="w-3.5 h-3.5" />
                Lupa Password?
              </Link>
            </div>
            <div className="relative flex items-center">
              <Lock className="w-5 h-5 absolute left-4 text-slate-400" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Masukkan PIN / Password"
                className="w-full pl-12 pr-4 py-3.5 sm:py-4 bg-slate-900/90 border-2 border-white/15 rounded-2xl text-white placeholder-slate-500 focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-400/30 transition-all text-sm sm:text-base font-sans"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-4 px-6 bg-blue-600 hover:bg-blue-500 text-white font-extrabold rounded-2xl shadow-xl shadow-blue-600/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed text-sm sm:text-base cursor-pointer"
          >
            {loading ? 'Memproses...' : 'Masuk Dashboard →'}
          </button>
        </form>
      </div>
    </div>
  );
}
