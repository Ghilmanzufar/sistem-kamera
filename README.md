# 🔍 Sistem Kamera Inspeksi AI & Quality Control

Sistem inspeksi visual otomatis berbasis **Deep Learning (YOLOv8)** dan **Computer Vision (OpenCV)** yang terintegrasi secara real-time dengan antarmuka desktop **PyQt6**, backend **FastAPI**, dan **Web Admin Dashboard (React + Vite + TailwindCSS)**. 

Dirancang khusus untuk lini produksi manufaktur otomotif guna memverifikasi kelengkapan komponen (*defect detection*), menghitung target QTY, serta berkomunikasi dua arah dengan sistem **SISON**.

---

## 🌟 Fitur Utama

### 1. 🤖 Inspeksi & Deteksi AI Real-Time
* **Model Deteksi YOLOv8:** Verifikasi keberadaan dan kelengkapan komponen perakitan (*Front/Rear side*) dengan skor keyakinan (*confidence score*).
* **Manajemen State Transaksi:** Siklus status inspeksi `STANDBY` ➡️ `RUNNING` ➡️ `OK` / `NG` ➡️ `COMPLETED`.
* **Alarm Abnormality (Sirene NG):** Pengambilan otomatis foto bukti part cacat ke folder `ng_records/` dan dialog validasi pengawas.

### 2. ⚡ Integrasi Sistem SISON
* **Pemicu Transaksi (`POST /api/start`):** Menerima data payload part dari SISON (`id_trans`, `lot`, `p_no`, `unique_no`, `p_name`, `qty`) yang diamankan dengan **Bearer API Key**.
* **Callback Webhook:** Mengirimkan kembali hasil verifikasi status inspeksi secara otomatis ke server SISON.
* **Simulator Interaktif:** Tombol **🚀 DEMO SISON** dan **📷 MOCK DETECT** langsung di antarmuka desktop untuk pengujian mandiri tanpa menunggu server SISON eksternal.

### 3. 🔌 Kontrol Hardware Kamera Dinamis
* **Saklar Power ON / OFF:** Memutus (*release*) dan menyalakan (*open*) feed video kamera secara instan dari Web Admin tanpa perlu me-restart aplikasi.
* **Dukungan Multi-Kamera:** Beralih antar-port USB atau stream kamera secara dinamis.
* **Auto Hardware Scanner:** Deteksi otomatis port kamera USB yang tercolok ke komputer.

### 4. 📊 Web Admin Dashboard Komprehensif
* **Live Dashboard:** Pemantauan statistik transaksi harian/bulanan (Total, Lulus OK, Cacat NG) dengan grafik tren interaktif.
* **Riwayat Inspeksi (History):** Tabel log lengkap dengan filter harian/bulanan, detail transaksi modal, dan ekspor laporan CSV/Excel (khusus hak akses *Admin & Pengawas*).
* **Manajemen Model AI (`.pt`):** Unggah model bobot baru, inspeksi label wajib, dan *hot-reloading* model otomatis saat part number berganti.
* **Manajemen User & PIN:** Pengaturan akun operator dan pengawas dengan enkripsi sandi aman (*argon2 / sha256*).
* **Audit Logs:** Pencatatan seluruh aktivitas penting (login, perubahan rule, pergantian kamera) untuk rekam jejak kepatuhan audit.
* **Pusat Informasi Error & Pemulihan:** Tampilan error bersahabat dengan panduan periksa mandiri (*self-troubleshooting checklist*) dan log telemetri teknis untuk tim IT.
* **Dukungan Tema Ganda:** Mode Gelap (*Dark Mode*) dan Mode Terang Berkontras Tinggi (*High-Contrast Light Mode*).

---

## 🏗️ Arsitektur & Teknologi

```
+-----------------------------------------------------------------------------------+
|                                   SISTEM SISON                                    |
+-----------------------------------------------------------------------------------+
                                   │  HTTP REST (Bearer API Key)
                                   ▼
+───────────────────────────────────────────────────────────────────────────────────+
|                  CORE ENGINE (Python / FastAPI / OpenCV / PyQt6)                   |
|                                                                                   |
|   • BASIC_APP.py        : GUI Desktop Operator, Video Stream 16:9, HUD Display     |
|   • terima_dari_sison.py: Endpoint Penerima Transaksi (POST /api/start)           |
|   • proses_kamera.py    : Engine Deteksi YOLOv8, Hitung Sisi, Logging NG DB       |
|   • admin_router.py     : REST API Endpoints untuk Web Admin Dashboard            |
|   • database_config.py  : ORM SQLAlchemy, Koneksi PostgreSQL / SQLite, Enkripsi   |
+───────────────────────────────────────────────────────────────────────────────────+
                                   ▲
                                   │  HTTP Client (Axios + JWT)
                                   ▼
+───────────────────────────────────────────────────────────────────────────────────+
|               WEB ADMIN DASHBOARD (React 19 / Vite / TailwindCSS v4)               |
|                                                                                   |
|   • Live Dashboard      • History & Export CSV    • Setting Rule Inspeksi         |
|   • Model AI (.pt)      • User Manajemen & PIN    • Kamera Manajemen (ON/OFF)     |
|   • Config Sison & API  • Audit Logs              • Error Information Center      |
+───────────────────────────────────────────────────────────────────────────────────+
```

