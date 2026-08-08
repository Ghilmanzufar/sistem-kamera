import React from 'react';
import { Link } from 'react-router-dom';
import { 
  KeyRound, 
  ArrowLeft, 
  ShieldAlert, 
  UserCheck, 
  PhoneCall, 
  HelpCircle,
  Clock,
  CheckCircle2
} from 'lucide-react';

export default function ForgotPassword() {
  return (
    <div className="min-h-screen app-bg-gradient flex items-center justify-center p-4 sm:p-6 lg:p-10">
      <div className="w-full max-w-xl p-8 sm:p-10 glass-card border border-white/10 rounded-3xl shadow-2xl backdrop-blur-xl space-y-8 animate-fadeIn">
        
        {/* Top Header & Branding */}
        <div className="text-center space-y-3">
          <img
            src="LOGO_SUGITY.png"
            alt="Logo Sugity"
            className="h-16 w-auto mx-auto object-contain drop-shadow-md"
          />
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-bold uppercase tracking-wider">
            <KeyRound className="w-3.5 h-3.5" />
            Bantuan Akses Akun
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Lupa Password / PIN?
          </h1>
          <p className="text-xs sm:text-sm text-slate-300 max-w-md mx-auto leading-relaxed">
            Panduan pemulihan kredensial akun pengguna sistem inspeksi kamera lini produksi
          </p>
        </div>

        {/* Security Policy Notice */}
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-start gap-3">
          <ShieldAlert className="w-5 h-5 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-bold block">Kebijakan Keamanan Sistem Pabrik:</span>
            <span className="text-slate-200 leading-relaxed block">
              Demi keamanan lini produksi dan mencegah akses tidak terotorisasi, reset password/PIN <strong>tidak dilakukan secara mandiri</strong>.
            </span>
          </div>
        </div>

        {/* Action Steps Card */}
        <div className="p-6 bg-black/40 border border-white/5 rounded-2xl space-y-4">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <UserCheck className="w-4 h-4 text-emerald-400" />
            Langkah Penanganan (Hubungi Pengawas / Admin):
          </h2>

          <div className="space-y-3.5 text-xs text-slate-300">
            <div className="flex items-start gap-3 p-3 rounded-xl bg-white/5 border border-white/5">
              <span className="text-emerald-400 font-bold text-sm shrink-0">1.</span>
              <div>
                <strong className="text-white block mb-0.5">Panggil Pengawas (Line Supervisor) atau Admin:</strong>
                <span>Hubungi Pengawas yang sedang bertugas di shift Anda atau PIC IT sistem inspeksi pabrik.</span>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3 rounded-xl bg-white/5 border border-white/5">
              <span className="text-emerald-400 font-bold text-sm shrink-0">2.</span>
              <div>
                <strong className="text-white block mb-0.5">Reset Melalui Menu User Manajemen:</strong>
                <span>Pengawas/Admin akan membuka menu <strong>User Manajemen</strong> di dashboard untuk mengganti atau mengatur ulang PIN baru akun Anda.</span>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3 rounded-xl bg-white/5 border border-white/5">
              <span className="text-emerald-400 font-bold text-sm shrink-0">3.</span>
              <div>
                <strong className="text-white block mb-0.5">Login Langsung:</strong>
                <span>Setelah PIN baru disimpan oleh Pengawas, Anda dapat langsung login kembali tanpa perlu restart aplikasi.</span>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Contact Info */}
        <div className="p-4 rounded-2xl bg-white/5 border border-white/10 text-xs text-slate-300 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <PhoneCall className="w-4 h-4 text-blue-400" />
            <div>
              <span className="font-bold text-white block">Pusat Pengawas & IT Support:</span>
              <span className="text-slate-400 text-[11px]">Ruang Control Room / Maintenance Lini Inspeksi</span>
            </div>
          </div>
          <span className="px-2.5 py-1 rounded-lg bg-black/40 text-emerald-400 font-mono font-bold text-xs border border-white/5">
            Shift Active
          </span>
        </div>

        {/* Back to Login Action Button */}
        <div className="pt-2">
          <Link
            to="/login"
            className="w-full flex items-center justify-center gap-2 py-3.5 px-6 bg-blue-600 hover:bg-blue-500 text-white font-bold text-sm rounded-xl shadow-lg shadow-blue-600/30 transition-all cursor-pointer transform hover:-translate-y-0.5 active:translate-y-0"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Kembali ke Halaman Login</span>
          </Link>
        </div>

        {/* Footer Brand Note */}
        <div className="text-center text-[11px] text-slate-500 font-medium">
          PT Sugity Creatives • Sistem Kamera Inspeksi AI
        </div>
      </div>
    </div>
  );
}
