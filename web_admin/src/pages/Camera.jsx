import React, { useState, useEffect } from 'react';
import { Camera as CameraIcon, Plus, CheckCircle, Trash2, Video } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api/client';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import ConfirmModal from '../components/ConfirmModal';

export default function Camera() {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
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

  const handleCreateCamera = async (e) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      await api.post('/api/admin/cameras', { name, source });
      toast.success(`Kamera ${name} berhasil ditambahkan!`);
      setShowModal(false);
      setName('');
      setSource('0');
      fetchCameras();
    } catch (err) {
      toast.error('Gagal menambah kamera');
    } finally {
      setSubmitting(false);
    }
  };

  const handleActivateCamera = async (id, name) => {
    try {
      await api.put(`/api/admin/cameras/${id}/activate`);
      toast.success(`Kamera ${name} diaktifkan sebagai sumber utama!`);
      fetchCameras();
    } catch (err) {
      toast.error('Gagal mengaktifkan kamera');
    }
  };

  const handleDeleteCamera = async () => {
    if (!deleteCamId) return;
    try {
      await api.delete(`/api/admin/cameras/${deleteCamId}`);
      toast.success('Kamera berhasil dihapus');
      fetchCameras();
    } catch (err) {
      toast.error('Gagal menghapus kamera');
    } finally {
      setDeleteCamId(null);
    }
  };

  const headers = ["# ID", "Nama Kamera", "Sumber (USB / RTSP URL)", "Status Aktif", "Aksi"];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Manajemen"
        highlightTitle="Kamera"
        subtitle="Konfigurasi perangkat masukan video/kamera inspeksi produksi"
        actionButton={
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm rounded-xl shadow-lg shadow-blue-600/30 transition-all"
          >
            <Plus className="w-4 h-4" />
            Tambah Kamera Baru
          </button>
        }
      />

      <div className="glass-card p-6 border border-white/10 rounded-2xl">
        <DataTable headers={headers} isLoading={loading}>
          {cameras.map((c) => (
            <tr key={c.id} className="hover:bg-white/5 transition-colors">
              <td className="p-4 text-xs font-mono text-slate-400">#{c.id}</td>
              <td className="p-4 font-bold text-white flex items-center gap-2">
                <Video className="w-4 h-4 text-blue-400" />
                {c.name}
              </td>
              <td className="p-4 font-mono text-xs text-amber-400">{c.source}</td>
              <td className="p-4">
                {c.is_active ? (
                  <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                    <CheckCircle className="w-3.5 h-3.5" />
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
                  onClick={() => setDeleteCamId(c.id)}
                  className="p-2 text-xs font-semibold text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-lg hover:bg-rose-500 hover:text-white transition-all"
                  title="Hapus Kamera"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </td>
            </tr>
          ))}
        </DataTable>
      </div>

      {/* Add Camera Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="w-full max-w-md p-6 glass-card border border-white/10 rounded-2xl shadow-2xl">
            <h3 className="text-xl font-bold text-white mb-4">Tambah Perangkat Kamera Baru</h3>

            <form onSubmit={handleCreateCamera} className="space-y-4">
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
                  className="w-full px-4 py-2.5 bg-black/30 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-blue-500"
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
                  className="w-full px-4 py-2.5 bg-black/30 border border-white/10 rounded-xl text-white font-mono text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-sm font-medium text-slate-300 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-lg shadow-lg shadow-blue-600/30 disabled:opacity-50"
                >
                  {submitting ? 'Memproses...' : 'Simpan Kamera'}
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
        message="Apakah Anda yakin ingin menghapus konfigurasi kamera ini?"
        confirmText="Hapus Kamera"
        isDanger={true}
        onConfirm={handleDeleteCamera}
        onCancel={() => setDeleteCamId(null)}
      />
    </div>
  );
}
