import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  HardDrive, 
  Database, 
  Cpu, 
  Wifi, 
  RefreshCw, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  Copy, 
  Server, 
  ShieldCheck, 
  Layers,
  Zap
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api/client';
import PageHeader from '../components/PageHeader';

export default function SystemHealth() {
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchHealth = async (isManual = false) => {
    if (isManual) setRefreshing(true);
    try {
      const res = await api.get('/api/health');
      setHealthData(res.data);
    } catch (err) {
      toast.error('Gagal mengambil data telemetri sistem');
    } finally {
      setLoading(false);
      if (isManual) setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(() => {
      fetchHealth();
    }, 5000); // Auto-refresh setiap 5 detik
    return () => clearInterval(interval);
  }, []);

  const copyHealthUrl = () => {
    const url = `${window.location.origin}/api/health`;
    navigator.clipboard.writeText(url);
    toast.success('Endpoint URL disalin ke clipboard!');
  };

  if (loading && !healthData) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[450px] space-y-4">
        <RefreshCw className="w-10 h-10 text-blue-400 animate-spin" />
        <p className="text-sm font-semibold text-slate-300">Memuat telemetri & status sistem...</p>
      </div>
    );
  }

  const disk = healthData?.disk_storage || {};
  const db = healthData?.database || {};
  const engine = healthData?.inspection_engine || {};
  const uptime = healthData?.uptime || {};
  const isHealthy = healthData?.status === 'HEALTHY';
  const isDiskWarning = disk.is_low_space_warning;

  return (
    <div className="space-y-6 animate-fadeIn">
      <PageHeader
        title="Status"
        highlightTitle="Sistem & Telemetri"
        subtitle="Monitoring observabilitas real-time kesehatan hardware, penyimpanan disk, database, dan engine AI"
        actionButton={
          <button
            onClick={() => fetchHealth(true)}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 font-semibold text-sm rounded-xl transition-all disabled:opacity-50 cursor-pointer"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh Status
          </button>
        }
      />

      {/* Low Disk Space Alert Banner */}
      {isDiskWarning && (
        <div className="p-4 bg-rose-500/15 border border-rose-500/30 rounded-2xl flex items-start gap-3.5 text-rose-200">
          <AlertTriangle className="w-6 h-6 text-rose-400 shrink-0 mt-0.5 animate-bounce" />
          <div className="space-y-1">
            <h4 className="font-bold text-sm text-white">⚠️ Peringatan: Kapasitas Harddisk Kritis (&lt; 10% Tersisa)!</h4>
            <p className="text-xs text-rose-200/90 leading-relaxed">
              Sisa ruang penyimpanan hanya <strong>{disk.free_gb} GB ({disk.free_percent}%)</strong>. 
              Sistem telah dilengkapi pembersihan otomatis foto NG lama (&gt; 30 hari), namun disarankan untuk segera melakukan backup data atau menambah kapasitas disk agar proses inspeksi tidak terhenti.
            </p>
          </div>
        </div>
      )}

      {/* Main Status Overview Banner */}
      <div className="glass-card p-6 border border-white/10 rounded-2xl grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Status System Badge */}
        <div className="flex items-center gap-4 p-4 bg-black/30 border border-white/5 rounded-xl">
          <div className={`p-3 rounded-xl border ${
            isHealthy 
              ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-400' 
              : 'bg-amber-500/20 border-amber-500/30 text-amber-400'
          }`}>
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs uppercase font-bold text-slate-400 block tracking-wider">Kondisi Sistem</span>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`w-2.5 h-2.5 rounded-full ${isHealthy ? 'bg-emerald-400 animate-ping' : 'bg-amber-400 animate-ping'}`}></span>
              <span className={`text-lg font-black tracking-wide ${isHealthy ? 'text-emerald-400' : 'text-amber-400'}`}>
                {healthData?.status || 'UNKNOWN'}
              </span>
            </div>
          </div>
        </div>

        {/* Uptime Badge */}
        <div className="flex items-center gap-4 p-4 bg-black/30 border border-white/5 rounded-xl">
          <div className="p-3 bg-blue-500/20 border border-blue-500/30 rounded-xl text-blue-400">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs uppercase font-bold text-slate-400 block tracking-wider">Uptime Server</span>
            <span className="text-lg font-black text-white tracking-wide font-mono mt-0.5 block">
              {uptime.human || '0s'}
            </span>
          </div>
        </div>

        {/* Database Status Badge */}
        <div className="flex items-center gap-4 p-4 bg-black/30 border border-white/5 rounded-xl">
          <div className="p-3 bg-purple-500/20 border border-purple-500/30 rounded-xl text-purple-400">
            <Database className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs uppercase font-bold text-slate-400 block tracking-wider">Database & Buffer</span>
            <span className="text-lg font-black text-emerald-400 tracking-wide mt-0.5 block font-mono">
              {db.status === 'CONNECTED' ? `Online (${db.latency_ms}ms)` : 'Offline'}
            </span>
          </div>
        </div>

        {/* Local Network Info */}
        <div className="flex items-center gap-4 p-4 bg-black/30 border border-white/5 rounded-xl">
          <div className="p-3 bg-cyan-500/20 border border-cyan-500/30 rounded-xl text-cyan-400">
            <Wifi className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs uppercase font-bold text-slate-400 block tracking-wider">IP Host Kamera</span>
            <span className="text-base font-black text-slate-200 tracking-wide font-mono mt-0.5 block">
              {healthData?.network?.local_ip}:{healthData?.network?.port}
            </span>
          </div>
        </div>
      </div>

      {/* Grid Telemetri Detail */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* 1. Storage & Harddisk Space Card */}
        <div className="glass-card p-6 border border-white/10 rounded-2xl space-y-5">
          <div className="flex items-center justify-between pb-4 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-amber-500/20 border border-amber-500/30 rounded-xl text-amber-400">
                <HardDrive className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-white text-base">Penyimpanan Harddisk (Storage Guard)</h3>
                <p className="text-xs text-slate-400">Monitoring kapasitas drive untuk foto rekaman NG & model AI</p>
              </div>
            </div>
            <span className={`px-2.5 py-1 rounded-full text-xs font-bold font-mono border ${
              isDiskWarning 
                ? 'bg-rose-500/20 text-rose-300 border-rose-500/30' 
                : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
            }`}>
              {disk.free_percent}% Tersedia
            </span>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-xs font-mono font-semibold text-slate-300">
              <span>Terpakai: {disk.used_gb} GB ({disk.used_percent}%)</span>
              <span>Sisa: {disk.free_gb} GB ({disk.free_percent}%)</span>
            </div>
            {/* Visual Progress Bar */}
            <div className="w-full h-3.5 bg-black/40 border border-white/10 rounded-full overflow-hidden p-0.5">
              <div 
                className={`h-full rounded-full transition-all duration-500 ${
                  disk.used_percent > 90 
                    ? 'bg-rose-500 shadow-lg shadow-rose-500/50' 
                    : disk.used_percent > 75 
                    ? 'bg-amber-500' 
                    : 'bg-blue-500'
                }`}
                style={{ width: `${Math.min(100, Math.max(0, disk.used_percent || 0))}%` }}
              ></div>
            </div>
            <div className="flex justify-between text-[11px] text-slate-400 pt-1">
              <span>Total Kapasitas: <strong className="text-white font-mono">{disk.total_gb} GB</strong></span>
              <span>Batas Peringatan Kritis: &lt; 10%</span>
            </div>
          </div>

          <div className="p-3.5 bg-white/5 border border-white/5 rounded-xl text-xs space-y-1.5">
            <div className="flex items-center gap-2 font-semibold text-slate-200">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Otomatisasi Pembersihan (Cleanup 30 Hari) Aktif</span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Foto bukti NG yang berumur lebih dari 30 hari akan dihapus secara otomatis setiap 24 jam sekali di background.
            </p>
          </div>
        </div>

        {/* 2. Database & Offline Buffer Resiliency Card */}
        <div className="glass-card p-6 border border-white/10 rounded-2xl space-y-5">
          <div className="flex items-center justify-between pb-4 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-purple-500/20 border border-purple-500/30 rounded-xl text-purple-400">
                <Database className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-white text-base">Database & Offline Buffer</h3>
                <p className="text-xs text-slate-400">Keandalan penyimpanan PostgreSQL & antrean fallback SQLite</p>
              </div>
            </div>
            <span className="px-2.5 py-1 rounded-full text-xs font-bold font-mono bg-purple-500/20 text-purple-300 border border-purple-500/30">
              Zero Data Loss
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-black/30 border border-white/5 rounded-xl">
              <span className="text-xs font-semibold text-slate-400 block mb-1">Status PostgreSQL</span>
              <span className="text-base font-bold text-emerald-400 flex items-center gap-2 font-mono">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                {db.status}
              </span>
              <span className="text-[11px] text-slate-400 font-mono mt-1 block">Latensi Query: {db.latency_ms} ms</span>
            </div>

            <div className="p-4 bg-black/30 border border-white/5 rounded-xl">
              <span className="text-xs font-semibold text-slate-400 block mb-1">Offline Buffer Queue</span>
              <span className="text-base font-bold text-white font-mono">
                {db.offline_buffer_unsynced_count} Antrean
              </span>
              <span className="text-[11px] text-slate-400 font-sans mt-1 block">
                {db.offline_buffer_unsynced_count === 0 ? '✅ Semua log tersinkronisasi' : '⏳ Menunggu auto-flush ke DB'}
              </span>
            </div>
          </div>

          <div className="p-3.5 bg-white/5 border border-white/5 rounded-xl text-xs space-y-1.5">
            <div className="flex items-center gap-2 font-semibold text-slate-200">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Proteksi Failover SQLite Lokal</span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Jika service PostgreSQL terhenti, seluruh log hasil inspeksi (OK/NG) otomatis disimpan ke disk lokal dan di-flush otomatis saat DB pulih.
            </p>
          </div>
        </div>

        {/* 3. AI & Vision Pipeline Engine Card */}
        <div className="glass-card p-6 border border-white/10 rounded-2xl space-y-5">
          <div className="flex items-center justify-between pb-4 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-emerald-500/20 border border-emerald-500/30 rounded-xl text-emerald-400">
                <Cpu className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-white text-base">Pipeline Inspeksi & AI Engine</h3>
                <p className="text-xs text-slate-400">Model Cache LRU, status mesin inspeksi, dan akselerasi ONNX</p>
              </div>
            </div>
            <span className="px-2.5 py-1 rounded-full text-xs font-bold font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
              <Zap className="w-3 h-3 text-amber-400" />
              LRU Active
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-black/30 border border-white/5 rounded-xl">
              <span className="text-xs font-semibold text-slate-400 block mb-1">Status Mesin Inspeksi</span>
              <span className="text-base font-bold text-cyan-300 font-mono">
                {engine.system_state || 'STANDBY'}
              </span>
              <span className="text-[11px] text-slate-400 mt-1 block">Mode: {engine.mode || 'AI'}</span>
            </div>

            <div className="p-4 bg-black/30 border border-white/5 rounded-xl">
              <span className="text-xs font-semibold text-slate-400 block mb-1">Model Ter-cache di RAM</span>
              <span className="text-base font-bold text-purple-300 font-mono">
                {engine.cached_models_count} Model Aktif
              </span>
              <span className="text-[11px] text-slate-400 mt-1 block">Part: {engine.active_part_no}</span>
            </div>
          </div>
        </div>

        {/* 4. Monitoring Endpoint for IT & DevOps */}
        <div className="glass-card p-6 border border-white/10 rounded-2xl space-y-5">
          <div className="flex items-center justify-between pb-4 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-cyan-500/20 border border-cyan-500/30 rounded-xl text-cyan-400">
                <Server className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-white text-base">Integrasi Telemetri (IT / SISON)</h3>
                <p className="text-xs text-slate-400">Public Health Check JSON API untuk monitoring eksternal</p>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-300">
              URL Endpoint Health Check:
            </label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                readOnly
                value={`${window.location.origin}/api/health`}
                className="w-full px-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-cyan-300 font-mono text-xs focus:outline-none"
              />
              <button
                onClick={copyHealthUrl}
                className="flex items-center gap-1.5 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold transition-all shrink-0 cursor-pointer shadow-md"
              >
                <Copy className="w-4 h-4" />
                <span>Salin URL</span>
              </button>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Endpoint ini dapat diintegrasikan dengan sistem monitoring pabrik (Prometheus, Uptime Kuma, Grafana, atau SISON heartbeat) tanpa perlu token autentikasi.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}
