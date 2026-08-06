import React, { useState, useEffect } from 'react';
import { Image as ImageIcon, Eye } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api/client';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import ImagePreviewModal from '../components/ImagePreviewModal';

export default function NgHistory() {
  const [ngRecords, setNgRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedImage, setSelectedImage] = useState(null);

  const fetchNgHistory = async () => {
    try {
      const res = await api.get('/api/admin/ng-history');
      setNgRecords(res.data || []);
    } catch (err) {
      toast.error('Gagal mengambil daftar foto NG');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNgHistory();
  }, []);

  const headers = ["#", "Part Number", "Nama File Foto NG", "Tanggal & Waktu", "Ukuran Berkas", "Preview"];

  return (
    <div className="space-y-6">
      <PageHeader
        title="History"
        highlightTitle="NG Records"
        subtitle="Daftar berkas foto cacat fisik hasil temuan inspeksi kamera"
      />

      <div className="glass-card p-6 border border-white/10 rounded-2xl">
        <DataTable headers={headers} isLoading={loading} center={true}>
          {ngRecords.map((item, idx) => {
            const imgUrl = item.image_url || `/ng_records/${item.filename}`;
            return (
              <tr key={item.filename || idx} className="hover:bg-white/5 transition-colors">
                <td className="p-4 text-xs font-mono text-slate-400 text-center">#{idx + 1}</td>
                <td className="p-4 font-bold text-white text-center">{item.part_no || '-'}</td>
                <td className="p-4 font-mono text-xs font-bold text-rose-400 text-center">
                  <div className="flex items-center justify-center gap-2">
                    <ImageIcon className="w-4 h-4 text-rose-400 shrink-0" />
                    <span>{item.filename}</span>
                  </div>
                </td>
                <td className="p-4 text-xs text-slate-300 text-center font-mono">
                  {item.created_at ? new Date(item.created_at).toLocaleString() : '-'}
                </td>
                <td className="p-4 text-center">
                  <span className="inline-block px-2.5 py-1 bg-black/30 border border-white/10 rounded-lg font-mono text-xs font-semibold text-amber-400">
                    {item.size_mb ? `${item.size_mb} MB` : '-'}
                  </span>
                </td>
                <td className="p-4 text-center">
                  <div className="flex justify-center">
                    <button
                      onClick={() => setSelectedImage({ url: imgUrl, title: item.filename })}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-blue-400 bg-blue-500/10 border border-blue-500/20 rounded-lg hover:bg-blue-500 hover:text-white transition-all"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      Lihat Foto
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </DataTable>
      </div>

      <ImagePreviewModal
        isOpen={Boolean(selectedImage)}
        imageUrl={selectedImage?.url}
        title={selectedImage?.title}
        onClose={() => setSelectedImage(null)}
      />
    </div>
  );
}
