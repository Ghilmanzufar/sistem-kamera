import React, { useState, useEffect } from 'react';
import { Upload, Edit2, Trash2, Plus, FileCode, CheckCircle, Eye, Download, Info } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api/client';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import ConfirmModal from '../components/ConfirmModal';

export default function Models() {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingPartNo, setEditingPartNo] = useState(null);

  // Form State
  const [partNo, setPartNo] = useState('');
  const [file, setFile] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [labelPreview, setLabelPreview] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  // Detail Modal State
  const [selectedDetail, setSelectedDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Confirm Delete & Overwrite Modal States
  const [deletePartNo, setDeletePartNo] = useState(null);
  const [showOverwriteModal, setShowOverwriteModal] = useState(false);

  const fetchModels = async () => {
    try {
      const res = await api.get('/api/admin/models');
      setModels(res.data || []);
    } catch (err) {
      toast.error('Gagal mengambil daftar model');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  const openUploadModal = () => {
    setEditingPartNo(null);
    setPartNo('');
    setFile(null);
    setLabelPreview(null);
    setShowModal(true);
  };

  const openEditModal = (model) => {
    setEditingPartNo(model.part_no);
    setPartNo(model.part_no);
    setFile(null);
    setLabelPreview(null);
    setShowModal(true);
  };

  const handleFileChange = async (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;

    setFile(selectedFile);
    setPreviewLoading(true);
    setLabelPreview(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const res = await api.post('/api/admin/models/preview-labels', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setLabelPreview(res.data);
      if (res.data && res.data.labels) {
        const sorted = Object.entries(res.data.labels).sort((a, b) => parseInt(a[0]) - parseInt(b[0]));
        if (sorted.length > 0 && !editingPartNo) {
          const autoPno = String(sorted[0][1]).replace(/^[fr]-?/i, '');
          setPartNo(autoPno);
        }
      }
    } catch (err) {
      toast.error('Gagal membaca label dari file .pt');
    } finally {
      setPreviewLoading(false);
    }
  };

  const executeUpload = async () => {
    setShowOverwriteModal(false);
    setSubmitting(true);

    try {
      if (editingPartNo) {
        // Rename
        await api.put(`/api/admin/models/${editingPartNo}`, { new_part_no: partNo });
        toast.success(`Model berhasil diubah nama menjadi ${partNo}`);
      } else {
        // Upload
        const formData = new FormData();
        formData.append('part_no', partNo);
        formData.append('file', file);

        await api.post('/api/admin/models', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        toast.success(`Model ${partNo}.pt berhasil diunggah & diperbarui!`);
      }
      setShowModal(false);
      fetchModels();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Gagal menyimpan model');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!partNo) return toast.error('Masukkan Part Number!');
    if (!editingPartNo && !file) return toast.error('Pilih file .pt untuk diunggah!');

    if (!editingPartNo) {
      const isExisting = models.some(m => m.part_no.toLowerCase() === partNo.trim().toLowerCase());
      if (isExisting) {
        setShowOverwriteModal(true);
        return;
      }
    }

    executeUpload();
  };

  const handleOpenDetail = async (part_no) => {
    setDetailLoading(true);
    try {
      const res = await api.get(`/api/admin/models/${encodeURIComponent(part_no)}/detail`);
      setSelectedDetail(res.data);
    } catch (err) {
      toast.error('Gagal memuat detail model');
    } finally {
      setDetailLoading(false);
    }
  };

  const handleDownloadModel = (part_no) => {
    const downloadUrl = `/api/admin/models/${encodeURIComponent(part_no)}/download`;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.setAttribute('download', `${part_no}.pt`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success(`Mengunduh berkas ${part_no}.pt...`);
  };

  const handleDeleteModel = async () => {
    if (!deletePartNo) return;
    try {
      await api.delete(`/api/admin/models/${deletePartNo}`);
      toast.success(`Model ${deletePartNo}.pt telah dihapus`);
      fetchModels();
    } catch (err) {
      toast.error('Gagal menghapus model');
    } finally {
      setDeletePartNo(null);
    }
  };

  const headers = ["Part Number", "Nama File", "Ukuran File", "Waktu Update", "Status", "Aksi"];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Model"
        highlightTitle="AI (.pt)"
        subtitle="Manajemen berkas bobot model deteksi YOLOv8"
        actionButton={
          <button
            onClick={openUploadModal}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm rounded-xl shadow-lg shadow-blue-600/30 transition-all"
          >
            <Plus className="w-4 h-4" />
            Upload Model Baru
          </button>
        }
      />

      <div className="glass-card p-6 border border-white/10 rounded-2xl">
        <DataTable headers={headers} isLoading={loading} center={true}>
          {models.map((m) => (
            <tr key={m.part_no} className="hover:bg-white/5 transition-colors">
              <td className="p-4 font-bold text-white text-center">
                <div className="flex items-center justify-center gap-2 font-mono text-sm">
                  <FileCode className="w-4 h-4 text-blue-400 shrink-0" />
                  <span>{m.part_no}</span>
                </div>
              </td>
              <td className="p-4 text-slate-300 font-mono text-xs text-center">{m.filename}</td>
              <td className="p-4 text-center">
                <span className="inline-block px-2.5 py-1 bg-black/30 border border-white/10 rounded-lg font-mono text-xs font-semibold text-amber-400">
                  {m.size_mb} MB
                </span>
              </td>
              <td className="p-4 text-xs text-slate-300 font-mono text-center">
                {m.last_modified || '-'}
              </td>
              <td className="p-4 text-center">
                {m.is_active ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
                    Aktif
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium bg-white/5 text-slate-400 border border-white/10">
                    Ready
                  </span>
                )}
              </td>
              <td className="p-4 text-center">
                <div className="flex items-center justify-center gap-1.5">
                  {/* Detail Label Button */}
                  <button
                    onClick={() => handleOpenDetail(m.part_no)}
                    className="p-2 text-xs font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-lg hover:bg-emerald-500 hover:text-white transition-all"
                    title="Lihat Detail Label & Rule"
                  >
                    <Eye className="w-3.5 h-3.5" />
                  </button>

                  {/* Download Model Button */}
                  <button
                    onClick={() => handleDownloadModel(m.part_no)}
                    className="p-2 text-xs font-semibold text-purple-400 bg-purple-500/10 border border-purple-500/20 rounded-lg hover:bg-purple-500 hover:text-white transition-all"
                    title="Download File .pt"
                  >
                    <Download className="w-3.5 h-3.5" />
                  </button>

                  {/* Edit Name Button */}
                  <button
                    onClick={() => openEditModal(m)}
                    className="p-2 text-xs font-semibold text-blue-400 bg-blue-500/10 border border-blue-500/20 rounded-lg hover:bg-blue-500 hover:text-white transition-all"
                    title="Edit Nama Part"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>

                  {/* Delete Button */}
                  <button
                    onClick={() => setDeletePartNo(m.part_no)}
                    className="p-2 text-xs font-semibold text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-lg hover:bg-rose-500 hover:text-white transition-all"
                    title="Hapus Model"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </DataTable>
      </div>

      {/* Detail Model Labels Modal */}
      {selectedDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md" onClick={() => setSelectedDetail(null)}>
          <div className="w-full max-w-lg p-6 glass-card border border-white/10 rounded-2xl shadow-2xl space-y-4" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center pb-3 border-b border-white/10">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Info className="w-5 h-5 text-blue-400" />
                Detail Label Model {selectedDetail.part_no}.pt
              </h3>
              <button onClick={() => setSelectedDetail(null)} className="text-slate-400 hover:text-white font-bold">✕</button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-2 p-3 bg-black/30 border border-white/5 rounded-xl">
                <div>
                  <span className="text-slate-500 block">Ukuran File</span>
                  <span className="font-bold text-amber-400">{selectedDetail.size_mb} MB</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Terakhir Di-update</span>
                  <span className="font-mono text-slate-200">{selectedDetail.last_modified}</span>
                </div>
              </div>

              <div>
                <h4 className="font-semibold text-white mb-2 flex justify-between items-center">
                  <span>Daftar Komponen Wajib ({selectedDetail.komponen_count} label)</span>
                </h4>

                <div className="max-h-56 overflow-y-auto space-y-1.5 pr-1 scrollbar-thin">
                  {selectedDetail.komponen.length > 0 ? (
                    selectedDetail.komponen.map((c, i) => (
                      <div key={i} className="flex justify-between items-center p-2.5 bg-white/5 border border-white/5 rounded-lg text-slate-300">
                        <div className="flex items-center gap-2">
                          <span className="px-1.5 py-0.5 rounded bg-black/40 text-[10px] font-mono font-bold text-blue-300 uppercase">
                            Sisi: {c.sisi}
                          </span>
                          <span className="font-semibold text-white">{c.nama_komponen}</span>
                        </div>
                        <div className="text-right">
                          <span className="text-[10px] text-slate-400 block">Min Conf: {(c.min_confidence * 100).toFixed(0)}%</span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="p-4 text-center text-slate-500 italic">Belum ada rule khusus terdaftar di DB untuk part ini.</div>
                  )}
                </div>
              </div>
            </div>

            <div className="pt-2 flex justify-end gap-2">
              <button
                onClick={() => handleDownloadModel(selectedDetail.part_no)}
                className="px-3.5 py-2 text-xs font-semibold text-white bg-purple-600 hover:bg-purple-500 rounded-lg shadow-md flex items-center gap-1.5"
              >
                <Download className="w-3.5 h-3.5" />
                Download .pt
              </button>
              <button
                onClick={() => setSelectedDetail(null)}
                className="px-4 py-2 text-xs font-semibold text-slate-300 bg-white/5 border border-white/10 hover:bg-white/10 rounded-lg"
              >
                Tutup
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Upload/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="w-full max-w-lg p-6 glass-card border border-white/10 rounded-2xl shadow-2xl">
            <h3 className="text-xl font-bold text-white mb-4">
              {editingPartNo ? 'Rename Model Part' : 'Upload Model AI (.pt)'}
            </h3>

            <form onSubmit={handleSubmit} className="space-y-4">
              {!editingPartNo && (
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                    Berkas Model YOLO (.pt)
                  </label>
                  <input
                    type="file"
                    accept=".pt"
                    required
                    onChange={handleFileChange}
                    className="w-full p-2.5 bg-black/30 border border-white/10 rounded-xl text-white text-sm file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-500 cursor-pointer"
                  />
                </div>
              )}

              {previewLoading && (
                <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-300 text-xs animate-pulse">
                  ⏳ Membaca label dari berkas model...
                </div>
              )}

              {labelPreview && (
                <div className="p-4 rounded-xl bg-black/40 border border-white/10 text-xs space-y-2 max-h-48 overflow-y-auto">
                  <div className="font-semibold text-blue-400 flex items-center gap-1.5">
                    <CheckCircle className="w-4 h-4" />
                    Preview Label ({labelPreview.label_count} label ditemukan)
                  </div>
                  <div className="font-mono text-slate-300 space-y-1">
                    {Object.entries(labelPreview.labels || {}).map(([idx, name]) => (
                      <div key={idx} className="flex justify-between py-0.5 border-b border-white/5">
                        <span className="text-slate-500">ID #{idx}</span>
                        <span className="font-semibold text-emerald-400">{name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Part Number (Sesuai nama .pt)
                </label>
                <input
                  type="text"
                  required
                  value={partNo}
                  onChange={(e) => setPartNo(e.target.value)}
                  placeholder="Contoh: 74231-0K550-00"
                  className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-xl text-white font-mono text-sm focus:outline-none focus:border-blue-500"
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
                  {submitting ? 'Memproses...' : (editingPartNo ? 'Simpan Nama' : 'Unggah & Buat Rule')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Overwrite Confirmation Modal */}
      <ConfirmModal
        isOpen={showOverwriteModal}
        title="⚠️ Konfirmasi Menimpa Model AI"
        message={`Model AI untuk Part Number "${partNo}" sudah terdaftar di database. Apakah Anda yakin ingin MENIMPA berkas model lama dengan file baru ini?`}
        confirmText="Ya, Timpa Model"
        isDanger={true}
        onConfirm={executeUpload}
        onCancel={() => setShowOverwriteModal(false)}
      />

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={Boolean(deletePartNo)}
        title="Hapus Model AI"
        message={`Apakah Anda yakin ingin menghapus model ${deletePartNo}.pt? File akan dihapus permanen dari folder weights.`}
        confirmText="Hapus Permanen"
        isDanger={true}
        onConfirm={handleDeleteModel}
        onCancel={() => setDeletePartNo(null)}
      />
    </div>
  );
}
