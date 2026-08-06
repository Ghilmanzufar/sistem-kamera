import React, { useState, useEffect } from 'react';
import { Settings, Save, ShieldCheck } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api/client';
import PageHeader from '../components/PageHeader';

export default function SisonConfig() {
  const [callbackUrl, setCallbackUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchSisonConfig = async () => {
    try {
      const res = await api.get('/api/admin/sison-config');
      if (res.data) {
        setCallbackUrl(res.data.callback_url || '');
        setApiKey(res.data.api_key || '');
      }
    } catch (err) {
      toast.error('Gagal memuat konfigurasi Sison');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSisonConfig();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);

    try {
      await api.put('/api/admin/sison-config', {
        callback_url: callbackUrl,
        api_key: apiKey,
      });
      toast.success('Konfigurasi integrasi Sison berhasil disimpan!');
    } catch (err) {
      toast.error('Gagal menyimpan konfigurasi Sison');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <PageHeader
        title="Konfigurasi"
        highlightTitle="Integrasi Sison"
        subtitle="Pengaturan URL Webhook Callback dan Token Kredensial Sistem Sison Pabrik"
      />

      <div className="glass-card p-8 border border-white/10 rounded-3xl shadow-2xl backdrop-blur-xl">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
              Callback Webhook URL (Tujuan Kirim Hasil Inspeksi)
            </label>
            <input
              type="text"
              required
              value={callbackUrl}
              onChange={(e) => setCallbackUrl(e.target.value)}
              placeholder="http://192.168.1.50:8000/api/inspection/result"
              className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-xl text-white font-mono text-sm focus:outline-none focus:border-blue-500 transition-all"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
              API Security Key / Authorization Bearer Token
            </label>
            <div className="relative">
              <input
                type="password"
                required
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sugity_sison_secret_key"
                className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-xl text-white font-mono text-sm focus:outline-none focus:border-blue-500 transition-all"
              />
              <ShieldCheck className="w-5 h-5 absolute right-3.5 top-1/2 -translate-y-1/2 text-emerald-400" />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || saving}
            className="w-full flex items-center justify-center gap-2 py-3.5 px-6 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl shadow-lg shadow-blue-600/30 transition-all text-sm disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Menyimpan...' : 'Simpan Konfigurasi Sison'}
          </button>
        </form>
      </div>
    </div>
  );
}
