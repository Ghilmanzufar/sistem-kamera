import React, { useState, useEffect, useCallback } from 'react';
import { Camera as CameraIcon, Plus, CheckCircle, Trash2, Video, Pencil, AlertTriangle, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api/client';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import ConfirmModal from '../components/ConfirmModal';

export default function Camera() {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editCam, setEditCam] = useState(null); // null = mode tambah, obj = mode edit
  const [name, setName] = useState('');
  const [source, setSource] = useState('0');
  const [submitting, setSubmitting] = useState(false);
  const [deleteCamId, setDeleteCamId] = useState(null);

  const fetchCameras = async () => {
    try {
      const res = await api.get('/api/admin/cameras');
      setCameras(res.data || []);
    } catch (err) {
      toast.error('Gagal mengambil daftar kamera');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCameras();
  }, []);

  const handleScanCameras = async () => {
    setScanning(true);
    try {
      const res = await api.post('/api/admin/cameras/scan');
      setCameras(res.data || []);
      toast.success(`Pemindaian selesai! Total ${res.data?.length || 0} kamera terdaftar.`);
    } catch (err) {
      toast.error('Gagal memindai perangkat kamera hardware');
    } finally {
      setScanning(false);
    }
  };

  const resetForm = useCallback(() => {
    setName('');
    setSource('0');
    setEditCam(null);
    setShowModal(false);
  }, []);

  const handleOpenCreateModal = () => {
    setName('');
    setSource('0');
    setEditCam(null);
    setShowModal(true);
  };

  const handleOpenEditModal = (cam) => {
    setEditCam(cam);
    setName(cam.name);
    setSource(cam.source);
    setShowModal(true);
  };

  // Keyboard shortcut listener (ESC to close modal)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        if (showModal) resetForm();
        if (deleteCamId) setDeleteCamId(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showModal, deleteCamId, resetForm]);

  const handleSubmitForm = async (e) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      if (editCam) {
        // Edit Mode
        await api.put(`/api/admin/cameras/${editCam.id}`, { name, source });
        toast.success(`Kamera ${name} berhasil diperbarui!`);
      } else {
        // Create Mode
        await api.post('/api/admin/cameras', { name, source });
        toast.success(`Kamera ${name} berhasil ditambahkan!`);
      }
      resetForm();
      fetchCameras();
    } catch (err) {
      toast.error(editCam ? 'Gagal memperbarui kamera' : 'Gagal menambah kamera');
    } finally {
      setSubmitting(false);
    }
  };

  const handleActivateCamera = async (id, camName) => {
    try {
      await api.put(`/api/admin/cameras/${id}/activate`);
      toast.success(`Kamera ${camName} diaktifkan sebagai sumber utama!`);
      fetchCameras();
    } catch (err) {
      toast.error('Gagal mengaktifkan kamera');
    }
  };

  const handleDeleteCamera = async () => {
    if (!deleteCamId) return;
    try {
      const res = await api.delete(`/api/admin/cameras/${deleteCamId}`);
      if (res.data && res.data.was_active) {
        toast.success('Kamera aktif dihapus. Perangkat lain otomatis diaktifkan.');
      } else {
        toast.success('Kamera berhasil dihapus');
      }
      fetchCameras();
    } catch (err) {
      toast.error('Gagal menghapus kamera');
    } finally {
      setDeleteCamId(null);
    }
  };

  const selectedDeleteCam = cameras.find((c) => c.id === deleteCamId);

  const headers = ["# ID", "Nama Perangkat / Lokasi", "Tipe & Sumber Video", "Status Utama", "Aksi"];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Manajemen"
        highlightTitle="Kamera"
        subtitle="Perangkat kamera masukan video terdeteksi di komputer lokasi inspeksi"
        actionButton={
          <div className="flex items-center gap-3">
            <button
              onClick={handleScanCameras}
              disabled={scanning}
              className="flex items-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm rounded-xl shadow-lg shadow-emerald-600/30 transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${scanning ? 'animate-spin' : ''}`} />
              {scanning ? 'Memindai Perangkat...' : 'Scan Kamera Hardware'}
            </button>
            <button
              onClick={handleOpenCreateModal}
              className="flex items-center gap-2 px-4 py-2.5 bg-white/10 hover:bg-white/20 text-white font-semibold text-sm rounded-xl border border-white/10 transition-all text-xs"
            >
              <Plus className="w-3.5 h-3.5" />
              Tambah RTSP / Custom
            </button>
          </div>
        }
      />

      <div className="glass-card p-6 border border-white/10 rounded-2xl">
        <DataTable headers={headers} isLoading={loading}>
          {cameras.map((c) => {
            const isRtsp = c.source.toLowerCase().startsWith('rtsp://') || c.source.toLowerCase().startsWith('http://');
            return (
              <tr key={c.id} className="hover:bg-white/5 transition-colors">
                <td className="p-4 text-xs font-mono text-slate-400">#{c.id}</td>
                <td className="p-4 font-bold text-white flex items-center gap-2">
                  <Video className="w-4 h-4 text-blue-400" />
                  {c.name}
                </td>
                <td className="p-4">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                        isRtsp
                          ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                          : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      }`}
                    >
                      {isRtsp ? 'RTSP Stream' : 'USB / Webcam'}
                    </span>
                    <span className="font-mono text-xs text-slate-300">{c.source}</span>
                  </div>
                </td>
                <td className="p-4">
                  {c.is_active ? (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shadow-sm shadow-emerald-500/20">
                      <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                      Aktif Utama
                    </span>
                  ) : (
                    <span className="px-3 py-1 rounded-full text-xs font-semibold bg-gray-500/20 text-slate-400">
                      Standby
                    </span>
                  )}
                </td>
                <td className="p-4 flex items-center gap-2">
                  {!c.is_active && (
                    <button
                      onClick={() => handleActivateCamera(c.id, c.name)}
                      className="px-3 py-1.5 text-xs font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-lg hover:bg-emerald-500 hover:text-white transition-all"
                    >
                      Aktifkan
                    </button>
                  )}
                  <button
                    onClick={() => handleOpenEditModal(c)}
                    className="p-2 text-xs font-semibold text-blue-400 bg-blue-500/10 border border-blue-500/20 rounded-lg hover:bg-blue-500 hover:text-white transition-all"
                    title="Edit Konfigurasi Kamera"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => setDeleteCamId(c.id)}
                    className="p-2 text-xs font-semibold text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-lg hover:bg-rose-500 hover:text-white transition-all"
                    title="Hapus Perangkat Kamera"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </td>
              </tr>
            );
          })}
        </DataTable>
      </div>

      {/* Add / Edit Camera Modal */}
      {showModal && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200"
          onClick={(e) => {
            if (e.target === e.currentTarget) resetForm();
          }}
        >
          <div className="w-full max-w-md p-6 glass-card border border-white/10 rounded-2xl shadow-2xl">
            <h3 className="text-xl font-bold text-white mb-4">
              {editCam ? 'Ubah Konfigurasi Kamera' : 'Tambah Perangkat Kamera Baru'}
            </h3>

            <form onSubmit={handleSubmitForm} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  Nama Perangkat / Lokasi
                </label>
                <input
                  type="text"
                  required
                  placeholder="Contoh: Kamera Line 1 Front"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-4 py-2.5 bg-black/30 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  Sumber Video (Index USB 0/1/2 atau URL RTSP)
                </label>
                <input
                  type="text"
                  required
                  placeholder="0 atau rtsp://192.168.1.100:554/stream"
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                  className="w-full px-4 py-2.5 bg-black/30 border border-white/10 rounded-xl text-white font-mono text-sm focus:outline-none focus:border-blue-500 transition-colors"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Gunakan <code className="text-amber-300">0</code> atau <code className="text-amber-300">1</code> untuk USB Webcam, atau sertakan URL RTSP lengkap.
                </p>
              </div>

              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={resetForm}
                  className="px-4 py-2 text-sm font-medium text-slate-300 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 transition-all"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-lg shadow-lg shadow-blue-600/30 disabled:opacity-50 transition-all"
                >
                  {submitting ? 'Memproses...' : editCam ? 'Simpan Perubahan' : 'Simpan Kamera'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      <ConfirmModal
        isOpen={Boolean(deleteCamId)}
        title="Hapus Kamera"
        message={
          <div>
            <p>Apakah Anda yakin ingin menghapus konfigurasi kamera <strong>{selectedDeleteCam?.name}</strong>?</p>
            {selectedDeleteCam?.is_active && (
              <div className="mt-3 p-3 bg-rose-500/20 border border-rose-500/30 rounded-xl text-rose-300 text-xs flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
                <span>
                  <strong>Peringatan PENTING:</strong> Kamera ini saat ini berstatus <strong>Aktif Utama</strong>. Jika dihapus, sistem akan otomatis mengalihkan sumber video ke kamera standby tersisa.
                </span>
              </div>
            )}
          </div>
        }
        confirmText="Hapus Kamera"
        isDanger={true}
        onConfirm={handleDeleteCamera}
        onCancel={() => setDeleteCamId(null)}
      />
    </div>
  );
}

