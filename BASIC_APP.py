import sys
import os
import time
import json
import threading
import logging
import warnings
import webbrowser

import cv2
import uvicorn
import requests
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget, QApplication, QMessageBox, QPushButton, QHBoxLayout, QSizePolicy, QInputDialog, QDialog, QLineEdit, QFrame
from PyQt6.QtGui import QImage, QPixmap

from database_config import SessionLocal, CameraConfig, User
from terima_dari_sison import router as camera_router
from proses_kamera import state, KameraProses
import proses_kamera
import admin_router

warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.getLogger('ultralytics').setLevel(logging.WARNING)
logging.getLogger().setLevel(logging.ERROR)

def authenticate_and_get_role(username: str, pin: str, allowed_roles: list) -> str:
    if username == "admin" and pin == "1234":
        return "admin" # Fail-safe bawaan
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username, User.password == pin, User.is_active == True).first()
        if not user:
            return None
        if user.role not in allowed_roles:
            return None
        return user.role
    except Exception as e:
        print(f"Auth error: {e}")
        return None
    finally:
        db.close()

# Setup FastAPI App
app_fastapi = FastAPI(title="Sistem Kamera API")
app_fastapi.include_router(camera_router, prefix="/api")

# --- CUSTOM WEB ADMIN CONFIGURATION ---

app_fastapi.include_router(admin_router.router, prefix="/api/admin")
app_fastapi.mount("/admin", StaticFiles(directory="web_admin", html=True), name="admin")
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
        role = authenticate_and_get_role(self.username_input.text(), self.pin_input.text(), ["admin", "pengawas"])
        if role:
            self.accept()
        else:
            QMessageBox.warning(self, "Ditolak", "Username/PIN Salah atau Anda tidak terdaftar!")
            self.pin_input.clear()

class AdminAuthDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Otentikasi Admin")
        self.setStyleSheet("background-color: #222; color: white; font-size: 24px;")
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 1. Pesan
        msg_label = QLabel("🔐 OTENTIKASI ADMIN 🔐\nMasukkan PIN untuk mengakses Dashboard Admin.", self)
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_label.setStyleSheet("color: #44aaff; font-weight: bold; font-size: 26px;")
        layout.addWidget(msg_label)
        
        # 2. Input Username
        self.username_input = QLineEdit(self)
        self.username_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.username_input.setPlaceholderText("Masukkan Username...")
        self.username_input.setStyleSheet("background-color: white; color: black; font-size: 32px; padding: 10px; border-radius: 8px; margin-bottom: 10px;")
        layout.addWidget(self.username_input)
        
        # 3. Input PIN
        self.pin_input = QLineEdit(self)
        self.pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pin_input.setPlaceholderText("Masukkan PIN Admin...")
        self.pin_input.setStyleSheet("background-color: white; color: black; font-size: 32px; padding: 10px; border-radius: 8px;")
        layout.addWidget(self.pin_input)
        
        # 3. Tombol
        btn_layout = QHBoxLayout()
        self.btn_login = QPushButton("LOGIN", self)
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.setStyleSheet("""
            QPushButton {
                background-color: #44aaff; 
                color: white; 
                font-weight: bold; 
                font-size: 28px; 
                padding: 15px; 
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #66bbff;
            }
        """)
        self.btn_login.clicked.connect(self.check_pin)
        
        btn_layout.addWidget(self.btn_login)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def check_pin(self):
        role = authenticate_and_get_role(self.username_input.text(), self.pin_input.text(), ["admin", "pengawas"])
        if role:
            self.authenticated_role = role
            self.accept()
        else:
            QMessageBox.warning(self, "Ditolak", "Username/PIN Salah atau Anda tidak terdaftar!")
            self.pin_input.clear()

