import React, { useState } from 'react';
import { useSearchParams, useNavigate, useLocation } from 'react-router-dom';
import { 
  AlertTriangle, 
  RefreshCw, 
  Home, 
  Copy, 
  Check, 
  ChevronDown, 
  ChevronUp, 
  Server, 
  WifiOff, 
  CameraOff, 
  FileQuestion,
  HelpCircle,
  ShieldAlert
} from 'lucide-react';
import toast from 'react-hot-toast';

export default function ErrorPage({ 
  type = 'auto', 
  error = null, 
  errorInfo = null, 
  resetErrorBoundary = null 
}) {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();

  const [copied, setCopied] = useState(false);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  // Error Code & Message from query params or props
  const codeParam = searchParams.get('code') || (type !== 'auto' ? type : '500');
  const msgParam = searchParams.get('msg') || (error ? (error.message || String(error)) : '');

  // Determine error category
  const is404 = codeParam === '404' || type === '404';
  const isNetwork = codeParam.toLowerCase().includes('network') || codeParam === 'OFFLINE' || (error && error.isAxiosError && !error.response);
  const isCamera = codeParam.toLowerCase().includes('camera') || codeParam === 'CAMERA_OFFLINE';

  const getErrorMeta = () => {
    if (is404) {
      return {
        title: 'Halaman Tidak Ditemukan (404)',
        badge: 'Rute Tidak Valid',
        badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
        subtitle: 'Alamat halaman yang Anda tuju tidak tersedia atau telah dipindahkan ke menu lain.',
        icon: FileQuestion,
        iconColor: 'text-amber-400',
        iconBg: 'bg-amber-500/10 border-amber-500/20',
        errorCode: 'ERR_PAGE_NOT_FOUND',
      };
    }

    if (isNetwork) {
      return {
        title: 'Koneksi Server Backend Terputus',
        badge: 'Koneksi Offline / Timeout',
        badgeColor: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
        subtitle: 'Aplikasi web tidak dapat berkomunikasi dengan server lokal port 8000.',
        icon: WifiOff,
        iconColor: 'text-rose-400',
        iconBg: 'bg-rose-500/10 border-rose-500/20',
        errorCode: 'ERR_CONNECTION_REFUSED_8000',
      };
    }

    if (isCamera) {
      return {
        title: 'Perangkat Kamera Tidak Terdeteksi',
        badge: 'Gangguan Hardware Kamera',
        badgeColor: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
        subtitle: 'Sumber video USB atau stream RTSP terputus atau dinonaktifkan dari saklar pengaturan.',
        icon: CameraOff,
        iconColor: 'text-purple-400',
        iconBg: 'bg-purple-500/10 border-purple-500/20',
        errorCode: 'ERR_CAMERA_HARDWARE_DISCONNECTED',
      };
    }

    return {
      title: 'Terjadi Gangguan pada Sistem (500)',
      badge: 'System Exception',
      badgeColor: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
      subtitle: 'Sistem mengalami kendala saat memproses permintaan data. Komponen utama tetap aman.',
      icon: ShieldAlert,
      iconColor: 'text-rose-400',
      iconBg: 'bg-rose-500/10 border-rose-500/20',
      errorCode: 'ERR_INTERNAL_SERVER_EXCEPTION',
    };
  };

  const meta = getErrorMeta();
  const IconComponent = meta.icon;

  const timestamp = new Date().toLocaleString('id-ID', {
    dateStyle: 'full',
    timeStyle: 'medium',
  });

  const diagnosticText = `[SISTEM KAMERA INSPEKSI - DIAGNOSTIC LOG]
Timestamp : ${timestamp}
URL Path  : ${location.pathname}${location.search}
Error Code: ${meta.errorCode} (${codeParam})
Message   : ${msgParam || 'Tidak ada pesan error spesifik'}
User Agent: ${navigator.userAgent}
Technical Details:
${error?.stack || errorInfo?.componentStack || 'No stack trace recorded'}`;

  const handleCopyDiagnostics = () => {
    navigator.clipboard.writeText(diagnosticText);
    setCopied(true);
    toast.success('Kode & log diagnostik berhasil disalin ke clipboard!');
    setTimeout(() => setCopied(false), 2500);
  };

  const handleRetry = () => {
    if (resetErrorBoundary) {
      resetErrorBoundary();
    } else {
      window.location.reload();
    }
  };

  const handleGoHome = () => {
    const role = (localStorage.getItem('user_role') || '').toLowerCase();
    if (role === 'operator') {
      navigate('/history');
    } else {
      navigate('/dashboard');
    }
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center p-4 sm:p-6 lg:p-10">
      <div className="w-full max-w-5xl lg:max-w-6xl glass-card border border-white/15 rounded-3xl p-8 sm:p-12 lg:p-14 shadow-2xl space-y-10 animate-fadeIn">
        
        {/* Top Header & Visual Icon */}
        <div className="flex flex-col sm:flex-row items-center sm:items-start gap-8 text-center sm:text-left pb-8 border-b border-white/10">
          <div className={`p-6 sm:p-7 rounded-3xl border ${meta.iconBg} shrink-0 shadow-2xl`}>
            <IconComponent className={`w-16 h-16 sm:w-20 sm:h-20 ${meta.iconColor}`} />
          </div>

          <div className="space-y-3.5 flex-1">
            <div className="flex flex-wrap items-center justify-center sm:justify-start gap-3">
              <span className={`px-4 py-1.5 rounded-full text-xs sm:text-sm font-extrabold uppercase tracking-wider border shadow-sm ${meta.badgeColor}`}>
                {meta.badge}
              </span>
              <span className="text-xs sm:text-sm font-mono text-slate-400 font-bold bg-black/30 px-3 py-1 rounded-lg border border-white/5">
                Ref: {meta.errorCode}
              </span>
            </div>

            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black text-white tracking-tight leading-tight">
              {meta.title}
            </h1>

            <p className="text-base sm:text-lg lg:text-xl text-slate-200 leading-relaxed max-w-3xl font-medium">
              {meta.subtitle}
            </p>
          </div>
        </div>

        {/* Action Buttons (Call to Action - Extra Large & Prominent) */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-5">
          <button
            onClick={handleRetry}
            className="flex items-center justify-center gap-3 px-6 py-4 sm:py-5 rounded-2xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-base sm:text-lg shadow-xl shadow-blue-600/30 transition-all cursor-pointer transform hover:-translate-y-0.5 active:translate-y-0"
          >
            <RefreshCw className="w-5 h-5 sm:w-6 sm:h-6 shrink-0" />
            <span>Coba Lagi (Refresh)</span>
          </button>

          <button
            onClick={handleGoHome}
            className="flex items-center justify-center gap-3 px-6 py-4 sm:py-5 rounded-2xl bg-white/5 hover:bg-white/10 text-white font-bold text-base sm:text-lg border border-white/10 transition-all cursor-pointer transform hover:-translate-y-0.5 active:translate-y-0"
          >
            <Home className="w-5 h-5 sm:w-6 sm:h-6 shrink-0" />
            <span>Ke Dashboard Utama</span>
          </button>

          <button
            onClick={handleCopyDiagnostics}
            className="flex items-center justify-center gap-3 px-6 py-4 sm:py-5 rounded-2xl bg-white/5 hover:bg-white/10 text-slate-200 hover:text-white font-bold text-base sm:text-lg border border-white/10 transition-all cursor-pointer transform hover:-translate-y-0.5 active:translate-y-0"
            title="Salin log error untuk tim IT Support"
          >
            {copied ? (
              <Check className="w-5 h-5 sm:w-6 sm:h-6 text-emerald-400 shrink-0" />
            ) : (
              <Copy className="w-5 h-5 sm:w-6 sm:h-6 text-slate-400 shrink-0" />
            )}
            <span>{copied ? 'Tersalin!' : 'Salin Kode Error'}</span>
          </button>
        </div>

        {/* Self-Troubleshooting Checklist (Extra Clear & High Contrast) */}
        <div className="p-6 sm:p-8 bg-black/40 border border-white/10 rounded-3xl space-y-4 shadow-inner">
          <h2 className="text-base sm:text-lg lg:text-xl font-black text-white flex items-center gap-3 uppercase tracking-wider">
            <HelpCircle className="w-6 h-6 text-blue-400 shrink-0" />
            <span>Panduan Penanganan Cepat (Self-Troubleshooting):</span>
          </h2>

          <ul className="text-sm sm:text-base text-slate-200 space-y-3.5 leading-relaxed pt-1">
            <li className="flex items-start gap-3 p-3 rounded-xl bg-white/5 border border-white/5">
              <span className="text-emerald-400 font-black text-base sm:text-lg shrink-0">1.</span>
              <span>
                <strong className="text-white font-bold">Aplikasi Server Python:</strong> Pastikan program backend <code className="px-2 py-1 rounded-lg bg-black/60 text-amber-300 font-mono font-bold text-sm border border-white/10">python BASIC_APP.py</code> sedang berjalan aktif di terminal.
              </span>
            </li>
            <li className="flex items-start gap-3 p-3 rounded-xl bg-white/5 border border-white/5">
              <span className="text-emerald-400 font-black text-base sm:text-lg shrink-0">2.</span>
              <span>
                <strong className="text-white font-bold">Koneksi Hardware Kamera:</strong> Periksa kabel USB kamera tercolok kencang di port komputer dan saklar kamera pada menu <strong>Kamera</strong> berada pada posisi <strong className="text-emerald-400">ON (Aktif)</strong>.
              </span>
            </li>
            <li className="flex items-start gap-3 p-3 rounded-xl bg-white/5 border border-white/5">
              <span className="text-emerald-400 font-black text-base sm:text-lg shrink-0">3.</span>
              <span>
                <strong className="text-white font-bold">Database PostgreSQL:</strong> Pastikan layanan database PostgreSQL dalam status aktif dan konfigurasi di berkas <code className="px-2 py-1 rounded-lg bg-black/60 text-slate-200 font-mono font-bold text-sm border border-white/10">.env</code> sudah sesuai.
              </span>
            </li>
          </ul>
        </div>

        {/* Accordion: Technical Diagnostics for IT / Debugging */}
        <div className="border border-white/10 rounded-3xl overflow-hidden shadow-lg">
          <button
            onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
            className="w-full flex items-center justify-between p-5 sm:p-6 bg-white/5 hover:bg-white/10 text-sm sm:text-base font-bold text-slate-200 uppercase tracking-wider transition-all cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <Server className="w-5 h-5 text-slate-400 shrink-0" />
              <span>Informasi Teknis untuk IT Support & Maintenance</span>
            </div>
            {showTechnicalDetails ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </button>

          {showTechnicalDetails && (
            <div className="p-6 sm:p-8 bg-black/60 border-t border-white/10 space-y-4 font-mono text-xs sm:text-sm text-slate-300">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="bg-black/40 p-4 rounded-xl border border-white/5 space-y-1">
                  <span className="text-slate-500 font-sans font-bold text-xs uppercase tracking-wider block">Waktu Gangguan:</span>
                  <span className="font-bold text-white text-sm sm:text-base">{timestamp}</span>
                </div>
                <div className="bg-black/40 p-4 rounded-xl border border-white/5 space-y-1">
                  <span className="text-slate-500 font-sans font-bold text-xs uppercase tracking-wider block">Kode Status Sistem:</span>
                  <span className="font-bold text-amber-400 text-sm sm:text-base">{meta.errorCode}</span>
                </div>
              </div>

              {msgParam && (
                <div className="bg-black/40 p-4 rounded-xl border border-white/5 space-y-1">
                  <span className="text-slate-500 font-sans font-bold text-xs uppercase tracking-wider block">Detail Pesan Error:</span>
                  <span className="text-rose-300 text-sm sm:text-base font-medium break-all">{msgParam}</span>
                </div>
              )}

              {(error?.stack || errorInfo?.componentStack) && (
                <div className="space-y-2">
                  <span className="text-slate-500 font-sans font-bold text-xs uppercase tracking-wider block">Stack Trace Telemetri:</span>
                  <pre className="p-4 bg-black/80 border border-white/10 rounded-2xl text-xs sm:text-sm text-slate-300 overflow-x-auto max-h-56 scrollbar-thin leading-relaxed">
                    {error?.stack || errorInfo?.componentStack}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer Brand Note */}
        <div className="pt-2 text-center text-xs sm:text-sm font-semibold text-slate-400 tracking-wide">
          Sistem Kamera Inspeksi AI • Continuous Quality & Defect Detection System
        </div>
      </div>
    </div>
  );
}
