import React, { useState, useEffect } from 'react';
import { Calendar, Search, Filter, RotateCcw, Download, Activity, CheckCircle, AlertOctagon, ChevronLeft, ChevronRight, Info } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api/client';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import StatCard from '../components/StatCard';

export default function History() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  // Filter states
  const [filterType, setFilterType] = useState('daily'); // 'daily' or 'monthly'
  const [dateFilter, setDateFilter] = useState('');
  const [monthFilter, setMonthFilter] = useState('');
  const [partFilter, setPartFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  // Pagination states
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 15;

  // Detail Modal state
  const [selectedLog, setSelectedLog] = useState(null);

  const fetchLogs = async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    try {
      const params = {};
      if (filterType === 'daily' && dateFilter) params.date_filter = dateFilter;
      if (filterType === 'monthly' && monthFilter) params.month_filter = monthFilter;
      if (partFilter) params.part_filter = partFilter;
      if (statusFilter && statusFilter !== 'ALL') params.status_filter = statusFilter;

      const res = await api.get('/api/admin/inspection-logs', { params });
      setLogs(res.data || []);
      if (!isSilent) setCurrentPage(1);
    } catch (err) {
      console.error('Failed to fetch inspection logs', err);
      if (!isSilent) toast.error('Gagal memuat log inspeksi');
    } finally {
      if (!isSilent) setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs(false);
    const interval = setInterval(() => {
      fetchLogs(true); // silent background update without spinner
    }, 2000);
    return () => clearInterval(interval);
  }, [filterType, dateFilter, monthFilter, statusFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchLogs();
  };

  const handleResetFilters = () => {
    setFilterType('daily');
    setDateFilter('');
    setMonthFilter('');
    setPartFilter('');
    setStatusFilter('ALL');
  };

  // Export to CSV
  const handleExportCSV = () => {
    if (logs.length === 0) return toast.error('Tidak ada data untuk diexport!');

    const headers = ["ID Log", "Waktu", "ID Transaksi", "Part Number", "Nama Part", "Lot No", "Unique No", "Target Qty", "Actual Qty", "Status Deteksi", "Confidence Score"];
    const rows = logs.map(l => [
      l.id,
      l.created_at ? new Date(l.created_at).toLocaleString() : '-',
      `"${l.id_trans || '-'}"`,
      `"${l.part_no || '-'}"`,
      `"${l.part_name || '-'}"`,
      `"${l.lot_no || '-'}"`,
      `"${l.unique_no || '-'}"`,
      l.target_qty ?? '-',
      l.qty_actual ?? '-',
      l.detection_status || 'OK',
      l.confidence_score !== undefined ? `${(l.confidence_score * 100).toFixed(0)}%` : '100%'
    ]);

    const csvContent = "\uFEFF" + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const dateSuffix = filterType === 'monthly' ? (monthFilter || 'Bulan_Ini') : (dateFilter || 'Hari_Ini');
    const filename = `Inspection_History_${dateSuffix}_${new Date().toISOString().slice(0, 10)}.csv`;

    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    toast.success(`Berhasil mengunduh ${logs.length} data ke ${filename}`);
  };

  // Summary Metrics
  const totalCount = logs.length;
  const okCount = logs.filter(l => (l.detection_status || 'OK').toUpperCase() === 'OK').length;
  const ngCount = logs.filter(l => (l.detection_status || '').toUpperCase() === 'NG').length;

  // Pagination Logic
  const totalPages = Math.ceil(logs.length / itemsPerPage) || 1;
  const startIdx = (currentPage - 1) * itemsPerPage;
  const currentLogs = logs.slice(startIdx, startIdx + itemsPerPage);

  const headers = ["# ID", "Waktu", "ID Trans", "Part No", "Target", "Aktual", "Status Deteksi", "Confidence", "Aksi"];

  return (
    <div className="space-y-6">
      <PageHeader
        title="History"
        highlightTitle="Inspeksi"
        subtitle="Riwayat hasil deteksi inspeksi kamera produksi"
        actionButton={
          <button
            onClick={handleExportCSV}
            disabled={logs.length === 0}
            className="flex items-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs rounded-xl shadow-lg shadow-emerald-600/30 transition-all disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            Export CSV / Excel
          </button>
        }
      />

      {/* Summary Stat Cards with Quick Filter Click */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard 
          title="Total Inspeksi (Semua)" 
          value={totalCount} 
          icon={Activity} 
          color="blue" 
          onClick={() => setStatusFilter('ALL')} 
        />
        <StatCard 
          title="Inspeksi OK (Berhasil)" 
          value={okCount} 
          icon={CheckCircle} 
          color="emerald" 
          onClick={() => setStatusFilter('OK')} 
        />
        <StatCard 
          title="Inspeksi NG (Cacat)" 
          value={ngCount} 
          icon={AlertOctagon} 
          color="rose" 
          onClick={() => setStatusFilter('NG')} 
        />
      </div>

      {/* Filter Bar */}
      <div className="glass-card p-4 border border-white/10 rounded-2xl">
        <form onSubmit={handleSearchSubmit} className="flex flex-wrap items-center gap-3">
          {/* Filter Type Toggle */}
          <div className="flex items-center bg-black/30 border border-white/10 rounded-xl p-1 text-xs">
            <button
              type="button"
              onClick={() => setFilterType('daily')}
              className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                filterType === 'daily' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
              }`}
            >
              Harian
            </button>
            <button
              type="button"
              onClick={() => setFilterType('monthly')}
              className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                filterType === 'monthly' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
              }`}
            >
              Bulanan
            </button>
          </div>

          {/* Date Picker (Harian) */}
          {filterType === 'daily' && (
            <div className="flex items-center gap-2 bg-black/30 border border-white/10 rounded-xl px-3 py-2 text-xs">
              <Calendar className="w-4 h-4 text-blue-400 shrink-0" />
              <input
                type="date"
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
                className="bg-transparent text-slate-200 outline-none cursor-pointer [color-scheme:dark]"
                title="Pilih Tanggal Inspeksi Harian"
              />
            </div>
          )}

          {/* Month Picker (Bulanan) */}
          {filterType === 'monthly' && (
            <div className="flex items-center gap-2 bg-black/30 border border-white/10 rounded-xl px-3 py-2 text-xs">
              <Calendar className="w-4 h-4 text-purple-400 shrink-0" />
              <input
                type="month"
                value={monthFilter}
                onChange={(e) => setMonthFilter(e.target.value)}
                className="bg-transparent text-slate-200 outline-none cursor-pointer [color-scheme:dark]"
                title="Pilih Bulan Inspeksi Bulanan"
              />
            </div>
          )}

          {/* Part No Search */}
          <div className="flex-1 min-w-[180px] flex items-center gap-2 bg-black/30 border border-white/10 rounded-xl px-3 py-2 text-xs">
            <Search className="w-4 h-4 text-slate-400 shrink-0" />
            <input
              type="text"
              placeholder="Cari Part No / ID Trans..."
              value={partFilter}
              onChange={(e) => setPartFilter(e.target.value)}
              className="w-full bg-transparent text-white placeholder-slate-500 outline-none"
            />
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-2 bg-black/30 border border-white/10 rounded-xl px-3 py-2 text-xs">
            <Filter className="w-4 h-4 text-amber-400 shrink-0" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-900 text-slate-200 outline-none cursor-pointer"
            >
              <option value="ALL">Semua Status</option>
              <option value="OK">OK (Berhasil)</option>
              <option value="NG">NG (Cacat)</option>
            </select>
          </div>

          <button
            type="submit"
            className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl shadow-lg shadow-blue-600/30 transition-all"
          >
            Cari
          </button>

          {(dateFilter || monthFilter || partFilter || statusFilter !== 'ALL') && (
            <button
              type="button"
              onClick={handleResetFilters}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-400 bg-white/5 border border-white/10 hover:bg-white/10 hover:text-white rounded-xl transition-all"
              title="Reset Filter"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset
            </button>
          )}
        </form>
      </div>

      {/* Table Section */}
      <div className="glass-card p-6 border border-white/10 rounded-2xl space-y-4">
        <DataTable headers={headers} isLoading={loading} center={true}>
          {currentLogs.map((item) => {
            const status = item.detection_status || item.status || 'OK';
            const conf = item.confidence_score !== undefined && item.confidence_score !== null
              ? (item.confidence_score * 100).toFixed(0) + '%'
              : (item.avg_confidence ? `${(item.avg_confidence * 100).toFixed(0)}%` : '100%');

            return (
              <tr key={item.id} className="hover:bg-white/5 transition-colors">
                <td className="p-4 text-xs font-mono text-slate-400 text-center">#{item.id}</td>
                <td className="p-4 text-xs text-slate-300 text-center">
                  {item.created_at ? new Date(item.created_at).toLocaleString('id-ID') : '-'}
                </td>
                <td className="p-4 font-mono font-medium text-slate-200 text-center cursor-pointer hover:text-white hover:underline" onClick={() => setSelectedLog(item)}>
                  {item.id_trans || '-'}
                </td>
                <td className="p-4 font-medium text-slate-200 text-center">{item.part_no || item.p_no || '-'}</td>
                <td className="p-4 font-medium text-slate-300 text-center">{item.target_qty ?? '-'}</td>
                <td className="p-4 font-medium text-slate-200 text-center">{item.qty_actual ?? '-'}</td>
                <td className="p-4 text-center"><StatusBadge status={status} /></td>
                <td className="p-4 font-mono font-medium text-slate-300 text-center">{conf}</td>
                <td className="p-4 text-center flex justify-center">
                  <button
                    onClick={() => setSelectedLog(item)}
                    className="p-1.5 text-xs text-slate-300 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 hover:text-white transition-all cursor-pointer"
                    title="Lihat Detail Log"
                  >
                    <Info className="w-3.5 h-3.5" />
                  </button>
                </td>
              </tr>
            );
          })}
        </DataTable>

        {/* Pagination & Count Bar */}
        {!loading && logs.length > 0 && (
          <div className="flex flex-col sm:flex-row items-center justify-between pt-4 border-t border-white/10 text-xs text-slate-400 gap-3">
            <div>
              Menampilkan <span className="font-semibold text-white">{startIdx + 1}</span> - <span className="font-semibold text-white">{Math.min(startIdx + itemsPerPage, logs.length)}</span> dari <span className="font-semibold text-white">{logs.length}</span> data
            </div>

            <div className="flex items-center gap-2">
              <button
                disabled={currentPage === 1}
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                className="p-2 rounded-lg bg-white/5 border border-white/10 text-slate-300 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="px-3 py-1 bg-black/30 border border-white/10 rounded-lg text-slate-200 font-medium">
                Halaman {currentPage} dari {totalPages}
              </span>
              <button
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                className="p-2 rounded-lg bg-white/5 border border-white/10 text-slate-300 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Log Detail Modal */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn" onClick={() => setSelectedLog(null)}>
          <div className="w-full max-w-2xl p-8 glass-card border border-white/15 rounded-3xl shadow-2xl space-y-6" onClick={e => e.stopPropagation()}>
            {/* Modal Header */}
            <div className="flex justify-between items-center pb-4 border-b border-white/10">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 text-slate-200">
                  <Info className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white tracking-wide">
                    Detail Log Inspeksi #{selectedLog.id}
                  </h3>
                  <p className="text-xs text-slate-400">Rincian data transaksi & hasil verifikasi kamera</p>
                </div>
              </div>
              <button 
                onClick={() => setSelectedLog(null)} 
                className="p-2.5 rounded-xl bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:bg-white/10 transition-all text-sm font-bold cursor-pointer"
                title="Tutup Modal"
              >
                ✕
              </button>
            </div>

            {/* Modal Content Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-black/30 p-4 rounded-2xl border border-white/5 space-y-1">
                <span className="block text-xs font-semibold uppercase tracking-wider text-slate-400">ID Transaksi</span>
                <span className="text-lg font-mono font-semibold text-white break-all">{selectedLog.id_trans || '-'}</span>
              </div>

              <div className="bg-black/30 p-4 rounded-2xl border border-white/5 space-y-1">
                <span className="block text-xs font-semibold uppercase tracking-wider text-slate-400">Part Number</span>
                <span className="text-lg font-semibold text-white">{selectedLog.part_no || selectedLog.p_no || '-'}</span>
              </div>

              <div className="bg-black/30 p-4 rounded-2xl border border-white/5 space-y-1 md:col-span-2">
                <span className="block text-xs font-semibold uppercase tracking-wider text-slate-400">Nama Part / Komponen</span>
                <span className="text-lg font-semibold text-white">{selectedLog.part_name || '-'}</span>
              </div>

              <div className="bg-black/30 p-4 rounded-2xl border border-white/5 space-y-1">
                <span className="block text-xs font-semibold uppercase tracking-wider text-slate-400">Nomor LOT (Lot No)</span>
                <span className="text-lg font-mono font-semibold text-white">{selectedLog.lot_no || '-'}</span>
              </div>

              <div className="bg-black/30 p-4 rounded-2xl border border-white/5 space-y-1">
                <span className="block text-xs font-semibold uppercase tracking-wider text-slate-400">Nomor Unik (Unique No)</span>
                <span className="text-lg font-mono font-semibold text-white">{selectedLog.unique_no || '-'}</span>
              </div>

              <div className="bg-black/30 p-4 rounded-2xl border border-white/5 space-y-1">
                <span className="block text-xs font-semibold uppercase tracking-wider text-slate-400">Target Qty</span>
                <span className="text-lg font-semibold text-slate-200">{selectedLog.target_qty ?? '-'}</span>
              </div>

              <div className="bg-black/30 p-4 rounded-2xl border border-white/5 space-y-1">
                <span className="block text-xs font-semibold uppercase tracking-wider text-slate-400">Qty Aktual</span>
                <span className="text-lg font-semibold text-slate-200">{selectedLog.qty_actual ?? '-'}</span>
              </div>

              <div className="bg-black/30 p-4 rounded-2xl border border-white/5 space-y-1">
                <span className="block text-xs font-semibold uppercase tracking-wider text-slate-400">Status Deteksi</span>
                <div className="pt-1">
                  <StatusBadge status={selectedLog.detection_status || 'OK'} />
                </div>
              </div>

              <div className="bg-black/30 p-4 rounded-2xl border border-white/5 space-y-1">
                <span className="block text-xs font-semibold uppercase tracking-wider text-slate-400">Confidence Score</span>
                <span className="text-lg font-mono font-semibold text-slate-200">
                  {selectedLog.confidence_score !== undefined ? `${(selectedLog.confidence_score * 100).toFixed(0)}%` : '100%'}
                </span>
              </div>

              <div className="bg-black/30 p-4 rounded-2xl border border-white/5 space-y-1 md:col-span-2">
                <span className="block text-xs font-semibold uppercase tracking-wider text-slate-400">Waktu Inspeksi</span>
                <span className="text-sm font-medium text-slate-200">
                  {selectedLog.created_at ? new Date(selectedLog.created_at).toLocaleString('id-ID', { dateStyle: 'full', timeStyle: 'medium' }) : '-'}
                </span>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setSelectedLog(null)}
                className="px-8 py-3 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl shadow-lg shadow-blue-600/30 transition-all cursor-pointer"
              >
                Tutup Informasi
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
