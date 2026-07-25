const API_URL = '/api/admin/models';
const tbody = document.getElementById('models-body');
const modal = document.getElementById('model-modal');
const form = document.getElementById('model-form');

async function fetchModels() {
    try {
        const res = await fetch(API_URL);
        const data = await res.json();
        renderModels(data);
    } catch (e) {
        console.error("Failed to fetch models", e);
    }
}

function renderModels(models) {
    tbody.innerHTML = '';
    
    if (models.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#999;">Belum ada model yang diunggah.</td></tr>';
        return;
    }
    
    models.forEach(m => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${m.part_no}</strong></td>
            <td>${m.filename}</td>
            <td>${m.size_mb} MB</td>
            <td>
                <button class="btn-primary" onclick="editModel('${m.part_no}')" style="margin-right: 5px; padding: 5px 10px;">Edit</button>
                <button class="btn-danger" onclick="deleteModel('${m.part_no}')" style="padding: 5px 10px;">Hapus</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

document.getElementById('btn-add-model').onclick = () => {
    form.reset();
    modal.classList.remove('hidden');
};

document.getElementById('btn-cancel').onclick = () => {
    modal.classList.add('hidden');
};

form.onsubmit = async (e) => {
    e.preventDefault();
    const p_no = document.getElementById('input-model-pno').value;
    const fileInput = document.getElementById('input-model-file');
    const file = fileInput.files[0];

    if (!file) {
        alert("Silakan pilih file .pt!");
        return;
    }

    const formData = new FormData();
    formData.append('part_no', p_no);
    formData.append('file', file);

    const btnSubmit = form.querySelector('button[type="submit"]');
    btnSubmit.innerText = "Mengunggah...";
    btnSubmit.disabled = true;

    try {
        const res = await fetch(API_URL, {
            method: 'POST',
            body: formData
        });
        
        const data = await res.json();
        
        if (res.ok) {
            modal.classList.add('hidden');
            fetchModels();
        } else {
            alert(data.detail || "Gagal mengunggah model");
        }
    } catch (err) {
        alert("Terjadi kesalahan saat mengunggah model.");
        console.error(err);
    } finally {
        btnSubmit.innerText = "Upload";
        btnSubmit.disabled = false;
    }
};

const renameModal = document.getElementById('rename-modal');
const renameForm = document.getElementById('rename-form');

window.editModel = (old_p_no) => {
    document.getElementById('input-rename-old-pno').value = old_p_no;
    document.getElementById('input-rename-new-pno').value = old_p_no;
    renameModal.classList.remove('hidden');
};

document.getElementById('btn-rename-cancel').onclick = () => {
    renameModal.classList.add('hidden');
};

renameForm.onsubmit = async (e) => {
    e.preventDefault();
    const old_p_no = document.getElementById('input-rename-old-pno').value;
    const newName = document.getElementById('input-rename-new-pno').value;
    
    if (!newName || newName === old_p_no) {
        renameModal.classList.add('hidden');
        return;
    }
    
    const btnSubmit = renameForm.querySelector('button[type="submit"]');
    btnSubmit.innerText = "Menyimpan...";
    btnSubmit.disabled = true;

    try {
        const res = await fetch(`${API_URL}/${old_p_no}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ new_part_no: newName })
        });
        const data = await res.json();
        
        if (res.ok) {
            renameModal.classList.add('hidden');
            fetchModels();
        } else {
            alert(data.detail || "Gagal mengubah nama model");
        }
    } catch (err) {
        console.error(err);
        alert("Terjadi kesalahan.");
    } finally {
        btnSubmit.innerText = "Simpan";
        btnSubmit.disabled = false;
    }
};

window.deleteModel = async (p_no) => {
    if(!confirm(`Yakin ingin menghapus model untuk part ${p_no}?`)) return;
    try {
        const res = await fetch(`${API_URL}/${p_no}`, { method: 'DELETE' });
        if (res.ok) {
            fetchModels();
        } else {
            alert("Gagal menghapus model");
        }
    } catch (e) {
        console.error(e);
    }
};

window.keluarAdmin = () => {
    if (confirm("Keluar dari Admin Dashboard?")) {
        window.close();
        document.body.innerHTML = "<h2 style='color:white; text-align:center; margin-top:50px;'>Silakan tutup tab browser ini.</h2>";
    }
};

// Start
fetchModels();
