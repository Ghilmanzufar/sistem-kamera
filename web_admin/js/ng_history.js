const filterDate = document.getElementById('filter-date');
const ngModal = document.getElementById('ng-modal');

// Set default date to today
if (!filterDate.value) {
    const today = new Date();
    const tzOffset = today.getTimezoneOffset() * 60000;
    const localISOTime = (new Date(today - tzOffset)).toISOString().split('T')[0];
    filterDate.value = localISOTime;
}

window.fetchNGLogs = async () => {
    try {
        let url = '/api/admin/ng-logs';
        if (filterDate.value) {
            url += `?date_filter=${filterDate.value}`;
        }
        const res = await fetch(url);
        const data = await res.json();
        renderNGLogs(data);
    } catch (e) {
        console.error("Failed to fetch NG logs", e);
    }
};

function renderNGLogs(logs) {
    const container = document.getElementById('ng-gallery');
    if (!container) return;
    container.innerHTML = '';
    
    if (logs.length === 0) {
        container.innerHTML = '<p style="color: rgba(255,255,255,0.6);">Belum ada riwayat NG pada tanggal ini.</p>';
        return;
    }

    logs.forEach(log => {
        let timeStr = new Date(log.created_at).toLocaleString([], { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
        let imgSrc = log.image_path ? `/${log.image_path.replace(/\\/g, '/')}` : '';
        
        // Escape data for onclick
        const logDataStr = encodeURIComponent(JSON.stringify({
            img: imgSrc,
            part: log.part_no || '-',
            time: timeStr
        }));
        
        container.innerHTML += `
            <div style="background: rgba(255,255,255,0.1); border-radius: 8px; overflow: hidden; border: 1px solid var(--glass-border); display: flex; flex-direction: column; cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'" onclick="showDetail('${logDataStr}')">
                <div style="height: 200px; background: #000; display: flex; align-items: center; justify-content: center;">
                    ${imgSrc ? `<img src="${imgSrc}" style="max-width: 100%; max-height: 100%; object-fit: contain;" alt="NG Image" onerror="this.src=''; this.alt='Gambar tidak ditemukan'">` : '<span style="color: #666;">No Image</span>'}
                </div>
                <div style="padding: 15px; flex-grow: 1;">
                    <h3 style="margin-top: 0; font-size: 16px; margin-bottom: 5px;">${log.id_trans}</h3>
                    <p style="margin: 0; font-size: 14px; color: #ddd;">Part: <strong>${log.part_no || '-'}</strong></p>
                    <p style="margin: 5px 0 0 0; font-size: 12px; color: #aaa;">${timeStr}</p>
                </div>
            </div>
        `;
    });
}

window.showDetail = (dataStr) => {
    const data = JSON.parse(decodeURIComponent(dataStr));
    document.getElementById('modal-ng-img').src = data.img;
    document.getElementById('modal-ng-part').innerText = data.part;
    document.getElementById('modal-ng-time').innerText = data.time;
    
    const btnDownload = document.getElementById('btn-download');
    btnDownload.href = data.img;
    
    // Extract filename for download attribute
    const filename = data.img.split('/').pop() || 'NG_Image.jpg';
    btnDownload.setAttribute('download', filename);
    
    ngModal.classList.remove('hidden');
};

document.getElementById('btn-close-modal').onclick = () => {
    ngModal.classList.add('hidden');
};

// Re-fetch when date changes
filterDate.addEventListener('change', fetchNGLogs);

// Start
fetchNGLogs();
setInterval(fetchNGLogs, 3000);
