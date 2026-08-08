import React, { useState, useEffect } from 'react';
import { FileText, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api/client';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';

export default function Logs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchLogs = async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    try {
      const res = await api.get('/api/admin/audit-logs');
      setLogs(res.data || []);
    } catch (err) {
      if (!isSilent) toast.error('Gagal mengambil audit log');
    } finally {
      if (!isSilent) setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs(false);
    const interval = setInterval(() => {
      fetchLogs(true);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  const headers = ["# ID", "Waktu", "Username", "Aksi", "Detail Aktivitas"];

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const cleanStr = typeof dateStr === 'string' ? dateStr.replace(' ', 'T') : dateStr;
    const d = new Date(cleanStr);
    return isNaN(d.getTime()) ? String(dateStr) : d.toLocaleString('id-ID');
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="System"
        highlightTitle="Audit Logs"
        subtitle="Catatan jejak aktivitas operasional dan keamanan pengguna di Web Admin"
        actionButton={
          <button
            onClick={fetchLogs}
            className="flex items-center gap-2 px-3 py-2 bg-white/5 border border-white/10 hover:bg-white/10 text-slate-300 font-semibold text-xs rounded-xl transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh Log
          </button>
        }
      />

      <div className="glass-card p-6 border border-white/10 rounded-2xl">
        <DataTable headers={headers} isLoading={loading} maxHeight="550px">
          {logs.map((item) => (
            <tr key={item.id} className="hover:bg-white/5 transition-colors">
              <td className="p-4 text-xs font-mono text-slate-400 text-center">#{item.id}</td>
              <td className="p-4 text-xs text-slate-300 whitespace-nowrap text-center">
                {formatDate(item.timestamp || item.created_at)}
              </td>
              <td className="p-4 font-bold text-white text-xs text-center">
                <div className="flex items-center justify-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                  <span>{item.username}</span>
                </div>
              </td>
              <td className="p-4 text-center"><StatusBadge status={item.action} /></td>
              <td className="p-4 text-xs text-slate-300 text-center">{item.details || '-'}</td>
            </tr>
          ))}
        </DataTable>
      </div>
    </div>
  );
}
