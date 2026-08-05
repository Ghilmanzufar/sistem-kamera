// auth.js - 👱 Ponytail Zero-Bloat Auth
const isLoginPage = window.location.pathname.endsWith('login.html');
const adminToken = localStorage.getItem('admin_token');

if (!adminToken && !isLoginPage) {
    window.location.href = 'login.html';
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
        console.warn("[Auth] Token tidak valid atau kadaluwarsa.");
        if (!isLoginPage) {
            localStorage.removeItem('admin_token');
            window.location.href = 'login.html';
        }
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
        localStorage.removeItem('admin_token');
        localStorage.removeItem('user_role');
        localStorage.removeItem('username');
        window.location.href = 'login.html';
    }
};
