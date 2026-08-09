import sys
import os
import time
import json
import threading
import logging
import warnings
import webbrowser

from dotenv import load_dotenv
load_dotenv()  # 👱 Ponytail: Pastikan SECRET_KEY dari .env terbaca sebelum FastAPI/router init

# 👱 Ponytail: Bungkam log MSMF/OpenCV via environment variable agar terminal tenang tanpa merusak decoding video
os.environ["OPENCV_LOG_LEVEL"] = "FATAL"
os.environ["OPENCV_VIDEOIO_DEBUG"] = "0"
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
import cv2
if hasattr(cv2, 'setLogLevel'):
    cv2.setLogLevel(0)

import uvicorn
import requests
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget, QApplication, QMessageBox, QPushButton, QHBoxLayout, QSizePolicy, QInputDialog, QDialog, QLineEdit, QFrame
from PyQt6.QtGui import QImage, QPixmap

from database_config import SessionLocal, CameraConfig, User, verify_password
from terima_dari_sison import router as camera_router
from proses_kamera import state, KameraProses
import proses_kamera
import admin_router

warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.getLogger('ultralytics').setLevel(logging.WARNING)
logging.getLogger().setLevel(logging.ERROR)

def authenticate_and_get_role(username: str, pin: str, allowed_roles: list) -> str:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username, User.is_active == True).first()
        if not user or not verify_password(pin, user.password):
            return None
        if user.role not in allowed_roles:
            return None
        return user.role
    except Exception as e:
        print(f"Auth error: {e}")
        return None
    finally:
        db.close()

def cleanup_old_ng_records(days: int = 30):
    """👱 Ponytail Background Task: Otomatis hapus file foto NG yang berumur > 30 hari untuk menghemat disk."""
    folder = "ng_records"
    if not os.path.exists(folder):
        return
    now = time.time()
    cutoff = now - (days * 86400)
    deleted_count = 0
    try:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path) and filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                if os.path.getmtime(file_path) < cutoff:
                    os.remove(file_path)
                    deleted_count += 1
        if deleted_count > 0:
            print(f"[CLEANUP] Otomatis menghapus {deleted_count} foto NG lama (> {days} hari).")
    except Exception as e:
        print(f"[CLEANUP WARN] Gagal menjalankan pembersihan foto NG: {e}")

def start_periodic_cleanup():
    def loop():
        while True:
            cleanup_old_ng_records(days=30)
            time.sleep(86400)  # Cek setiap 24 jam
    t = threading.Thread(target=loop, daemon=True)
    t.start()

from starlette.exceptions import HTTPException as StarletteHTTPException

class SPAStaticFiles(StaticFiles):
    """👱 Ponytail SPA Handler: Otomatis alihkan 404 ke index.html agar React Router tidak crash saat F5 / Refresh."""
    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
            if response.status_code == 404:
                return await super().get_response("index.html", scope)
            return response
        except StarletteHTTPException as ex:
            if ex.status_code == 404:
                return await super().get_response("index.html", scope)
            raise ex

# Setup FastAPI App
app_fastapi = FastAPI(title="Sistem Kamera API")
app_fastapi.include_router(camera_router, prefix="/api")
app_fastapi.include_router(admin_router.public_router, prefix="/api")

# --- CUSTOM WEB ADMIN CONFIGURATION ---

app_fastapi.include_router(admin_router.router, prefix="/api/admin")
os.makedirs("web_admin/dist", exist_ok=True)
app_fastapi.mount("/admin", SPAStaticFiles(directory="web_admin/dist", html=True), name="admin")
app_fastapi.mount("/ng_records", StaticFiles(directory="ng_records"), name="ng_records")
# ----------------------------------------

def run_fastapi():
    """Jalankan uvicorn server di background thread"""
    uvicorn.run(app_fastapi, host="0.0.0.0", port=8000, log_level="error")