---

## 📂 Struktur Direktori Proyek

```plaintext
sistem-kamera/
├── BASIC_APP.py             # Aplikasi utama desktop PyQt6 & runner FastAPI
├── admin_router.py          # Rute API backend untuk Web Admin (Auth, Logs, Cameras)
├── terima_dari_sison.py     # Rute API penerima payload transaksi SISON (/api/start)
├── proses_kamera.py         # Pipeline inferensi YOLOv8, parsing bounding box & rule
├── database_config.py       # Model database SQLAlchemy (User, Log, Rule, CamConfig)
├── weights/                 # Direktori model bobot AI PyTorch (.pt)
├── ng_records/              # Direktori penyimpanan otomatis foto part cacat (NG)
├── web_admin/               # Source code frontend Web Admin Dashboard (React + Vite)
│   ├── src/
│   │   ├── components/      # Sidebar, Navbar, StatCard, DataTable, ErrorBoundary
│   │   ├── pages/           # Dashboard, History, Camera, Users, Models, ErrorPage
│   │   ├── api/client.js    # Konfigurasi Axios client & JWT token interceptor
│   │   └── index.css        # Desain Tailwind & tema High-Contrast Light Mode
│   ├── dist/                # Production build bundle frontend yang disajikan FastAPI
│   └── package.json
├── .env                     # Konfigurasi environment (DB, Secret Key, Port)
├── requirements.txt         # Daftar dependensi Python
└── README.md
```

---

## 🚀 Panduan Instalasi & Menjalankan

### 1. Prasyarat Sistem
* **Python:** Versi 3.10 atau lebih baru.
* **Node.js:** Versi 18 atau lebih baru (untuk build frontend).
* **Database:** PostgreSQL (atau SQLite lokal).
* **Hardware:** Kamera USB Web Camera / Kamera Industri (mendukung resolusi HD 720p/1080p).

---

### 2. Setup Backend Python

1. **Clone repository:**
   ```bash
   git clone https://github.com/Ghilmanzufar/sistem-kamera.git
   cd sistem-kamera
   ```

2. **Buat & aktifkan Virtual Environment:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependensi:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Konfigurasi file `.env`:**
   Buat file `.env` di root direktori:
   ```ini
   DATABASE_URL=postgresql://postgres:password@localhost:5432/sistem_kamera
   SECRET_KEY=sugity_super_secret_jwt_key_2026
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=480
   ```

---

### 3. Build Frontend Web Admin

```bash
cd web_admin
npm install
npm run build
cd ..
```
*Hasil build bundle di folder `web_admin/dist` otomatis disajikan oleh server FastAPI.*

---

### 4. Menjalankan Aplikasi

Jalankan server utama dan antarmuka desktop:
```bash
python BASIC_APP.py
```

* **Layar Desktop Operator:** Otomatis terbuka secara maximized menampilkan live video feed kamera dan status HUD.
* **Web Admin Dashboard:** Buka browser di `http://localhost:8000/admin/`
* **Swagger API Documentation:** Buka `http://localhost:8000/docs`

---

## 🔌 Spesifikasi API Integrasi SISON

### `POST /api/start`
Digunakan oleh sistem SISON untuk memicu transaksi inspeksi baru.

* **Headers:**
  ```http
  Content-Type: application/json
  Authorization: Bearer <API_KEY_SISON>
  ```
* **Payload Request:**
  ```json
  {
    "id_trans": "DEMO-1786211114",
    "lot": "LOT-8821",
    "p_no": "74231-0K550-00",
    "unique_no": "UNQ-9901",
    "p_name": "Demo Part Komponen A",
    "qty": 1
  }
  ```
* **Response:**
  * `200 OK`: Transaksi diterima & inspeksi dimulai.
  * `400 Bad Request`: Payload JSON tidak lengkap / salah format.
  * `401 Unauthorized`: API Key tidak valid.
  * `409 Conflict`: Kamera sedang sibuk memproses transaksi sebelumnya.

---

## 👥 Pengguna & Hak Akses (RBAC)

| Peran (*Role*) | Hak Akses Fitur |
| :--- | :--- |
| **Operator** | Memantau live feed desktop, melihat riwayat inspeksi (*view-only*). |
| **Pengawas / Admin** | Akses penuh Web Admin: Dashboard analitik, ekspor CSV/Excel, saklar kamera ON/OFF, manajemen model AI, setting rule, audit log, manajemen user & PIN. |

---

## 📄 Lisensi & Hak Cipta
Dikembangkan untuk lini inspeksi kualitas manufaktur otomotif **PT Sugity Creatives**. Seluruh hak cipta dilindungi undang-undang.
