import React, { useState, useEffect } from 'react';
import { Video, RefreshCw, Info, Power } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api/client';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';

export default function Camera() {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [switchingId, setSwitchingId] = useState(null);

  const fetchCameras = async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    try {
      const res = await api.get('/api/admin/cameras');
      setCameras(res.data || []);
    } catch (err) {
      if (!isSilent) toast.error('Gagal mengambil daftar kamera');
    } finally {
      if (!isSilent) setLoading(false);
    }
  };

  useEffect(() => {
    fetchCameras(false);
    const interval = setInterval(() => {
      fetchCameras(true);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleScanCameras = async () => {
    setScanning(true);
    try {
      const res = await api.post('/api/admin/cameras/scan');
      setCameras(res.data || []);
      toast.success(`Deteksi selesai! Ditemukan ${res.data?.length || 0} perangkat kamera.`);
    } catch (err) {
      toast.error('Gagal memindai perangkat kamera hardware');
    } finally {
      setScanning(false);
    }
  };

  const handleToggleCamera = async (c) => {
    setSwitchingId(c.id);
    try {
      const res = await api.put(`/api/admin/cameras/${c.id}/toggle`);
      if (res.data && res.data.is_active) {
        toast.success(`Kamera "${c.name || 'Kamera'}" dinyalakan (ON / Aktif)!`);
      } else {
        toast(`Kamera "${c.name || 'Kamera'}" dimatikan (OFF / Standby).`, { icon: '⏸️' });
      }
      await fetchCameras();
    } catch (err) {
      toast.error('Gagal mengubah saklar kamera');
    } finally {
      setSwitchingId(null);
    }
  };

  const headers = ["# ID", "Nama Perangkat / Posisi Kamera", "Port Input USB", "Status Operasional", "Saklar Power (ON / OFF)"];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Manajemen"
        highlightTitle="Kamera"
        subtitle="Saklar pemilihan perangkat kamera inspeksi visual AI"
        actionButton={
          <button
            onClick={handleScanCameras}
            disabled={scanning}
            className="flex items-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs rounded-xl shadow-lg shadow-emerald-600/30 transition-all disabled:opacity-50 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${scanning ? 'animate-spin' : ''}`} />
            {scanning ? 'Memindai Ulang...' : 'Deteksi Ulang Kamera'}
          </button>
        }
      />

      {/* Info Card / Guidance Banner */}
      <div className="glass-card p-4 border border-blue-500/20 bg-blue-500/5 rounded-2xl flex items-start gap-3.5">
        <Info className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-300 space-y-1">
          <p className="font-semibold text-blue-300">
            💡 Cara Ganti Kamera (Saklar ON / OFF):
          </p>
          <p className="text-slate-400 leading-relaxed">
            Cukup klik tombol saklar <strong className="text-emerald-400">ON / OFF</strong> pada kamera yang ingin digunakan. Kamera yang disetel <strong className="text-emerald-400">ON</strong> akan langsung aktif dan digunakan oleh sistem AI untuk inspeksi visual.
          </p>
        </div>
      </div>

      {/* Camera Table with Centered Layout & ON/OFF Switch */}
      <div className="glass-card p-6 border border-white/10 rounded-2xl">
        <DataTable headers={headers} isLoading={loading || scanning} emptyMessage="Tidak ada kamera terdaftar. Kamera akan otomatis terdeteksi saat sistem berjalan.">
          {cameras.map((c) => {
            const src = String(c?.source || '0');
            const camName = c?.name || `USB Camera (${src})`;
            const isSwitching = switchingId === c.id;

            return (
              <tr key={c.id || src} className="hover:bg-white/5 transition-colors">
                {/* 1. ID */}
                <td className="p-4 text-xs font-mono text-slate-400 text-center">
                  #{c.id ?? '-'}
                </td>

                {/* 2. Nama Perangkat */}
                <td className="p-4 font-bold text-white text-center">
                  <div className="flex items-center justify-center gap-2">
                    <Video className={`w-4 h-4 ${c.is_active ? 'text-emerald-400' : 'text-slate-500'} shrink-0`} />
                    <span className="truncate">{camName}</span>
                  </div>
                </td>

                {/* 3. Port Input USB */}
                <td className="p-4 text-center">
                  <div className="flex items-center justify-center gap-2">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/30">
                      USB Port
                    </span>
                    <span className="font-mono text-xs text-slate-300 bg-black/30 px-2.5 py-0.5 rounded-lg border border-white/5 font-semibold">
                      Index {src}
                    </span>
                  </div>
                </td>

                {/* 4. Status Operasional */}
                <td className="p-4 text-center">
                  <div className="flex justify-center items-center">
                    {c.is_active ? (
                      <span className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shadow-sm shadow-emerald-500/20">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                        AKTIF (ON)
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-white/10">
                        <span className="w-2 h-2 rounded-full bg-slate-500"></span>
                        STANDBY (OFF)
                      </span>
                    )}
                  </div>
                </td>

                {/* 5. Saklar ON / OFF Single Button */}
                <td className="p-4 text-center">
                  <div className="flex items-center justify-center">
                    <button
                      onClick={() => handleToggleCamera(c)}
                      disabled={isSwitching}
                      className={`flex items-center justify-center gap-2 px-5 py-2 text-xs font-bold rounded-xl transition-all cursor-pointer ${
                        c.is_active
                          ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/30'
                          : 'bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 hover:text-white'
                      } ${isSwitching ? 'opacity-50 cursor-wait' : ''}`}
                      title={c.is_active ? 'Klik untuk mematikan kamera (OFF / Standby)' : 'Klik untuk menyalakan kamera ini (ON / Aktif)'}
                    >
                      <Power className={`w-3.5 h-3.5 ${c.is_active ? 'text-white' : 'text-slate-400'}`} />
                      <span>{c.is_active ? 'ON' : 'OFF'}</span>
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </DataTable>
      </div>
    </div>
  );
}