class NGValidationDialog(QDialog):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NG Terdeteksi!")
        self.setStyleSheet("background-color: #222; color: white; font-size: 24px;")
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 1. Gambar Bukti Cacat
        self.img_label = QLabel(self)
        self.img_label.setPixmap(pixmap.scaled(800, 600, Qt.AspectRatioMode.KeepAspectRatio))
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet("border: 3px solid #ff4444; background-color: black;")
        layout.addWidget(self.img_label)
        
        # 2. Pesan
        msg_label = QLabel("⚠️ KOMPONEN NG TERDETEKSI! ⚠️\nPanggil Pengawas dan masukkan PIN untuk mematikan sirene.", self)
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_label.setStyleSheet("color: #ff4444; font-weight: bold; font-size: 26px;")
        layout.addWidget(msg_label)
        
        # 3. Input Username
        self.username_input = QLineEdit(self)
        self.username_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.username_input.setPlaceholderText("Masukkan Username...")
        self.username_input.setStyleSheet("background-color: white; color: black; font-size: 32px; padding: 10px; border-radius: 8px; margin-bottom: 10px;")
        layout.addWidget(self.username_input)
        
        # 4. Input PIN
        self.pin_input = QLineEdit(self)
        self.pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pin_input.setPlaceholderText("Masukkan PIN (misal: 1234)...")
        self.pin_input.setStyleSheet("background-color: white; color: black; font-size: 32px; padding: 10px; border-radius: 8px;")
        layout.addWidget(self.pin_input)
        
        # 4. Tombol
        btn_layout = QHBoxLayout()
        self.btn_validasi = QPushButton("VALIDASI PIN", self)
        self.btn_validasi.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_validasi.setStyleSheet("""
            QPushButton {
                background-color: #ff4444; 
                color: white; 
                font-weight: bold; 
                font-size: 28px; 
                padding: 15px; 
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #ff6666;
            }
        """)
        self.btn_validasi.clicked.connect(self.check_pin)
        
        btn_layout.addWidget(self.btn_validasi)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def check_pin(self):
        role = authenticate_and_get_role(self.username_input.text(), self.pin_input.text(), ["pengawas"])
        if role:
            self.accept()
        else:
            QMessageBox.warning(self, "Ditolak", "Username/PIN Salah atau Anda tidak terdaftar!")
            self.pin_input.clear()

