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

let existingPartNos = new Set();

function renderModels(models) {
    existingPartNos = new Set(models.map(m => m.part_no));
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

// --- Label Preview ---
const labelPreview = document.getElementById('label-preview');
const labelPreviewContent = document.getElementById('label-preview-content');

function resetLabelPreview() {
    labelPreview.style.display = 'none';
    labelPreviewContent.innerHTML = '';
}

function renderLabelPreview(data) {
    const { label_count, labels } = data;
    const sortedEntries = Object.entries(labels || {}).sort((a, b) => parseInt(a[0]) - parseInt(b[0]));
    if (sortedEntries.length > 0) {
        document.getElementById('input-model-pno').value = String(sortedEntries[0][1]).replace(/^[fr]-?/i, '');
    }
    // Bangun baris: "Label  0 : klip_kuning"
    const rows = sortedEntries
        .map(([idx, name], i) => {
            const prefix = i === 0
                ? `<strong>Label</strong>&nbsp;&nbsp;`
                : `<span style="visibility:hidden">Label</span>&nbsp;&nbsp;`;
            return `<div style="font-family: monospace; white-space: pre;">  ${prefix}<strong>${idx}</strong> : ${name}</div>`;
        })
        .join('');

    labelPreviewContent.innerHTML = `
        <div style="margin-bottom: 6px; color: #a0cfff; font-weight: 600; font-size: 0.8rem; letter-spacing: 0.05em; text-transform: uppercase;">
            📋 Label Preview (dari model)
        </div>
        <div style="margin-bottom: 4px;">Jumlah label : <strong>${label_count}</strong></div>
        <div style="border-top: 1px solid rgba(255,255,255,0.1); padding-top: 6px; margin-top: 4px;">
            ${rows}
        </div>
    `;
    labelPreview.style.display = 'block';
}

document.getElementById('input-model-file').addEventListener('change', async function () {
    const file = this.files[0];
    if (!file) { resetLabelPreview(); return; }

    // Tampilkan loading
    labelPreviewContent.innerHTML = '<span style="color:#aaa;">⏳ Membaca label dari file...</span>';
    labelPreview.style.display = 'block';

    const fd = new FormData();
    fd.append('file', file);

    try {
        const res = await fetch(`${API_URL}/preview-labels`, { method: 'POST', body: fd });
        const data = await res.json();

        if (!res.ok) {
            labelPreviewContent.innerHTML = `<span style="color:#ff7070;">⚠️ ${data.detail || 'Gagal membaca label'}</span>`;
            return;
        }
        renderLabelPreview(data);
    } catch (e) {
        labelPreviewContent.innerHTML = '<span style="color:#ff7070;">⚠️ Gagal terhubung ke server.</span>';
        console.error(e);
    }
});

// --- Modal open/close ---
document.getElementById('btn-add-model').onclick = () => {
    form.reset();
    resetLabelPreview();
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

    if (existingPartNos.has(p_no)) {
        document.getElementById('confirm-message').innerHTML = `Model untuk Part Number <strong style="color:#a0cfff;">"${p_no}"</strong> sudah terinstall di sistem.<br><br>Mau ganti baru atau pakai yang lama?`;
        document.getElementById('confirm-modal').classList.remove('hidden');
        
        document.getElementById('btn-confirm-old').onclick = () => {
            document.getElementById('confirm-modal').classList.add('hidden');
        };
        document.getElementById('btn-confirm-new').onclick = () => {
            document.getElementById('confirm-modal').classList.add('hidden');
            performUpload(p_no, file);
        };
        return;
    }

    performUpload(p_no, file);
};

async function performUpload(p_no, file) {
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
}

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

