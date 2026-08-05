// auth.js
// 1. Cek parameter URL untuk role baru saat login dari BASIC_APP.py
const urlParams = new URLSearchParams(window.location.search);
const roleParam = urlParams.get('role');
const tokenParam = urlParams.get('token');

if (roleParam) {
    localStorage.setItem('user_role', roleParam);
}
if (tokenParam) {
    localStorage.setItem('admin_token', tokenParam);
}
if (roleParam || tokenParam) {
    // Hapus parameter rahasia dari URL agar terlihat bersih
    window.history.replaceState({}, document.title, window.location.pathname);
}

// 👱 Ponytail: Injeksi header Authorization secara otomatis ke setiap panggilan API Admin (0% boilerplate di file JS lain!)
const origFetch = window.fetch;
window.fetch = async function(url, options = {}) {
    const urlStr = typeof url === 'string' ? url : (url && url.url ? url.url : '');
    if (urlStr.includes('/api/admin')) {
        options = options || {};
        options.headers = options.headers || {};
        const token = localStorage.getItem('admin_token') || '';
        if (options.headers instanceof Headers) {
            options.headers.set('Authorization', 'Bearer ' + token);
        } else {
            options.headers['Authorization'] = 'Bearer ' + token;
        }
    }
    const response = await origFetch(url, options);
    if (response.status === 401 || response.status === 403) {
        console.warn("[Auth] Token kosong atau kadaluwarsa. Silakan tutup browser & login ulang dari GUI BASIC_APP.py!");
    }
    return response;
};

// 2. Terapkan Restriksi Role
document.addEventListener("DOMContentLoaded", () => {
    const userRole = localStorage.getItem('user_role') || 'pengawas'; // Default paling rendah
    
    if (userRole === 'pengawas') {
        const restrictedTabs = ['rules.html', 'models.html', 'users.html'];
        
        // Sembunyikan tombol tab
        document.querySelectorAll('.nav-tabs a').forEach(link => {
            restrictedTabs.forEach(restricted => {
                if (link.href.includes(restricted)) {
                    link.style.display = 'none';
                }
            });
        });
        
        // Tendang user jika mencoba mengetik URL secara manual
        const currentPath = window.location.pathname;
        if (restrictedTabs.some(r => currentPath.endsWith(r))) {
            alert("Akses Ditolak! Anda masuk sebagai Pengawas.");
            window.location.href = 'index.html';
        }
    }
});

// 👱 Ponytail: Fungsi keluarAdmin dipasang terpusat di auth.js (menghilangkan duplikasi boilerplate di semua file JS)
window.keluarAdmin = () => {
    if (confirm("Keluar dari Admin Dashboard?")) {
        window.close();
        document.body.innerHTML = "<h2 style='color:white; text-align:center; margin-top:50px;'>Silakan tutup tab browser ini.</h2>";
    }
};
