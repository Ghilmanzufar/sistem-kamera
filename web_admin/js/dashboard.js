const API_URL_TRANS = '/api/admin/transactions';
const tbody_trans = document.getElementById('transactions-body');

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
    if (!tbody_trans) return; 
    tbody_trans.innerHTML = '';
    trans.forEach(t => {
        let statusBadge = t.status === 1 
            ? '<span class="status-badge status-selesai">Selesai (OK)</span>'
            : (t.status === 2 ? '<span class="status-badge status-running">Running</span>' : '<span style="color:red; font-weight:bold;">NG / Gagal</span>');
            
        let startTime = t.start_time ? new Date(t.start_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '-';
        let endTime = t.end_time ? new Date(t.end_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '-';
        
        tbody_trans.innerHTML += `
            <tr>
                <td>${t.id_trans}</td>
                <td>${t.part_no || '-'}</td>
                <td>${t.unique_no || '-'}</td>
                <td>${t.part_name || '-'}</td>
                <td>${t.target_qty}</td>
                <td>${t.qty_actual}</td>
                <td>${statusBadge}</td>
                <td>${startTime}</td>
                <td>${endTime}</td>
            </tr>
        `;
    });
}

// Start
fetchTransactions();
setInterval(fetchTransactions, 3000);