class YoloApp(QWidget):

    def __init__(self):
        super().__init__()
        # Load Camera Source from DB
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
            print(f"[SYSTEM] Menggunakan sumber kamera: {cam_source}")
        except Exception as e:
            print(f"[WARNING] Gagal membaca konfigurasi kamera dari DB, fallback ke index 0. Error: {e}")
            cam_source = 0

        self.cap = cv2.VideoCapture(cam_source)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)  
        self.model = None # Lazy load model nanti saat Start Sison
        self.current_loaded_p_no = "" # Untuk mendeteksi perubahan part number dari Sison
        self.ng_popup_active = False

        # UI & Timers
        self.initUI()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30) # Refresh 30 FPS
        
        # Start FastAPI
        self.api_thread = threading.Thread(target=run_fastapi, daemon=True)
        self.api_thread.start()

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
        self.hud_frame.setFixedHeight(100)
        hud_layout = QHBoxLayout(self.hud_frame)
        hud_layout.setContentsMargins(20, 10, 20, 10)

        self.part_name = QLabel("<span style='color:#64748b; font-size:16px;'>PART NUMBER</span><br/><span style='color:#f8fafc; font-size:28px; font-weight:bold;'>MENUNGGU SISON...</span>", self)
        self.part_name.setStyleSheet("border: none; background: transparent;")
        self.part_name.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        self.status_label = QLabel("<span style='color:#94a3b8; font-size:16px;'>STATUS MESIN</span><br/><span style='color:#cbd5e1; font-size:28px; font-weight:bold;'>STANDBY</span>", self)
        self.status_label.setStyleSheet("border: none; background: transparent;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
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
        hud_layout.addWidget(self.status_label, stretch=1)
        hud_layout.addWidget(right_container, stretch=1)

        self.btn_demo = QPushButton("🚀 DEMO SISON", self)
        self.btn_demo.setFixedHeight(35)
        self.btn_demo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_demo.setStyleSheet("background-color: #475569; color: white; font-size:14px; font-weight:bold; border-radius: 5px; padding: 0 10px;")
        self.btn_demo.clicked.connect(self.prompt_demo_sison)

        self.btn_mock = QPushButton("📷 MOCK DETECT", self)
        self.btn_mock.setFixedHeight(35)
        self.btn_mock.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mock.setStyleSheet("background-color: #475569; color: white; font-size:14px; font-weight:bold; border-radius: 5px; padding: 0 10px;")
        self.btn_mock.clicked.connect(self.trigger_mock_detect)

        self.btn_mock_ng = QPushButton("🚨 MOCK NG", self)
        self.btn_mock_ng.setFixedHeight(35)
        self.btn_mock_ng.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mock_ng.setStyleSheet("background-color: #ef4444; color: white; font-size:14px; font-weight:bold; border-radius: 5px; padding: 0 10px;")
        self.btn_mock_ng.clicked.connect(self.trigger_mock_ng)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.addWidget(self.btn_demo)
        toolbar_layout.addWidget(self.btn_mock)
        toolbar_layout.addWidget(self.btn_mock_ng)
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
                res = requests.post("http://localhost:8000/api/start", json=data_dict, headers={"X-Api-Key": api_key}, timeout=3)
                if res.status_code == 200:
                    QMessageBox.information(self, "Sukses", "Simulasi Sison Berhasil Dikirim!")
                else:
                    QMessageBox.warning(self, "Gagal", f"Error API: {res.text}")
                    
            except json.JSONDecodeError:
                QMessageBox.warning(self, "Error", "Format JSON Tidak Valid!")
            except Exception as e:
                QMessageBox.critical(self, "Error Jaringan", f"Gagal menghubungi server lokal: {e}")

    def prompt_admin_dashboard(self):
        dialog = AdminAuthDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            role = getattr(dialog, 'authenticated_role', 'pengawas')
            webbrowser.open(f"http://localhost:8000/admin?role={role}")

    def trigger_mock_detect(self):
        with state.lock:
            state.mock_detect_trigger = True

    def trigger_mock_ng(self):
        with state.lock:
            state.status = "NG"

    def update_frame(self):
        # 1. Update text info dari State (Thread-safe)
        with state.lock:
            p_no = state.p_no
            target_qty = state.target_qty
            sisa_qty = state.qty
            current_status = state.status

        qty_selesai = target_qty - sisa_qty
        
        # Update Part Name (Rich Text)
        if p_no:
            self.part_name.setText(f"<span style='color:#eab308; font-size:28px; font-weight:bold;'>{p_no}</span><br/><span style='color:#38bdf8; font-size:18px;'>Target: {target_qty} PCS | Selesai: {qty_selesai} PCS</span>")
        else:
            self.part_name.setText("<span style='color:#64748b; font-size:16px;'>PART NUMBER</span><br/><span style='color:#f8fafc; font-size:28px; font-weight:bold;'>MENUNGGU SISON...</span>")

        # Update Status Label (Rich Text & Colors)
        status_color = "#cbd5e1" # Default Gray
        status_text = "STANDBY"
        
        if current_status == "OK":
            status_color = "#22c55e" # Green
            status_text = "INSPEKSI AKTIF"
            self.hud_frame.setStyleSheet("#hud { background-color: #0f172a; border: none; border-radius: 10px; }")
        elif current_status == "NG":
            status_color = "#ef4444" # Red
            status_text = "NG TERDETEKSI"
            # Blinking effect for NG border
            blink = "red" if int(time.time() * 2) % 2 == 0 else "transparent"
            self.hud_frame.setStyleSheet(f"#hud {{ background-color: #0f172a; border: 4px solid {blink}; border-radius: 10px; }}")
        else:
            self.hud_frame.setStyleSheet("#hud { background-color: #0f172a; border: none; border-radius: 10px; }")
            
        self.status_label.setText(f"<span style='color:#94a3b8; font-size:16px;'>STATUS MESIN</span><br/><span style='color:{status_color}; font-size:28px; font-weight:bold;'>{status_text}</span>")

        # 2. Lazy Load Model (Ganti model otomatis jika p_no berubah)
        if p_no != "" and p_no != self.current_loaded_p_no:
            self.model = KameraProses.load_model(p_no)
            self.current_loaded_p_no = p_no

        # 3. Baca Kamera
        ret, frame = self.cap.read()
        if not ret: return
        
        # 4. Proses Logika & Render Deteksi
        frame, pesan_ui = KameraProses.proses_frame(frame, self.model)
        
        # 5. Render ke PyQt
        self.status_label.setText(pesan_ui)
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qt_image = QImage(rgb_image.data, rgb_image.shape[1], rgb_image.shape[0], QImage.Format.Format_RGB888)
        pixmap = QPixmap(qt_image).scaled(self.video_label.width(), self.video_label.height(), Qt.AspectRatioMode.KeepAspectRatio)
        self.video_label.setPixmap(pixmap)

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
            
        if current_status != "STANDBY":
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
