import React, { useState, useEffect } from 'react';
import { 
  Settings, 
  Save, 
  ShieldCheck, 
  Eye, 
  EyeOff, 
  Copy, 
  Check, 
  ExternalLink, 
  Terminal, 
  Code2, 
  Activity, 
  FileCode, 
  CheckCircle,
  HelpCircle,
  Cpu,
  Wifi,
  Radio,
  Send,
  AlertCircle,
  RefreshCw,
  Server
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api/client';
import PageHeader from '../components/PageHeader';

export default function SisonConfig() {
  const [callbackUrl, setCallbackUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [serverIp, setServerIp] = useState('127.0.0.1');
  const [showApiKey, setShowApiKey] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testingPing, setTestingPing] = useState(false);
  const [pingResult, setPingResult] = useState(null);

  // Copy states
  const [copiedPayload, setCopiedPayload] = useState(false);
  const [copiedCurl, setCopiedCurl] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);
  const [copiedIp, setCopiedIp] = useState(false);

  const fetchSisonConfig = async () => {
    try {
      const res = await api.get('/api/admin/sison-config');
      if (res.data) {
        setCallbackUrl(res.data.callback_url || '');
        setApiKey(res.data.api_key || 'kamera-secret-key');
        if (res.data.server_ip) setServerIp(res.data.server_ip);
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

  const handleTestPing = async () => {
    if (!callbackUrl || !callbackUrl.trim()) {
      toast.error('Masukkan Callback Webhook URL terlebih dahulu!');
      return;
    }
    setTestingPing(true);
    setPingResult(null);

    try {
      const res = await api.post('/api/admin/sison-test-ping', { callback_url: callbackUrl });
      setPingResult(res.data);
      if (res.data && res.data.success) {
        toast.success(`Server SISON Terhubung! (Status: ${res.data.status_code}, Latency: ${res.data.latency_ms}ms)`);
      } else {
        toast.error(`Koneksi SISON Gagal: ${res.data?.error || 'Tidak ada respon'}`);
      }
    } catch (err) {
      const errMsg = err.response?.data?.detail || err.message || 'Gagal menghubungi server SISON';
      setPingResult({ success: false, error: errMsg });
      toast.error(`Uji Webhook Gagal: ${errMsg}`);
    } finally {
      setTestingPing(false);
    }
  };

  // Example Sample JSON payload
  const samplePayload = {
    id_trans: "DEMO-1786211114",
    lot: "LOT-8821",
    p_no: "74231-0K550-00",
    unique_no: "UNQ-9901",
    p_name: "Demo Part Komponen A",
    qty: 1
  };
  const jsonPayloadString = JSON.stringify(samplePayload, null, 2);

  // Generated cURL Command
  const curlCommand = `curl.exe -X POST "http://localhost:8000/api/start" \\
  -H "Authorization: Bearer ${apiKey || 'kamera-secret-key'}" \\
  -H "Content-Type: application/json" \\
  -d '${JSON.stringify(samplePayload)}'`;

  const copyToClipboard = (text, type) => {
    navigator.clipboard.writeText(text);
    if (type === 'payload') {
      setCopiedPayload(true);
      toast.success('Template JSON berhasil disalin!');
      setTimeout(() => setCopiedPayload(false), 2000);
    } else if (type === 'curl') {
      setCopiedCurl(true);
      toast.success('Perintah cURL berhasil disalin!');
      setTimeout(() => setCopiedCurl(false), 2000);
    } else if (type === 'key') {
      setCopiedKey(true);
      toast.success('API Key berhasil disalin!');
      setTimeout(() => setCopiedKey(false), 2000);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <PageHeader
        title="Integrasi"
        highlightTitle="Sison & API Reference"
        subtitle="Pengaturan Webhook Callback, Kredensial API Key, dan Panduan Dokumentasi Endpoint Transaksi SISON"
        actionButton={
          <a
            href="/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs rounded-xl shadow-lg shadow-blue-600/30 transition-all cursor-pointer"
          >
            <ExternalLink className="w-4 h-4" />
            Buka Swagger Docs
          </a>
        }
      />

      {/* Top Grid: Sison Settings Form & Status Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left 2 Cols: Form Konfigurasi SISON */}
        <div className="lg:col-span-2 glass-card p-6 sm:p-8 border border-white/10 rounded-3xl shadow-2xl space-y-6">
          <div className="flex items-center gap-3 pb-4 border-b border-white/10">
            <div className="p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <Settings className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-wide">
                Konfigurasi Webhook & API Key
              </h2>
              <p className="text-xs text-slate-400">
                Pengaturan integrasi pertukaran data dua arah antara SISON dan Sistem Kamera
              </p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-300">
                  Callback Webhook URL (Tujuan Kirim Hasil Inspeksi ke SISON)
                </label>
                <button
                  type="button"
                  onClick={handleTestPing}
                  disabled={testingPing || !callbackUrl}
                  className="flex items-center gap-1.5 px-3 py-1 bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 rounded-lg text-xs font-semibold transition-all disabled:opacity-50 cursor-pointer"
                  title="Kirim paket ping tes ke server SISON untuk menguji konektivitas"
                >
                  {testingPing ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Menguji...</span>
                    </>
                  ) : (
                    <>
                      <Radio className="w-3.5 h-3.5" />
                      <span>🧪 Uji Koneksi Callback</span>
                    </>
                  )}
                </button>
              </div>

              <input
                type="text"
                required
                value={callbackUrl}
                onChange={(e) => setCallbackUrl(e.target.value)}
                placeholder="http://192.168.1.50:8000/api/inspection/result"
                className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-xl text-white font-mono text-sm focus:outline-none focus:border-blue-500 transition-all"
              />

              {/* Ping Result Feedback Box */}
              {pingResult && (
                <div className={`mt-2.5 p-3 rounded-xl border text-xs font-mono flex items-start gap-2 ${
                  pingResult.success 
                    ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300' 
                    : 'bg-rose-500/10 border-rose-500/20 text-rose-300'
                }`}>
                  {pingResult.success ? <CheckCircle className="w-4 h-4 shrink-0 mt-0.5" /> : <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />}
                  <div className="space-y-0.5">
                    <span className="font-bold">
                      {pingResult.success 
                        ? `✅ Server SISON Terhubung (HTTP ${pingResult.status_code} | Latensi: ${pingResult.latency_ms} ms)`
                        : `❌ Gagal Terhubung ke SISON (${pingResult.error}) | Latensi: ${pingResult.latency_ms} ms`
                      }
                    </span>
                    <p className="text-[11px] text-slate-300 font-sans">
                      {pingResult.success 
                        ? 'Endpoint Webhook SISON aktif dan siap menerima data hasil inspeksi.'
                        : 'Pastikan server SISON sedang menyala dan alamat IP/Port sudah sesuai.'}
                    </p>
                  </div>
                </div>
              )}

              <p className="text-[11px] text-slate-400 mt-1.5">
                URL endpoint di server SISON yang akan menerima kiriman status (OK/NG) saat inspeksi selesai. Dilengkapi <strong>Auto-Retry 3x</strong> otomatis jika terjadi gangguan jaringan sesaat.
              </p>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">
                API Security Key / Authorization Bearer Token
              </label>
              <div className="relative flex items-center">
                <input
                  type={showApiKey ? "text" : "password"}
                  required
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="sugity_sison_secret_key"
                  className="w-full px-4 py-3 pr-24 bg-black/30 border border-white/10 rounded-xl text-white font-mono text-sm focus:outline-none focus:border-blue-500 transition-all"
                />
                <div className="absolute right-2 flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="p-2 text-slate-400 hover:text-white transition-colors cursor-pointer"
                    title={showApiKey ? "Sembunyikan API Key" : "Lihat API Key"}
                  >
                    {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(apiKey, 'key')}
                    className="p-2 text-slate-400 hover:text-emerald-400 transition-colors cursor-pointer"
                    title="Salin API Key"
                  >
                    {copiedKey ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <p className="text-[11px] text-slate-400 mt-1.5">
                Token rahasia yang wajib disertakan pada header <code className="text-amber-300 font-mono">Authorization: Bearer &lt;key&gt;</code> oleh sistem SISON.
              </p>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={loading || saving}
                className="w-full sm:w-auto flex items-center justify-center gap-2 py-3 px-8 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl shadow-lg shadow-blue-600/30 transition-all text-sm disabled:opacity-50 cursor-pointer"
              >
                <Save className="w-4 h-4" />
                {saving ? 'Menyimpan...' : 'Simpan Konfigurasi Sison'}
              </button>
            </div>
          </form>
        </div>

        {/* Right 1 Col: Status Integrasi & Ringkasan Server */}
        <div className="glass-card p-6 sm:p-8 border border-white/10 rounded-3xl shadow-2xl space-y-5 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center gap-3 pb-3 border-b border-white/10">
              <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Status Jaringan & Server</h3>
                <p className="text-xs text-slate-400">Parameter port & protokol aktif</p>
              </div>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="flex justify-between items-center p-2.5 bg-black/30 rounded-xl border border-white/5">
                <span className="text-slate-400 font-medium">IP PC Kamera:</span>
                <div className="flex items-center gap-1.5">
                  <span className="font-mono font-bold text-emerald-400">{serverIp}</span>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(serverIp);
                      setCopiedIp(true);
                      toast.success('IP PC Kamera disalin!');
                      setTimeout(() => setCopiedIp(false), 2000);
                    }}
                    className="text-slate-400 hover:text-white cursor-pointer"
                    title="Salin IP"
                  >
                    {copiedIp ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>
              <div className="flex justify-between p-2.5 bg-black/30 rounded-xl border border-white/5">
                <span className="text-slate-400 font-medium">Port Server:</span>
                <span className="font-mono font-bold text-emerald-400">:8000</span>
              </div>
              <div className="flex justify-between p-2.5 bg-black/30 rounded-xl border border-white/5">
                <span className="text-slate-400 font-medium">Metode Autentikasi:</span>
                <span className="font-mono font-bold text-blue-300">Bearer Token</span>
              </div>
              <div className="flex justify-between p-2.5 bg-black/30 rounded-xl border border-white/5">
                <span className="text-slate-400 font-medium">Keandalan Webhook:</span>
                <span className="font-mono font-bold text-emerald-400">Auto-Retry (3x)</span>
              </div>
              <div className="flex justify-between p-2.5 bg-black/30 rounded-xl border border-white/5">
                <span className="text-slate-400 font-medium">Format Payload:</span>
                <span className="font-mono font-bold text-amber-300">application/json</span>
              </div>
            </div>
          </div>

          {/* Rekomendasi Jaringan IT Pabrik */}
          <div className="p-3.5 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-xs text-blue-300 space-y-1.5">
            <div className="font-bold flex items-center gap-1.5 text-white">
              <Server className="w-4 h-4 text-blue-400" />
              Rekomendasi IT & Jaringan
            </div>
            <p className="text-[11px] text-slate-300 leading-relaxed">
              Gunakan <strong>Static IP</strong> pada PC Kamera atau kunci <strong>DHCP Reservation (MAC Address Binding)</strong> di router agar IP tidak pernah berubah saat PC restart.
            </p>
          </div>
        </div>
      </div>

      {/* ==============================================================
          BOTTOM SECTION: DOKUMENTASI LENGKAP ENDPOINT & INTEGRASI API
      ============================================================== */}
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
            <Code2 className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white tracking-wide">
              Dokumentasi Spesifikasi Endpoint API
            </h2>
            <p className="text-xs text-slate-400">
              Panduan format payload data transaksi, header keamanan, dan perintah pengujian
            </p>
          </div>
        </div>

        {/* 1. Endpoint Utama: POST /api/start */}
        <div className="glass-card p-6 sm:p-8 border border-white/10 rounded-3xl shadow-2xl space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-white/10">
            <div className="flex items-center gap-3">
              <span className="px-3 py-1 rounded-xl text-xs font-black bg-emerald-600 text-white shadow-md shadow-emerald-600/30">
                POST
              </span>
              <span className="text-base sm:text-lg font-mono font-bold text-white">
                /api/start
              </span>
            </div>
            <span className="text-xs font-semibold text-slate-300 bg-white/5 border border-white/10 px-3 py-1 rounded-lg">
              Trigger Transaksi SISON
            </span>
          </div>

          <p className="text-xs sm:text-sm text-slate-200 leading-relaxed">
            Endpoint ini dipanggil oleh sistem SISON ketika part baru masuk ke stasiun kerja kamera untuk memulai proses deteksi dan verifikasi komponen.
          </p>

          {/* Headers Spec */}
          <div className="space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 block">
              Required Headers:
            </span>
            <div className="p-3.5 bg-black/40 border border-white/5 rounded-2xl font-mono text-xs text-slate-300 space-y-1">
              <div><span className="text-slate-500">Content-Type  :</span> <span className="text-amber-300">application/json</span></div>
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-slate-500">Authorization :</span> <span className="text-emerald-400">Bearer {apiKey || 'kamera-secret-key'}</span>
                </div>
                <button
                  onClick={() => copyToClipboard(`Bearer ${apiKey || 'kamera-secret-key'}`, 'key')}
                  className="text-[11px] font-sans font-semibold text-slate-400 hover:text-white flex items-center gap-1 cursor-pointer"
                >
                  <Copy className="w-3.5 h-3.5" /> Salin Header
                </button>
              </div>
            </div>
          </div>

          {/* JSON Payload & Copy */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Request Body (JSON Payload):
              </span>
              <button
                onClick={() => copyToClipboard(jsonPayloadString, 'payload')}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-200 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 hover:text-white transition-all cursor-pointer"
              >
                {copiedPayload ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedPayload ? 'Tersalin!' : 'Salin JSON Payload'}</span>
              </button>
            </div>

            <pre className="p-4 bg-black/60 border border-white/5 rounded-2xl font-mono text-xs sm:text-sm text-blue-300 overflow-x-auto scrollbar-thin">
              {jsonPayloadString}
            </pre>
          </div>

          {/* Field Description Table */}
          <div className="space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 block">
              Struktur Parameter Payload:
            </span>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border border-white/10 rounded-2xl overflow-hidden">
                <thead className="bg-white/5 text-slate-300 border-b border-white/10 font-bold">
                  <tr>
                    <th className="p-3">Field</th>
                    <th className="p-3">Tipe</th>
                    <th className="p-3">Wajib?</th>
                    <th className="p-3">Deskripsi & Contoh</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-slate-300 font-mono">
                  <tr>
                    <td className="p-3 font-bold text-white">id_trans</td>
                    <td className="p-3 text-amber-300">string</td>
                    <td className="p-3 text-emerald-400 font-sans font-bold">Ya</td>
                    <td className="p-3 font-sans">ID unik transaksi dari SISON (Contoh: <code>DEMO-1786211114</code>)</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-bold text-white">p_no</td>
                    <td className="p-3 text-amber-300">string</td>
                    <td className="p-3 text-emerald-400 font-sans font-bold">Ya</td>
                    <td className="p-3 font-sans">Part number produk yang diinspeksi (Contoh: <code>74231-0K550-00</code>)</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-bold text-white">lot</td>
                    <td className="p-3 text-amber-300">string</td>
                    <td className="p-3 text-slate-400 font-sans">Opsional</td>
                    <td className="p-3 font-sans">Nomor LOT produksi batch (Contoh: <code>LOT-8821</code>)</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-bold text-white">unique_no</td>
                    <td className="p-3 text-amber-300">string</td>
                    <td className="p-3 text-slate-400 font-sans">Opsional</td>
                    <td className="p-3 font-sans">Nomor identifikasi unik komponen (Contoh: <code>UNQ-9901</code>)</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-bold text-white">p_name</td>
                    <td className="p-3 text-amber-300">string</td>
                    <td className="p-3 text-slate-400 font-sans">Opsional</td>
                    <td className="p-3 font-sans">Nama part atau deskripsi komponen (Contoh: <code>Demo Part A</code>)</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-bold text-white">qty</td>
                    <td className="p-3 text-blue-300">integer</td>
                    <td className="p-3 text-emerald-400 font-sans font-bold">Ya</td>
                    <td className="p-3 font-sans">Target jumlah QTY inspeksi per transaksi (Contoh: <code>1</code>)</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* cURL Command Generator */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 text-blue-400" />
                Perintah Pengujian cURL (PowerShell / Terminal / Postman):
              </span>
              <button
                onClick={() => copyToClipboard(curlCommand, 'curl')}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-200 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 hover:text-white transition-all cursor-pointer"
              >
                {copiedCurl ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedCurl ? 'Tersalin!' : 'Salin Perintah cURL'}</span>
              </button>
            </div>

            <pre className="p-4 bg-black/70 border border-white/10 rounded-2xl font-mono text-xs text-emerald-300 overflow-x-auto scrollbar-thin leading-relaxed">
              {curlCommand}
            </pre>
          </div>
        </div>

        {/* 2. Endpoint Monitoring & System Health */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* GET /health */}
          <div className="glass-card p-6 border border-white/10 rounded-3xl shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-lg text-xs font-bold bg-blue-600 text-white">GET</span>
                <span className="font-mono font-bold text-white text-sm">/health</span>
              </div>
              <span className="text-xs text-emerald-400 font-semibold">Server Check</span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Digunakan oleh sistem monitoring atau watchdog untuk memeriksa apakah server FastAPI dan kamera berjalan aktif.
            </p>
            <div className="p-3 bg-black/40 rounded-xl border border-white/5 font-mono text-xs text-emerald-400">
              {`{ "status": "ok", "app": "Sistem Kamera Inspeksi", "code": 200 }`}
            </div>
          </div>

          {/* GET /api/status */}
          <div className="glass-card p-6 border border-white/10 rounded-3xl shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-lg text-xs font-bold bg-blue-600 text-white">GET</span>
                <span className="font-mono font-bold text-white text-sm">/api/status</span>
              </div>
              <span className="text-xs text-blue-400 font-semibold">Live State</span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Mengembalikan status inspeksi saat ini (<code className="text-amber-300">RUNNING</code>, <code className="text-emerald-300">OK</code>, <code className="text-rose-300">NG</code>, <code className="text-slate-300">STANDBY</code>) dan sisa QTY.
            </p>
            <div className="p-3 bg-black/40 rounded-xl border border-white/5 font-mono text-xs text-blue-300">
              {`{ "status": "RUNNING", "p_no": "74231-0K550-00", "sisa_qty": 1 }`}
            </div>
          </div>
        </div>

        {/* 3. HTTP Response Status Reference Card */}
        <div className="glass-card p-6 sm:p-8 border border-white/10 rounded-3xl shadow-xl space-y-4">
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <HelpCircle className="w-5 h-5 text-blue-400" />
            Standar Status Response HTTP
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
            <div className="p-3.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 space-y-1">
              <div className="font-mono font-bold text-emerald-400 text-sm">200 OK</div>
              <p className="text-slate-300">Payload valid & transaksi inspeksi berhasil dimulai di kamera.</p>
            </div>

            <div className="p-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/20 space-y-1">
              <div className="font-mono font-bold text-amber-400 text-sm">400 Bad Request</div>
              <p className="text-slate-300">Format JSON tidak valid atau parameter wajib (<code>p_no</code>, <code>id_trans</code>) kosong.</p>
            </div>

            <div className="p-3.5 rounded-2xl bg-rose-500/10 border border-rose-500/20 space-y-1">
              <div className="font-mono font-bold text-rose-400 text-sm">401 Unauthorized</div>
              <p className="text-slate-300">API Key tidak disertakan atau tidak cocok dengan konfigurasi SISON.</p>
            </div>

            <div className="p-3.5 rounded-2xl bg-purple-500/10 border border-purple-500/20 space-y-1">
              <div className="font-mono font-bold text-purple-400 text-sm">409 Conflict</div>
              <p className="text-slate-300">Kamera masih sibuk memproses inspeksi transaksi sebelumnya.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
