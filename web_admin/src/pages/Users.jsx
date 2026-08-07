import React, { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, UserCheck, Shield } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api/client';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import ConfirmModal from '../components/ConfirmModal';

export default function Users() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);

  // Form State
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('pengawas');
  const [fullname, setFullname] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  // Confirm Delete
  const [deleteUserId, setDeleteUserId] = useState(null);

  const fetchUsers = async () => {
    try {
      const res = await api.get('/api/admin/users');
      setUsers(res.data || []);
    } catch (err) {
      toast.error('Gagal mengambil data user');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const openCreateModal = () => {
    setEditingUser(null);
    setUsername('');
    setPassword('');
    setRole('pengawas');
    setFullname('');
    setIsActive(true);
    setShowModal(true);
  };

  const openEditModal = (u) => {
    setEditingUser(u);
    setUsername(u.username);
    setPassword(''); // Kosongkan jika tidak ingin ganti password
    setRole(u.role);
    setFullname(u.fullname || '');
    setIsActive(u.is_active ?? true);
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);

    const payload = {
      username,
      role,
      fullname,
      is_active: isActive,
    };
    if (password) {
      payload.password = password;
    }

    try {
      if (editingUser) {
        await api.put(`/api/admin/users/${editingUser.id}`, payload);
        toast.success(`User ${username} berhasil diperbarui!`);
      } else {
        if (!password) return toast.error('PIN / Password wajib diisi untuk user baru!');
        await api.post('/api/admin/users', payload);
        toast.success(`User ${username} berhasil dibuat!`);
      }
      setShowModal(false);
      fetchUsers();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Gagal menyimpan data user');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteUser = async () => {
    if (!deleteUserId) return;
    try {
      await api.delete(`/api/admin/users/${deleteUserId}`);
      toast.success('User berhasil dihapus!');
      fetchUsers();
    } catch (err) {
      toast.error('Gagal menghapus user');
    } finally {
      setDeleteUserId(null);
    }
  };

  const headers = ["# ID", "Username", "Nama Lengkap", "Role", "Status", "Aksi"];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Manajemen"
        highlightTitle="User & PIN"
        subtitle="Kelola akun pengguna dan hak akses sistem inspeksi"
        actionButton={
          <button
            onClick={openCreateModal}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm rounded-xl shadow-lg shadow-blue-600/30 transition-all"
          >
            <Plus className="w-4 h-4" />
            Tambah User Baru
          </button>
        }
      />

      <div className="glass-card p-6 border border-white/10 rounded-2xl">
        <DataTable headers={headers} isLoading={loading}>
          {users.map((u) => (
            <tr key={u.id} className="hover:bg-white/5 transition-colors">
              <td className="p-4 text-xs font-mono text-slate-400">#{u.id}</td>
              <td className="p-4 font-bold text-white flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-blue-400" />
                {u.username}
              </td>
              <td className="p-4 text-slate-300 text-sm">{u.fullname || '-'}</td>
              <td className="p-4">
                <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold uppercase border ${
                  u.role === 'pengawas'
                    ? 'bg-blue-500/20 text-blue-300 border-blue-500/30'
                    : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                }`}>
                  <Shield className="w-3 h-3" />
                  {u.role}
                </span>
              </td>
              <td className="p-4">
                <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                  u.is_active ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                }`}>
                  {u.is_active ? 'Aktif' : 'Non-Aktif'}
                </span>
              </td>
              <td className="p-4 flex items-center gap-2">
                <button
                  onClick={() => openEditModal(u)}
                  className="p-2 text-xs font-semibold text-blue-400 bg-blue-500/10 border border-blue-500/20 rounded-lg hover:bg-blue-500 hover:text-white transition-all"
                  title="Edit User"
                >
                  <Edit className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setDeleteUserId(u.id)}
                  className="p-2 text-xs font-semibold text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-lg hover:bg-rose-500 hover:text-white transition-all"
                  title="Hapus User"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </td>
            </tr>
          ))}
        </DataTable>
      </div>

      {/* User Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
          <div className="w-full max-w-xl p-8 glass-card border border-white/15 rounded-3xl shadow-2xl space-y-6">
            <h3 className="text-2xl font-bold text-white mb-6">
              {editingUser ? `Edit User: ${editingUser.username}` : 'Tambah User Baru'}
            </h3>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                  Username
                </label>
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-xl text-white text-base focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                  Nama Lengkap
                </label>
                <input
                  type="text"
                  value={fullname}
                  onChange={(e) => setFullname(e.target.value)}
                  className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-xl text-white text-base focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                  PIN / Password {editingUser && '(Biarkan kosong jika tidak diubah)'}
                </label>
                <input
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-xl text-white text-base focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                  Role Sistem
                </label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full px-4 py-3 bg-slate-900 border border-white/10 rounded-xl text-white text-base focus:outline-none focus:border-blue-500"
                >
                  <option value="pengawas">Pengawas (Akses Penuh)</option>
                  <option value="operator">Operator (History Inspeksi Only)</option>
                </select>
              </div>

              <div className="flex items-center gap-3 pt-2">
                <input
                  type="checkbox"
                  id="isActiveCheck"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="w-5 h-5 rounded bg-black/30 border-white/10 text-blue-600 focus:ring-0 cursor-pointer"
                />
                <label htmlFor="isActiveCheck" className="text-base font-semibold text-slate-300 cursor-pointer">
                  Status Akun Aktif
                </label>
              </div>

              <div className="flex justify-end gap-3 pt-6">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-6 py-2.5 text-base font-semibold text-slate-300 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-6 py-2.5 text-base font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl shadow-lg shadow-blue-600/30 disabled:opacity-50"
                >
                  {submitting ? 'Memproses...' : 'Simpan User'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete User Modal */}
      <ConfirmModal
        isOpen={Boolean(deleteUserId)}
        title="Hapus Akun User"
        message="Apakah Anda yakin ingin menghapus user ini? Tindakan ini tidak dapat dibatalkan."
        confirmText="Hapus User"
        isDanger={true}
        onConfirm={handleDeleteUser}
        onCancel={() => setDeleteUserId(null)}
      />
    </div>
  );
}
