const API_URL = '/api/admin/rules';
const API_URL_TRANS = '/api/admin/transactions';
const tbody = document.getElementById('rules-body');
const tbody_trans = document.getElementById('transactions-body');
const modal = document.getElementById('rule-modal');
const form = document.getElementById('rule-form');
const compContainer = document.getElementById('components-container');

let currentRules = [];

// --- TAB NAVIGATION LOGIC ---
function switchTab(tabId) {
    document.querySelectorAll('.nav-tabs button').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    
    document.getElementById(`tab-${tabId}`).classList.add('active');
    document.getElementById(`view-${tabId}`).classList.add('active');
}

// --- DASHBOARD LOGIC ---
async function fetchTransactions() {
    try {
        const res = await fetch(API_URL_TRANS);
        const data = await res.json();
        renderTransactions(data);
    } catch (e) {
        console.error("Failed to fetch transactions", e);
    }
}

function renderTransactions(trans) {
    if (!tbody_trans) return; // Prevent error if element not ready
    tbody_trans.innerHTML = '';
    trans.forEach(t => {
        let statusBadge = t.status === 2 
            ? '<span class="status-badge status-selesai">Selesai</span>'
            : '<span class="status-badge status-running">Running</span>';
            
        let startTime = t.start_time ? new Date(t.start_time).toLocaleTimeString() : '-';
        
        tbody_trans.innerHTML += `
            <tr>
                <td>${t.id_trans}</td>
                <td>${t.part_no || '-'}</td>
                <td>${t.part_name || '-'}</td>
                <td>${t.target_qty}</td>
                <td>${t.qty_actual}</td>
                <td>${statusBadge}</td>
                <td>${startTime}</td>
            </tr>
        `;
    });
}

// Polling for Dashboard Every 3 seconds
setInterval(fetchTransactions, 3000);

async function fetchRules() {
    try {
        const res = await fetch(API_URL);
        currentRules = await res.json();
        renderRules(currentRules);
    } catch (e) {
        console.error("Failed to fetch rules", e);
    }
}

function renderRules(rules) {
    tbody.innerHTML = '';
    rules.forEach(r => {
        let compHtml = r.komponen.map(k => 
            `<span style="background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 4px; display: inline-block; margin: 2px;">
                Sisi <b>${k.sisi}</b> : ${k.nama_komponen} (Qty: ${k.qty})
            </span>`
        ).join('<br>');
        
        if(!compHtml) compHtml = '<span style="color: #666;">Tidak ada komponen</span>';

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${r.p_no}</strong></td>
            <td>${compHtml}</td>
            <td>
                <button class="btn-primary" onclick="editRule('${r.p_no}')" style="margin-right: 5px; padding: 5px 10px;">Edit</button>
                <button class="btn-danger" onclick="deleteRule('${r.p_no}')" style="padding: 5px 10px;">Hapus</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function createComponentRow(sisi = 'Depan', nama = '', qty = '') {
    const div = document.createElement('div');
    div.className = 'component-row';
    div.innerHTML = `
        <select class="comp-sisi" required style="width: 120px;">
            <option value="Depan" ${sisi === 'Depan' ? 'selected' : ''}>Depan</option>
            <option value="Belakang" ${sisi === 'Belakang' ? 'selected' : ''}>Belakang</option>
        </select>
        <input type="text" placeholder="Nama Komponen (e.g. bodypart)" class="comp-nama" value="${nama}" required style="flex-grow: 1;">
        <input type="number" placeholder="Qty" class="comp-qty" value="${qty}" required style="width: 80px;" min="1">
        <button type="button" class="btn-danger btn-remove-comp" style="padding: 10px;">X</button>
    `;
    div.querySelector('.btn-remove-comp').onclick = () => div.remove();
    return div;
}

document.getElementById('btn-add-comp').onclick = () => {
    compContainer.appendChild(createComponentRow());
};

document.getElementById('btn-add-rule').onclick = () => {
    form.reset();
    document.getElementById('input-pno').disabled = false;
    compContainer.innerHTML = ''; // bersihkan komponen
    compContainer.appendChild(createComponentRow()); // tambah 1 baris kosong
    document.getElementById('modal-title').innerText = "Tambah Rule";
    modal.classList.remove('hidden');
};

document.getElementById('btn-cancel').onclick = () => {
    modal.classList.add('hidden');
};

form.onsubmit = async (e) => {
    e.preventDefault();
    const p_no = document.getElementById('input-pno').value;
    
    // Ambil data komponen
    const rows = document.querySelectorAll('.component-row');
    const komponen = [];
    rows.forEach(row => {
        komponen.push({
            sisi: row.querySelector('.comp-sisi').value,
            nama_komponen: row.querySelector('.comp-nama').value,
            qty: parseInt(row.querySelector('.comp-qty').value)
        });
    });

    if (komponen.length === 0) {
        alert("Pilih minimal 1 komponen!");
        return;
    }

    const res = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ p_no, komponen: komponen })
    });
    
    if (res.ok) {
        modal.classList.add('hidden');
        fetchRules();
    } else {
        alert("Gagal menyimpan rule");
    }
};

window.deleteRule = async (p_no) => {
    if(!confirm(`Hapus rule untuk part ${p_no}?`)) return;
    const res = await fetch(`${API_URL}/${p_no}`, { method: 'DELETE' });
    if (res.ok) {
        fetchRules();
    }
};

window.editRule = (p_no) => {
    const rule = currentRules.find(r => r.p_no === p_no);
    if (!rule) return;
    
    document.getElementById('modal-title').innerText = "Edit Rule";
    const pnoInput = document.getElementById('input-pno');
    pnoInput.value = rule.p_no;
    pnoInput.disabled = true; // Kunci Part Number saat edit
    
    compContainer.innerHTML = '';
    rule.komponen.forEach(k => {
        compContainer.appendChild(createComponentRow(k.sisi, k.nama_komponen, k.qty));
    });
    
    modal.classList.remove('hidden');
};

window.keluarAdmin = () => {
    if (confirm("Keluar dari Admin Dashboard?")) {
        // Coba tutup tab. Jika diblokir browser, tampilkan pesan.
        window.close();
        document.body.innerHTML = "<h2 style='color:white; text-align:center; margin-top:50px;'>Silakan tutup tab browser ini.</h2>";
    }
};

// Start
fetchRules();
fetchTransactions();
