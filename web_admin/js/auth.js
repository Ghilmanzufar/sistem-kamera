// auth.js
// 1. Cek parameter URL untuk role baru saat login dari BASIC_APP.py
const urlParams = new URLSearchParams(window.location.search);
const roleParam = urlParams.get('role');

if (roleParam) {
    localStorage.setItem('user_role', roleParam);
    // Hapus parameter role dari URL agar terlihat bersih
    window.history.replaceState({}, document.title, window.location.pathname);
}

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
