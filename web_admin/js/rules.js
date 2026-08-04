const globalForm = document.getElementById('global-rule-form');

async function fetchGlobalRule() {
    try {
        const res = await fetch('/api/admin/global-rule');
        if (res.ok) {
            const data = await res.json();
            document.getElementById('global-avg-conf').value = (data.default_avg_conf * 100).toFixed(0);
            document.getElementById('global-min-conf').value = (data.default_min_conf * 100).toFixed(0);
            document.getElementById('global-min-coverage').value = (data.default_min_coverage * 100).toFixed(0);
        }
    } catch (e) {
        console.error("Gagal memuat global rule", e);
        showAlertModal("Gagal terhubung ke server saat memuat rule.", true);
    }
}

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

function showAlertModal(message, isError = false) {
    const alertModal = document.getElementById('alert-modal');
    const title = document.getElementById('alert-title');
    const msg = document.getElementById('alert-message');
    const btnOk = document.getElementById('btn-alert-ok');

    if (isError) {
        title.innerText = '❌ Gagal';
        title.style.color = '#ef4444';
    } else {
        title.innerText = '✅ Berhasil';
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

globalForm.onsubmit = async (e) => {
    e.preventDefault();
    const isConfirmed = await showConfirmModal();
    if (!isConfirmed) return;

    const btnSubmit = globalForm.querySelector('button[type="submit"]');
    const origText = btnSubmit.innerText;
    btnSubmit.innerText = "Menyimpan...";
    btnSubmit.disabled = true;

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
            showAlertModal("Global rule berhasil disimpan & teraplikasikan ke seluruh part!");
        } else {
            const data = await res.json().catch(() => ({}));
            showAlertModal(data.detail || "Gagal menyimpan global rule", true);
        }
    } catch (e) {
        showAlertModal("Terjadi kesalahan koneksi server: " + e, true);
    } finally {
        btnSubmit.innerText = origText;
        btnSubmit.disabled = false;
    }
};

window.keluarAdmin = () => {
    if (confirm("Keluar dari Admin Dashboard?")) {
        window.close();
        document.body.innerHTML = "<h2 style='color:white; text-align:center; margin-top:50px;'>Silakan tutup tab browser ini.</h2>";
    }
};

// Start
fetchGlobalRule();
