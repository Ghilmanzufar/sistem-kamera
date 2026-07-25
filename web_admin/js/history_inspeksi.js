const filterDate = document.getElementById('filter-date');
const tbody = document.getElementById('transactions-body');
let currentData = [];

// Set default date to today
if (!filterDate.value) {
    const today = new Date();
    const tzOffset = today.getTimezoneOffset() * 60000;
    const localISOTime = (new Date(today - tzOffset)).toISOString().split('T')[0];
    filterDate.value = localISOTime;
}

window.fetchTransactions = async () => {
    try {
        let url = '/api/admin/transactions';
        if (filterDate.value) {
            url += `?date_filter=${filterDate.value}`;
        }
        const res = await fetch(url);
        currentData = await res.json();
        renderTransactions(currentData);
    } catch (e) {
        console.error("Failed to fetch transactions", e);
    }
};

function renderTransactions(transactions) {
    tbody.innerHTML = '';
    
    if (transactions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; color:#999;">Belum ada riwayat transaksi pada tanggal ini.</td></tr>';
        return;
    }

    transactions.forEach(t => {
        const tr = document.createElement('tr');
        
        let statusStr = "Unknown";
        if (t.status === 0) statusStr = "<span style='color:orange;'>Running</span>";
        else if (t.status === 1) statusStr = "<span style='color:green;'>OK</span>";
        else if (t.status === 2) statusStr = "<span style='color:red;'>NG</span>";
        
        let startTime = new Date(t.start_time).toLocaleString([], { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });

        tr.innerHTML = `
            <td><strong>${t.id_trans}</strong></td>
            <td>${t.part_no || '-'}</td>
            <td>${t.part_name || '-'}</td>
            <td>${t.lot_no || '-'}</td>
            <td>${t.unique_no || '-'}</td>
            <td>${t.target_qty}</td>
            <td>${t.qty_actual}</td>
            <td>${statusStr}</td>
            <td>${startTime}</td>
        `;
        tbody.appendChild(tr);
    });
}

document.getElementById('btn-export').onclick = () => {
    if (currentData.length === 0) {
        alert("Tidak ada data untuk di-export pada tanggal ini.");
        return;
    }

    // Buat Header CSV
    let csvContent = "ID Transaksi,Part No,Part Name,Lot No,Unique No,Target Qty,Actual Qty,Status,Waktu Mulai\n";
    
    // Isi Data
    currentData.forEach(t => {
        let statusStr = "Unknown";
        if (t.status === 0) statusStr = "Running";
        else if (t.status === 1) statusStr = "OK";
        else if (t.status === 2) statusStr = "NG";
        
        // Escape koma pada data jika ada
        const row = [
            `"${t.id_trans || ''}"`,
            `"${t.part_no || ''}"`,
            `"${t.part_name || ''}"`,
            `"${t.lot_no || ''}"`,
            `"${t.unique_no || ''}"`,
            t.target_qty,
            t.qty_actual,
            `"${statusStr}"`,
            `"${t.start_time || ''}"`
        ];
        csvContent += row.join(",") + "\n";
    });

    // Buat Blob dan Download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `Report_Inspeksi_${filterDate.value}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
};

// Re-fetch when date changes
filterDate.addEventListener('change', fetchTransactions);

window.keluarAdmin = () => {
    if (confirm("Keluar dari Admin Dashboard?")) {
        window.close();
        document.body.innerHTML = "<h2 style='color:white; text-align:center; margin-top:50px;'>Silakan tutup tab browser ini.</h2>";
    }
};

// Start
fetchTransactions();
