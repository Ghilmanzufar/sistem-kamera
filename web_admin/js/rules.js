const API_URL = '/api/admin/rules';
const tbody = document.getElementById('rules-body');
const modal = document.getElementById('rule-modal');
const form = document.getElementById('rule-form');
const compContainer = document.getElementById('components-container');

// Global Rule Modal elements
const globalModal = document.getElementById('global-rule-modal');
const globalForm = document.getElementById('global-rule-form');
const btnGlobalRule = document.getElementById('btn-global-rule');
const btnGlobalCancel = document.getElementById('btn-global-cancel');

let currentRules = [];

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
    
    if (!rules || rules.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#999; padding: 2rem;">Belum ada rule yang dibuat. Klik <b>+ Tambah Rule</b> di atas.</td></tr>';
        return;
    }

    rules.forEach(r => {
        const avgConf = r.avg_confidence !== undefined && r.avg_confidence !== null ? r.avg_confidence : 0.75;
        const minCov = r.min_coverage !== undefined && r.min_coverage !== null ? r.min_coverage : 1.0;
        
        let compHtml = r.komponen.map(k => {
            const minConf = k.min_confidence !== undefined && k.min_confidence !== null ? k.min_confidence : 0.70;
            const sideBadge = getSideBadge(k.nama_komponen);
            return `<div style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); padding: 5px 12px; border-radius: 8px; display: inline-flex; align-items: center; gap: 8px; margin: 3px 4px 3px 0;">
                ${sideBadge}
                <span style="color: #f8fafc; font-weight: 600; font-size: 0.9rem;">🏷️ ${k.nama_komponen}</span>
                <span style="background: rgba(53, 200, 240, 0.15); border: 1px solid rgba(53, 200, 240, 0.3); color: #35c8f0; padding: 2px 8px; border-radius: 6px; font-size: 0.8rem; font-weight: 700;">Min: ${(minConf * 100).toFixed(0)}%</span>
            </div>`;
        }).join('');
        
        if (!compHtml) compHtml = '<span style="color: #64748b;">Tidak ada label</span>';

        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid rgba(255,255,255,0.08)';
        
        tr.innerHTML = `
            <td style="white-space: nowrap; font-weight: bold; font-size: 1rem; color: #f8fafc;">${r.p_no}</td>
            <td style="white-space: nowrap;">
                <span style="background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); color: #3b82f6; padding: 5px 12px; border-radius: 8px; font-weight: 800; font-size: 0.95rem;">
                    ${(minCov * 100).toFixed(0)}%
                </span>
            </td>
            <td style="white-space: nowrap;">
                <span style="background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.3); color: #22c55e; padding: 5px 12px; border-radius: 8px; font-weight: 800; font-size: 0.95rem;">
                    ${(avgConf * 100).toFixed(0)}%
                </span>
            </td>
            <td style="vertical-align: middle;">${compHtml}</td>
            <td style="white-space: nowrap; text-align: right;">
                <button class="btn-primary" onclick="editRule('${r.p_no}')" style="margin-right: 6px; padding: 6px 14px; font-size: 0.85rem; border-radius: 8px;">Edit</button>
                <button class="btn-danger" onclick="deleteRule('${r.p_no}')" style="padding: 6px 14px; font-size: 0.85rem; border-radius: 8px;">Hapus</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// Badge sisi otomatis berdasarkan prefix label
function getSideBadge(nama) {
    const n = (nama || '').toLowerCase();
    if (n.startsWith('f-')) return `<span style="background:rgba(34,197,94,0.2); color:#22c55e; font-size:0.72rem; font-weight:800; padding:1px 6px; border-radius:4px; border:1px solid rgba(34,197,94,0.4);">F</span>`;
    if (n.startsWith('r-')) return `<span style="background:rgba(245,158,11,0.2); color:#f59e0b; font-size:0.72rem; font-weight:800; padding:1px 6px; border-radius:4px; border:1px solid rgba(245,158,11,0.4);">R</span>`;
    return `<span style="background:rgba(100,116,139,0.2); color:#94a3b8; font-size:0.72rem; font-weight:800; padding:1px 6px; border-radius:4px; border:1px solid rgba(100,116,139,0.4);">—</span>`;
}

function createComponentRow(nama = '', minConf = 0.70) {
    const div = document.createElement('div');
    div.className = 'component-row';
    div.style.display = 'flex';
    div.style.gap = '10px';
    div.style.marginBottom = '10px';
    div.style.alignItems = 'center';

    div.innerHTML = `
        <input type="text" placeholder="Nama Label (misal: klip_kuning)" class="comp-nama" value="${nama}" required style="flex-grow: 1; padding: 8px 12px; border-radius: 8px; background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.15); color: #fff;">
        <div style="display: flex; align-items: center; gap: 6px;">
            <label style="font-size: 0.85rem; margin: 0; color: #94a3b8;">Min Conf (%):</label>
            <input type="number" placeholder="70" class="comp-min-conf" value="${(minConf * 100).toFixed(0)}" required style="width: 85px; padding: 8px; border-radius: 8px; background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.15); color: #fff;" step="1" min="0" max="100">
        </div>
        <button type="button" class="btn-danger btn-remove-comp" style="padding: 8px 12px; border-radius: 8px;">✕</button>
    `;
    div.querySelector('.btn-remove-comp').onclick = () => div.remove();
    return div;
}

document.getElementById('btn-add-comp').onclick = () => {
    compContainer.appendChild(createComponentRow());
};

// Tombol Auto Load Label dari Model .pt
document.getElementById('btn-auto-load-model').onclick = async () => {
    const p_no = document.getElementById('input-pno').value.trim();
    if (!p_no) {
        alert("Ketikkan Part Number terlebih dahulu!");
        return;
    }
    
    try {
        const rulesRes = await fetch(API_URL);
        const rules = await rulesRes.json();
        const rule = rules.find(r => r.p_no === p_no);
        
        compContainer.innerHTML = '';
        if (rule && rule.komponen && rule.komponen.length > 0) {
            rule.komponen.forEach(k => {
                compContainer.appendChild(createComponentRow(k.nama_komponen, k.min_confidence || 0.70));
            });
            document.getElementById('input-avg-conf').value = rule.avg_confidence ? (rule.avg_confidence * 100).toFixed(0) : 75;
            document.getElementById('input-min-coverage').value = rule.min_coverage ? (rule.min_coverage * 100).toFixed(0) : 100;
            showAlertModal(`✅ ${rule.komponen.length} label berhasil dimuat untuk Part ${p_no}`);
        } else {
            showAlertModal(`Rule untuk ${p_no} belum tersimpan. Saat mengunggah file model ${p_no}.pt di menu Model AI (.pt), label akan otomatis dimuat ke sini.`);
        }
    } catch(e) {
        showAlertModal("Error loading label dari .pt: " + e, true);
    }
};

// Modal Handling
document.getElementById('btn-cancel').onclick = () => {
    modal.classList.add('hidden');
};

form.onsubmit = async (e) => {
    e.preventDefault();
    const p_no = document.getElementById('input-pno').value.trim();
    const avg_confidence = parseFloat(document.getElementById('input-avg-conf').value) / 100;
    const min_coverage = parseFloat(document.getElementById('input-min-coverage').value) / 100;
    
    const rows = document.querySelectorAll('.component-row');
    const komponen = [];
    rows.forEach(row => {
        const nama = row.querySelector('.comp-nama').value.trim();
        const minConf = parseFloat(row.querySelector('.comp-min-conf').value) / 100;
        if (nama) {
            komponen.push({
                sisi: "-",
                nama_komponen: nama,
                qty: 1,
                min_confidence: isNaN(minConf) ? 0.70 : minConf
            });
        }
    });

    if (komponen.length === 0) {
        showAlertModal("Pilih minimal 1 label komponen!", true);
        return;
    }

    try {
        const res = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                p_no: p_no,
                avg_confidence: isNaN(avg_confidence) ? 0.75 : avg_confidence,
                min_coverage: isNaN(min_coverage) ? 1.0 : min_coverage,
                komponen: komponen
            })
        });
        
        if(res.ok) {
            showAlertModal("Sukses! Rule berhasil disimpan.");
            modal.classList.add('hidden');
            fetchRules();
        } else {
            showAlertModal("Gagal menyimpan rule", true);
        }
    } catch(e) {
        console.error(e);
        showAlertModal("Gagal menghubungi server", true);
    }
};

window.deleteRule = async (p_no) => {
    // Note: Replaced native confirm with custom logic if desired, keeping current flow as requested
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
    pnoInput.disabled = true;
    
    document.getElementById('input-avg-conf').value = rule.avg_confidence !== undefined ? (rule.avg_confidence * 100).toFixed(0) : 75;
    document.getElementById('input-min-coverage').value = rule.min_coverage !== undefined ? (rule.min_coverage * 100).toFixed(0) : 100;
    
    compContainer.innerHTML = '';
    rule.komponen.forEach(k => {
        compContainer.appendChild(createComponentRow(k.nama_komponen, k.min_confidence || 0.70));
    });
    
    modal.classList.remove('hidden');
};

window.keluarAdmin = () => {
    if (confirm("Keluar dari Admin Dashboard?")) {
        window.close();
        document.body.innerHTML = "<h2 style='color:white; text-align:center; margin-top:50px;'>Silakan tutup tab browser ini.</h2>";
    }
};

// --- MODAL UTILS ---
function showAlertModal(message, isError = false) {
    const alertModal = document.getElementById('alert-modal');
    const title = document.getElementById('alert-title');
    const msg = document.getElementById('alert-message');
    const btnOk = document.getElementById('btn-alert-ok');

    if (isError) {
        title.innerText = '❌ Gagal';
        title.style.color = '#ef4444';
    } else {
        title.innerText = '✅ Berhasil / Info';
        title.style.color = '#22c55e';
    }
    
    msg.innerText = message;
    alertModal.classList.remove('hidden');

    const handleOk = () => {
        alertModal.classList.add('hidden');
        btnOk.removeEventListener('click', handleOk);
    };
    btnOk.addEventListener('click', handleOk);
}

// --- GLOBAL RULE LOGIC ---
function showConfirmModal() {
    return new Promise((resolve) => {
        const confirmModal = document.getElementById('confirm-modal');
        const btnYes = document.getElementById('btn-confirm-yes');
        const btnCancel = document.getElementById('btn-confirm-cancel');

        confirmModal.classList.remove('hidden');

        const handleYes = () => {
            confirmModal.classList.add('hidden');
            cleanup();
            resolve(true);
        };

        const handleCancel = () => {
            confirmModal.classList.add('hidden');
            cleanup();
            resolve(false);
        };

        const cleanup = () => {
            btnYes.removeEventListener('click', handleYes);
            btnCancel.removeEventListener('click', handleCancel);
        };

        btnYes.addEventListener('click', handleYes);
        btnCancel.addEventListener('click', handleCancel);
    });
}

btnGlobalRule.onclick = async () => {
    try {
        const res = await fetch('/api/admin/global-rule');
        if(res.ok) {
            const data = await res.json();
            document.getElementById('global-avg-conf').value = (data.default_avg_conf * 100).toFixed(0);
            document.getElementById('global-min-conf').value = (data.default_min_conf * 100).toFixed(0);
            document.getElementById('global-min-coverage').value = (data.default_min_coverage * 100).toFixed(0);
        }
    } catch(e) {
        console.error("Gagal load global rules", e);
    }
    globalModal.classList.remove('hidden');
};

btnGlobalCancel.onclick = () => {
    globalModal.classList.add('hidden');
};

globalForm.onsubmit = async (e) => {
    e.preventDefault();
    const isConfirmed = await showConfirmModal();
    if (!isConfirmed) return;

    const avg_c = parseFloat(document.getElementById('global-avg-conf').value) / 100;
    const min_c = parseFloat(document.getElementById('global-min-conf').value) / 100;
    const min_cov = parseFloat(document.getElementById('global-min-coverage').value) / 100;

    try {
        const res = await fetch('/api/admin/global-rule', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                default_avg_conf: avg_c,
                default_min_conf: min_c,
                default_min_coverage: min_cov
            })
        });
        
        if (res.ok) {
            showAlertModal("Global rule berhasil diaplikasikan ke semua part!");
            globalModal.classList.add('hidden');
            fetchRules(); // Refresh tabel
        } else {
            showAlertModal("Gagal menyimpan global rule", true);
        }
    } catch(e) {
        showAlertModal("Error: " + e, true);
    }
};

// Start
fetchRules();
