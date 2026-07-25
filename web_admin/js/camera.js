document.addEventListener('DOMContentLoaded', () => {
    loadCameras();
});

function loadCameras() {
    fetch('/api/cameras')
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById('camera-table-body');
            tbody.innerHTML = '';
            
            data.forEach(cam => {
                const statusBadge = cam.is_active 
                    ? '<span class="badge active">AKTIF</span>' 
                    : '<span class="badge inactive">STANDBY</span>';
                    
                const actionBtn = cam.is_active
                    ? `<button class="btn btn-danger btn-sm" onclick="deleteCamera(${cam.id})">Hapus</button>`
                    : `<button class="btn btn-activate btn-sm" style="margin-right:5px" onclick="activateCamera(${cam.id})">Aktifkan</button>
                       <button class="btn btn-danger btn-sm" onclick="deleteCamera(${cam.id})">Hapus</button>`;

                tbody.innerHTML += `
                    <tr>
                        <td>${cam.id}</td>
                        <td>${cam.name}</td>
                        <td>${cam.source}</td>
                        <td>${statusBadge}</td>
                        <td>${actionBtn}</td>
                    </tr>
                `;
            });
        })
        .catch(err => console.error("Error loading cameras:", err));
}

function openAddCameraModal() {
    document.getElementById('addCameraModal').classList.add('show');
}

function closeAddCameraModal() {
    document.getElementById('addCameraModal').classList.remove('show');
    document.getElementById('camName').value = '';
    document.getElementById('camSource').value = '';
}

function saveNewCamera() {
    const name = document.getElementById('camName').value;
    const source = document.getElementById('camSource').value;
    
    if(!name || !source) {
        alert("Nama dan Sumber harus diisi!");
        return;
    }
    
    fetch('/api/cameras', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, source })
    })
    .then(res => res.json())
    .then(() => {
        closeAddCameraModal();
        loadCameras();
    })
    .catch(err => alert("Gagal menyimpan kamera"));
}

function activateCamera(id) {
    if(confirm("Jadikan kamera ini sebagai sumber utama? Anda harus merestart aplikasi Python (BASIC_APP.py) setelah ini agar efeknya terlihat.")) {
        fetch(`/api/cameras/${id}/activate`, { method: 'PUT' })
            .then(res => res.json())
            .then(() => loadCameras())
            .catch(err => alert("Gagal mengaktifkan kamera"));
    }
}

function deleteCamera(id) {
    if(confirm("Hapus profil kamera ini?")) {
        fetch(`/api/cameras/${id}`, { method: 'DELETE' })
            .then(res => res.json())
            .then(() => loadCameras())
            .catch(err => alert("Gagal menghapus kamera"));
    }
}