class YoloApp(QWidget):

    def __init__(self):
        super().__init__()
        # Mengembalikan manajemen kamera via Database agar dinamis (bisa diatur lewat Web Admin perusahaan).
        try:
            db = SessionLocal()
            active_cam = db.query(CameraConfig).filter(CameraConfig.is_active == True).first()
            if active_cam:
                cam_source = active_cam.source
                if cam_source.isdigit():
                    cam_source = int(cam_source)
            else:
                cam_source = 0
            db.close()
            print(f"[SYSTEM] Menggunakan sumber kamera dari DB: {cam_source}")
        except Exception as e:
            print(f"[WARNING] Gagal membaca DB, fallback ke index 0. Error: {e}")
            cam_source = 0

        self.is_cam_active = (active_cam is not None)
        self.cam_source = cam_source
        self.last_cam_check_time = 0.0
        if self.is_cam_active:
            self._open_camera()
        else:
            self.cap = cv2.VideoCapture() # Empty capture object
        
        self.model = None # Lazy load model nanti saat Start Sison
        self.current_loaded_p_no = "" # Untuk mendeteksi perubahan part number dari Sison
        self.last_model_mtime = 0.0 # 👱 Ponytail: Mendeteksi jika file .pt diperbarui via Web Admin
        self.ng_popup_active = False

        # UI & Timers
        self.initUI()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30) # Refresh 30 FPS
        
        # Start FastAPI & Auto Cleanup
        self.api_thread = threading.Thread(target=run_fastapi, daemon=True)
        self.api_thread.start()
        start_periodic_cleanup()

    def _open_camera(self):
        # 👱 Ponytail: Default OpenCV adalah 640x480 (VGA 4:3) yang terlihat kecil/kotak di layar monitor. 
        # Naikkan ke 1280x720 (16:9 HD) agar gambar penuh, tajam untuk inspeksi, tanpa membebani FPS.
        self.cap = cv2.VideoCapture(self.cam_source)
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    def initUI(self):
        self.setWindowTitle("Sistem Kamera Inspeksi")
        self.setStyleSheet("font-size: 24px;")

        self.video_label = QLabel(self)
        self.video_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_label.setMinimumSize(1, 1)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("padding: 0px; margin: 0px; border: 2px solid black; background-color: #111;")
      
        # --- HUD (Heads-Up Display) ---
        self.hud_frame = QFrame(self)
        self.hud_frame.setObjectName("hud")
        self.hud_frame.setStyleSheet("#hud { background-color: #0f172a; border: none; border-radius: 10px; }")
        self.hud_frame.setFixedHeight(115)
        hud_layout = QHBoxLayout(self.hud_frame)
        hud_layout.setContentsMargins(20, 8, 20, 8)

        self.part_name = QLabel("<span style='color:#ffff00; font-size:14px; font-weight:bold;'>PART NUMBER</span><br/><span style='color:#f8fafc; font-size:24px; font-weight:bold;'>MENUNGGU SISON...</span>", self)
        self.part_name.setStyleSheet("border: none; background: transparent;")
        self.part_name.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        status_container = QWidget(self)
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(0,0,0,0)
        status_layout.setSpacing(0)
        
        self.status_label = QLabel("<span style='color:#94a3b8; font-size:13px;'>STATUS KAMERA</span><br/><span style='color:#cbd5e1; font-size:22px; font-weight:bold;'>STANDBY</span>", self)
        self.status_label.setStyleSheet("border: none; background: transparent;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 🐎 ponytail: info_label untuk memindahkan teks qty & sisi dari overlay OpenCV
        self.info_label = QLabel("<span style='color:#cbd5e1; font-size:13px; font-weight:bold;'>QTY: - | SISI: -</span>", self)
        self.info_label.setStyleSheet("border: none; background: transparent;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.info_label)
        
        self.btn_admin = QPushButton("⚙️ ADMIN DASHBOARD", self)
        self.btn_admin.setFixedHeight(45)
        self.btn_admin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_admin.setStyleSheet("background-color: #2563eb; color: white; font-size:16px; font-weight:bold; border-radius: 5px; padding: 0 15px;")
        self.btn_admin.clicked.connect(self.prompt_admin_dashboard)

        right_container = QWidget()
        right_layout = QHBoxLayout(right_container)
        right_layout.setContentsMargins(0,0,0,0)
        right_layout.addStretch()
        right_layout.addWidget(self.btn_admin)

        hud_layout.addWidget(self.part_name, stretch=1)
        hud_layout.addWidget(status_container, stretch=1)
        hud_layout.addWidget(right_container, stretch=1)

        self.btn_pass_manual = QPushButton("✅ PASS MANUAL (OK)", self)
        self.btn_pass_manual.setFixedHeight(38)
        self.btn_pass_manual.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pass_manual.setStyleSheet("background-color: #059669; hover: { background-color: #10b981; } color: white; font-size:14px; font-weight:bold; border-radius: 6px; padding: 0 14px;")
        self.btn_pass_manual.clicked.connect(self.trigger_manual_pass)

        self.btn_reject_manual = QPushButton("❌ REJECT (NG)", self)
        self.btn_reject_manual.setFixedHeight(38)
        self.btn_reject_manual.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reject_manual.setStyleSheet("background-color: #dc2626; color: white; font-size:14px; font-weight:bold; border-radius: 6px; padding: 0 14px;")
        self.btn_reject_manual.clicked.connect(self.trigger_manual_reject)

        self.btn_demo = QPushButton("🚀 DEMO SISON", self)
        self.btn_demo.setFixedHeight(38)
        self.btn_demo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_demo.setStyleSheet("background-color: #475569; color: white; font-size:14px; font-weight:bold; border-radius: 6px; padding: 0 10px;")
        self.btn_demo.clicked.connect(self.prompt_demo_sison)

        self.btn_mock = QPushButton("📷 MOCK DETECT", self)
        self.btn_mock.setFixedHeight(38)
        self.btn_mock.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mock.setStyleSheet("background-color: #334155; color: #94a3b8; font-size:13px; font-weight:bold; border-radius: 6px; padding: 0 10px;")
        self.btn_mock.clicked.connect(self.trigger_mock_detect)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.addWidget(self.btn_pass_manual)
        toolbar_layout.addWidget(self.btn_reject_manual)
        toolbar_layout.addSpacing(15)
        toolbar_layout.addWidget(self.btn_demo)
        toolbar_layout.addWidget(self.btn_mock)
        toolbar_layout.addStretch()

        # --- Main Layout ---
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        layout.addWidget(self.hud_frame)
        layout.addLayout(toolbar_layout)
        layout.addWidget(self.video_label)
        self.setLayout(layout)

    def prompt_demo_sison(self):
        import random
        default_json = json.dumps({
            "id_trans": f"DEMO-{int(time.time())}",
            "lot": f"LOT-{random.randint(1000, 9999)}",
            "p_no": "74231-0K550-00",
            "unique_no": f"UNQ-{random.randint(1000, 9999)}",
            "p_name": random.choice(["Demo Part A", "Demo Part B", "Demo Part C"]),
            "qty": 1
        }, indent=4)
        
        teks, ok = QInputDialog.getMultiLineText(self, "Simulator Sison", "Edit JSON payload (Peringatan: Pastikan format benar!):", default_json)
        if ok and teks:
            try:
                # Validasi format
                data_dict = json.loads(teks)
                
                # Ambil API key dari DB untuk bypass auth demo
                from database_config import SessionLocal, SisonConfig
                db_session = SessionLocal()
                try:
                    cfg = db_session.query(SisonConfig).first()
                    api_key = cfg.api_key if cfg else "kamera-secret-key"
                finally:
                    db_session.close()

                # Kirim HTTP POST ke API FastAPI kita sendiri
                res = requests.post("http://localhost:8000/api/start", json=data_dict, headers={"Authorization": f"Bearer {api_key}"}, timeout=3)
                if res.status_code == 200:
                    QMessageBox.information(self, "Sukses", "Simulasi Sison Berhasil Dikirim!")
                else:
                    QMessageBox.warning(self, "Gagal", f"Error API: {res.text}")
                    
            except json.JSONDecodeError:
                QMessageBox.warning(self, "Error", "Format JSON Tidak Valid!")
            except Exception as e:
                QMessageBox.critical(self, "Error Jaringan", f"Gagal menghubungi server lokal: {e}")

    def prompt_admin_dashboard(self):
        # 👱 Ponytail: Otentikasi dialihkan ke antarmuka Web Admin (tanpa perantara parameter rahasia di URL)
        webbrowser.open("http://localhost:8000/admin/")

    def trigger_manual_pass(self):
        with state.lock:
            curr_status = state.status
        if curr_status not in ["RUNNING", "OK"]:
            QMessageBox.information(self, "Info", "Sistem dalam posisi STANDBY.\nTidak ada transaksi aktif yang dapat divalidasi secara manual.")
            return
        with state.lock:
            state.manual_pass_trigger = True

    def trigger_manual_reject(self):
        with state.lock:
            curr_status = state.status
        if curr_status not in ["RUNNING", "OK"]:
            QMessageBox.information(self, "Info", "Sistem dalam posisi STANDBY.\nTidak ada transaksi aktif yang dapat di-reject.")
            return
        with state.lock:
            state.manual_reject_trigger = True

    def trigger_mock_detect(self):
        with state.lock:
            curr_status = state.status
        if curr_status not in ["RUNNING", "OK"]:
            QMessageBox.information(self, "Info", "Sistem dalam posisi STANDBY.\nSilakan klik '🚀 DEMO SISON' terlebih dahulu untuk memulai simulasi transaksi!")
            return
        with state.lock:
            state.mock_detect_trigger = True

    def update_frame(self):
        # 1. Update text info dari State (Thread-safe)
        with state.lock:
            p_no = state.p_no
            target_qty = state.target_qty
            sisa_qty = state.qty
            current_status = state.status
            inspection_mode = getattr(state, 'inspection_mode', 'AI')

        qty_selesai = target_qty - sisa_qty
        
        # Update Part Name (Rich Text) - Yellow #ffff00 for Part No and Green #22c55e for Target/Selesai
        if p_no:
            self.part_name.setText(f"<span style='color:#ffff00; font-size:28px; font-weight:bold;'>{p_no}</span><br/><span style='color:#22c55e; font-size:18px; font-weight:bold;'>Target: {target_qty} PCS | Selesai: {qty_selesai} PCS</span>")
        else:
            self.part_name.setText("<span style='color:#ffff00; font-size:16px; font-weight:bold;'>PART NUMBER</span><br/><span style='color:#f8fafc; font-size:28px; font-weight:bold;'>MENUNGGU SISON...</span>")

        # Update Status Label (Rich Text & Colors)
        status_color = "#cbd5e1" # Default Gray
        status_text = "STANDBY"
        
        is_running = current_status in ["OK", "RUNNING"]
        self.btn_pass_manual.setEnabled(is_running)
        self.btn_reject_manual.setEnabled(is_running)

        if is_running:
            if inspection_mode == "MANUAL" or self.model is None:
                status_color = "#f59e0b" # Amber / Orange
                status_text = "MODE MANUAL (VISUAL)"
            else:
                status_color = "#22c55e" # Green
                status_text = "INSPEKSI AI AKTIF" if current_status == "OK" else "PROSES (AI AUTO)"
            self.hud_frame.setStyleSheet("#hud { background-color: #0f172a; border: none; border-radius: 10px; }")
        elif current_status == "COMPLETED":
            status_color = "#38bdf8" # Sky Blue
            status_text = "SELESAI (OK)"
            self.hud_frame.setStyleSheet("#hud { background-color: #0f172a; border: none; border-radius: 10px; }")
            # 👱 Ponytail: Auto reset ke STANDBY setelah 5 detik transaksi selesai
            if state.completed_time > 0 and (time.time() - state.completed_time) >= 5.0:
                state.reset_to_standby()
        elif current_status == "NG":
            status_color = "#ef4444" # Red
            status_text = "NG TERDETEKSI"
            # Blinking effect for NG border
            blink = "red" if int(time.time() * 2) % 2 == 0 else "transparent"
            self.hud_frame.setStyleSheet(f"#hud {{ background-color: #0f172a; border: 4px solid {blink}; border-radius: 10px; }}")
        else:
            self.hud_frame.setStyleSheet("#hud { background-color: #0f172a; border: none; border-radius: 10px; }")
            
        self.status_label.setText(f"<span style='color:#94a3b8; font-size:13px;'>STATUS KAMERA</span><br/><span style='color:{status_color}; font-size:22px; font-weight:bold;'>{status_text}</span>")

        # 2. Lazy & Hot-Reload Model (Ganti model jika p_no berubah ATAU file .pt diperbarui di Web Admin)
        model_path = os.path.join(os.getcwd(), "weights", f"{p_no}.pt")
        curr_mtime = os.path.getmtime(model_path) if os.path.exists(model_path) else 0.0
        if p_no != "" and (p_no != self.current_loaded_p_no or curr_mtime > getattr(self, 'last_model_mtime', 0.0)):
            self.model = KameraProses.load_model(p_no)
            self.current_loaded_p_no = p_no
            self.last_model_mtime = curr_mtime

        # 3. Dynamic Camera Switch & Toggle Sync dari Database
        now_ts = time.time()
        if now_ts - self.last_cam_check_time >= 1.0:
            self.last_cam_check_time = now_ts
            try:
                db_cam_session = SessionLocal()
                active_cam = db_cam_session.query(CameraConfig).filter(CameraConfig.is_active == True).first()
                if active_cam:
                    new_src = active_cam.source
                    if isinstance(new_src, str) and new_src.isdigit():
                        new_src = int(new_src)
                    if not self.is_cam_active or self.cam_source != new_src or not self.cap.isOpened():
                        self.is_cam_active = True
                        self.cam_source = new_src
                        if self.cap.isOpened():
                            self.cap.release()
                        self._open_camera()
                        print(f"[SYSTEM] Saklar Kamera Aktif: {active_cam.name} (Source: {new_src})")
                else:
                    if self.is_cam_active:
                        self.is_cam_active = False
                        if self.cap.isOpened():
                            self.cap.release()
                        print("[SYSTEM] Saklar Kamera Standby (OFF): Video feed dihentikan.")
                db_cam_session.close()
            except Exception as e:
                pass

        if not self.is_cam_active:
            self.video_label.setText("<span style='color:#94a3b8; font-size:24px; font-weight:bold;'>⏸️ KAMERA STANDBY (OFF)<br/><span style='color:#64748b; font-size:15px; font-weight:normal;'>Kamera dimatikan dari Admin Dashboard.<br/>Nyalakan saklar kamera untuk melanjutkan live video stream.</span></span>")
            return

        # 4. Baca Frame Kamera
        ret, frame = self.cap.read() if self.cap.isOpened() else (False, None)
        if not ret:
            self.video_label.setText("<span style='color:#ef4444; font-size:24px; font-weight:bold;'>⚠️ KAMERA GAGAL DIAKSES / TIDAK TERDETEKSI<br/>Cek sambungan port USB atau settingan sumber kamera di Admin Dashboard.</span>")
            # 👱 Ponytail: Rem putaran timer jadi 2000ms (2 detik) agar terminal tidak kebanjiran error log OpenCV, lalu coba open ulang
            self.timer.setInterval(2000)
            self.cap.release()
            self._open_camera()
            return

        # 👱 Ponytail: Kamera sehat, pastikan kecepatan timer normal kembali ke 30ms (33 FPS)
        if self.timer.interval() != 30:
            self.timer.setInterval(30)
        
        # 4. Proses Logika & Render Deteksi
        frame, pesan_ui = KameraProses.proses_frame(frame, self.model)
        
        # 5. Render ke PyQt
        # Menjaga judul STATUS KAMERA agar tidak hilang saat ditimpa pesan_ui
        self.status_label.setText(f"<span style='color:#94a3b8; font-size:13px;'>STATUS KAMERA</span><br/><span style='color:{status_color}; font-size:18px; font-weight:bold;'>{pesan_ui}</span>")
        
        # 🐎 ponytail: Update info QTY dan SISI (dipindah dari kamera)
        if p_no and current_status != "STANDBY":
            side_text = "FRONT" if state.current_side == "F" else "REAR"
            self.info_label.setText(f"<span style='color:#10b981; font-size:13px; font-weight:bold;'>SISA QTY: {sisa_qty}/{target_qty}  |  SISI: {side_text}</span>")
        else:
            self.info_label.setText("<span style='color:#cbd5e1; font-size:13px; font-weight:bold;'>QTY: - | SISI: -</span>")
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 👱 Ponytail: Mencegah PyQt memory corruption dengan mendefinisikan bytesPerLine
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        pixmap = QPixmap(qt_image).scaled(self.video_label.width(), self.video_label.height(), Qt.AspectRatioMode.KeepAspectRatio)
        self.video_label.setPixmap(pixmap)

        # Cek Popup Part OK (Pop Up di Operator Screen)
        should_popup_ok = False
        should_popup_flip = False
        with state.lock:
            if getattr(state, 'part_ok_popup', False):
                state.part_ok_popup = False
                should_popup_ok = True
            if getattr(state, 'flip_part_popup', False):
                state.flip_part_popup = False
                should_popup_flip = True

        if should_popup_flip or should_popup_ok:
            details = state.last_inspection_details
            lbl_terdeteksi = details.get("label_terdeteksi", "-")
            avg_conf = details.get("avg_confidence", "-")
            found_labels = details.get("found_labels", "-")
            
            # Format list string (replace \n with <br>)
            found_labels_html = found_labels.replace('\n', '<br>')
            
            if should_popup_flip:
                title = "BALIK PART"
                header_msg = "🔄 SISI DEPAN OK!"
                sub_msg = "Balik Part ke SISI BELAKANG."
            else:
                title = "INSPEKSI OK"
                header_msg = "✅ PART BERHASIL TERDETEKSI!"
                sub_msg = "Semua label terdeteksi dan memenuhi standar confidence."
                
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(title)
            msg_box.setIcon(QMessageBox.Icon.Information)
            
            # 🐎 ponytail: Gunakan HTML text agar format lebih rapi (Teks instruksi putih terang)
            html_text = f"""
            <h3 style='margin-bottom: 5px;'>{header_msg}</h3>
            <p style='color: #ffffff; font-size: 15px; font-weight: bold;'>{sub_msg}</p>
            <hr>
            <table cellpadding='4'>
                <tr>
                    <td><b>Label Terdeteksi</b></td>
                    <td>: {lbl_terdeteksi}</td>
                </tr>
                <tr>
                    <td><b>Rata-rata Confidence</b></td>
                    <td>: {avg_conf}</td>
                </tr>
            </table>
            <br>
            <b>Label yang ditemukan:</b><br>
            <div style='font-family: monospace; color: #10b981; margin-top: 5px;'>
                {found_labels_html}
            </div>
            """
            
            msg_box.setText(html_text)
            msg_box.exec()

        # 6. Tangani NG Popup
        with state.lock:
            status_kamera = state.status

        if status_kamera == "NG" and not self.ng_popup_active:
            self.ng_popup_active = True
            print("\n[HARDWARE] SIRENE ABNORMAL ON!")
            
            # Simpan frame/pixmap terakhir untuk dipajang di Dialog
            self.last_ng_pixmap = pixmap
            
            # Save gambar fisik & Log Database
            os.makedirs("ng_records", exist_ok=True)
            timestamp = int(time.time())
            filename = f"ng_records/NG_{state.id_trans}_{timestamp}.jpg"
            # frame itu BGR format OpenCV, langsung disave
            cv2.imwrite(filename, frame)
            print(f"[SYSTEM] Gambar cacat disimpan di: {filename}")
            
            # Log ke database via background thread
            threading.Thread(target=proses_kamera.log_ng_db, args=(state.id_trans, state.p_no, filename)).start()
            
            # Gunakan QTimer agar modal dialog tidak memblokir render frame terakhir secara total
            QTimer.singleShot(100, self.show_ng_popup)
            
    def show_ng_popup(self):
        dialog = NGValidationDialog(self.last_ng_pixmap, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            print("[HARDWARE] SIRENE OFF!")
            with state.lock:
                state.status = "RUNNING"
                state.cooldown_until = time.time() + 2.0
            self.ng_popup_active = False
        else:
            # Jika diclose silang paksa, panggil lagi
            self.show_ng_popup()

    def closeEvent(self, event):
        with state.lock:
            current_status = state.status
            
        if current_status not in ["STANDBY", "COMPLETED"]:
            QMessageBox.warning(self, "Peringatan", f"Aplikasi sedang berjalan (Status: {current_status})!\nSelesaikan inspeksi terlebih dahulu sebelum menutup aplikasi.")
            event.ignore()
            return
            
        self.cap.release()
        print("Program closed.")
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = YoloApp()
    window.showMaximized()
    sys.exit(app.exec())
