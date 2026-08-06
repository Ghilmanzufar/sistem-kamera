import React, { useState, useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api/client';
import PageHeader from '../components/PageHeader';
import ConfirmModal from '../components/ConfirmModal';

export default function Rules() {
  const [minCoverage, setMinCoverage] = useState('');
  const [avgConf, setAvgConf] = useState('');
  const [minConf, setMinConf] = useState('');
  const [totalParts, setTotalParts] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  const fetchGlobalRule = async () => {
    setLoading(true);
    try {
      const res = await api.get('/api/admin/global-rule');
      if (res.data) {
        setAvgConf(Math.round((res.data.default_avg_conf || 0.75) * 100));
        setMinConf(Math.round((res.data.default_min_conf || 0.70) * 100));
        setMinCoverage(Math.round((res.data.default_min_coverage || 1.0) * 100));
        setTotalParts(res.data.total_parts || 0);
      }
    } catch (err) {
      toast.error('Gagal terhubung ke server saat memuat rule global');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGlobalRule();
  }, []);

  const handleConfirmSave = async () => {
    setShowConfirmModal(false);
    setSaving(true);

    try {
      const res = await api.post('/api/admin/global-rule', {
        default_avg_conf: parseFloat(avgConf) / 100,
        default_min_conf: parseFloat(minConf) / 100,
        default_min_coverage: parseFloat(minCoverage) / 100,
      });

      if (res.data && res.data.success) {
        toast.success('Global rule berhasil disimpan & diterapkan ke seluruh part!');
      } else {
        toast.error(res.data?.message || 'Gagal menyimpan global rule');
      }
    } catch (err) {
      toast.error('Gagal menyimpan rule: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <PageHeader
        title="Setting"
        highlightTitle="Global Rule"
        subtitle="Pengaturan parameter ambang batas inspeksi standar seluruh model part"
      />

      <div className="glass-card p-8 border border-white/10 rounded-3xl shadow-2xl backdrop-blur-xl">
        {loading ? (
          <div className="py-12 text-center text-slate-400 animate-pulse space-y-3">
            <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
            <p className="text-xs font-semibold">Memuat data setting global rule...</p>
          </div>
        ) : (
          <form onSubmit={(e) => { e.preventDefault(); setShowConfirmModal(true); }} className="space-y-6">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
                Target Kelengkapan Labelname (0 - 100%)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                required
                value={minCoverage}
                onChange={(e) => setMinCoverage(e.target.value)}
                className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-xl text-white font-mono text-lg focus:outline-none focus:border-amber-500 transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
                Target Avg Confidence Global (0 - 100%)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                required
                value={avgConf}
                onChange={(e) => setAvgConf(e.target.value)}
                className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-xl text-white font-mono text-lg focus:outline-none focus:border-amber-500 transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
                Target Min Confidence Komponen Global (0 - 100%)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                required
                value={minConf}
                onChange={(e) => setMinConf(e.target.value)}
                className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-xl text-white font-mono text-lg focus:outline-none focus:border-amber-500 transition-all"
              />
            </div>

            {/* Impact Summary Badge */}
            <div className="flex items-start gap-3 p-4 bg-amber-500/10 border border-amber-500/20 rounded-2xl text-amber-300 text-xs">
              <AlertTriangle className="w-5 h-5 shrink-0 text-amber-400 mt-0.5" />
              <div className="leading-relaxed">
                <span className="font-bold text-amber-400">Ringkasan Dampak Rule:</span>
                <p className="mt-0.5 text-slate-300">
                  ⚠️ Perubahan rule ini akan otomatis diterapkan & menimpa parameter standar pada <strong className="text-white underline">{totalParts} Part Number</strong> yang terdaftar di database.
                </p>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || saving}
              className="w-full py-4 px-6 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-xl shadow-lg shadow-amber-500/20 transition-all text-base disabled:opacity-50"
            >
              {saving ? 'Menyimpan...' : 'Simpan & Terapkan Global Rule'}
            </button>
          </form>
        )}
      </div>

      <ConfirmModal
        isOpen={showConfirmModal}
        title="⚠️ Peringatan Overwrite Global Rule"
        message={`Apakah Anda yakin ingin menimpa parameter standar pada ${totalParts} Part Number dengan rule baru ini?`}
        confirmText="Ya, Timpa Rule"
        isDanger={true}
        onConfirm={handleConfirmSave}
        onCancel={() => setShowConfirmModal(false)}
      />
    </div>
  );
}
