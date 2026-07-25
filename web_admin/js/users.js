const API_URL = '/api/admin/users';
const tbody = document.getElementById('users-body');
const modal = document.getElementById('user-modal');
const form = document.getElementById('user-form');
const btnAdd = document.getElementById('btn-add-user');
const btnCancel = document.getElementById('btn-cancel');

// Load Data
async function fetchUsers() {
    try {
        const res = await fetch(API_URL);
        const data = await res.json();
        renderUsers(data);
    } catch (e) {
        console.error("Failed to fetch users", e);
    }
}

function renderUsers(users) {
    tbody.innerHTML = '';
    
    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:#999;">Belum ada user. (Sistem menggunakan default PIN 1234)</td></tr>';
        return;
    }
    
    users.forEach(u => {
        const tr = document.createElement('tr');
        const roleStr = u.role === 'admin' ? '<span style="color:var(--primary); font-weight:bold;">Admin</span>' : '<span style="color:yellow; font-weight:bold;">Pengawas</span>';
        const activeStr = u.is_active ? '<span style="color:green;">Aktif</span>' : '<span style="color:red;">Nonaktif</span>';
        
        tr.innerHTML = `
            <td>${u.id}</td>
            <td><strong>${u.username}</strong></td>
            <td>${u.fullname}</td>
            <td>${roleStr}</td>
            <td>•••• (Tersembunyi)</td>
            <td>${activeStr}</td>
            <td>
                <button class="btn-primary" onclick="editUser(${u.id}, '${u.username}', '${u.fullname}', '${u.role}', ${u.is_active})" style="padding:5px 10px; font-size:12px;">Edit</button>
                <button class="btn-danger" onclick="deleteUser(${u.id}, '${u.username}')" style="padding:5px 10px; font-size:12px;">Hapus</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// Show/Hide Modal
btnAdd.onclick = () => {
    document.getElementById('modal-title').innerText = "Tambah User";
    document.getElementById('user-id').value = '';
    document.getElementById('password').required = true;
    document.getElementById('lbl-password').innerText = "PIN / Password (Wajib)";
    form.reset();
    modal.classList.add('show');
};

btnCancel.onclick = () => {
    modal.classList.remove('show');
};

// Add/Edit Submit
form.onsubmit = async (e) => {
    e.preventDefault();
    
    const id = document.getElementById('user-id').value;
    const isEdit = id !== '';
    
    const payload = {
        username: document.getElementById('username').value,
        fullname: document.getElementById('fullname').value,
        role: document.getElementById('role').value,
        is_active: document.getElementById('is-active').value === 'true'
    };
    
    const pwd = document.getElementById('password').value;
    if (pwd) payload.password = pwd; // Optional during edit

    try {
        const res = await fetch(isEdit ? `${API_URL}/${id}` : API_URL, {
            method: isEdit ? 'PUT' : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (res.ok) {
            modal.classList.remove('show');
            fetchUsers();
        } else {
            const err = await res.json();
            alert("Error: " + (err.detail || "Gagal menyimpan user"));
        }
    } catch (e) {
        console.error(e);
        alert("Gagal menghubungi server");
    }
};

// Global actions for onclick
window.editUser = (id, username, fullname, role, is_active) => {
    document.getElementById('modal-title').innerText = "Edit User";
    document.getElementById('user-id').value = id;
    document.getElementById('username').value = username;
    document.getElementById('fullname').value = fullname;
    document.getElementById('role').value = role;
    document.getElementById('is-active').value = is_active ? 'true' : 'false';
    
    document.getElementById('password').value = '';
    document.getElementById('password').required = false;
    document.getElementById('lbl-password').innerText = "PIN / Password (Kosongkan jika tidak ingin diubah)";
    
    modal.classList.add('show');
};

window.deleteUser = async (id, username) => {
    if (confirm(`Yakin ingin menghapus user: ${username}?`)) {
        try {
            const res = await fetch(`${API_URL}/${id}`, { method: 'DELETE' });
            if (res.ok) {
                fetchUsers();
            } else {
                alert("Gagal menghapus user");
            }
        } catch (e) {
            console.error(e);
            alert("Gagal menghubungi server");
        }
    }
};

window.keluarAdmin = () => {
    if (confirm("Keluar dari Admin Dashboard?")) {
        window.close();
        document.body.innerHTML = "<h2 style='color:white; text-align:center; margin-top:50px;'>Silakan tutup tab browser ini.</h2>";
    }
};

// Init
fetchUsers();
