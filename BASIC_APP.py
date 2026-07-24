import sys
import os
import shutil
import threading
import uvicorn
from fastapi import FastAPI
import cv2
import logging
import warnings

from PyQt6.QtCore import QTimer, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget, QApplication, QMessageBox, QPushButton, QHBoxLayout, QSizePolicy, QInputDialog, QFileDialog, QDialog, QLineEdit
from PyQt6.QtGui import QImage, QPixmap
from ultralytics import YOLO

# Import Screaming Architecture (Struktur Ponytail)
import importlib
terima_sison = importlib.import_module("1_terima_dari_sison")
camera_router = terima_sison.router

proses_kamera = importlib.import_module("2_proses_kamera")
state = proses_kamera.state
KameraProses = proses_kamera.KameraProses

warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.getLogger('ultralytics').setLevel(logging.WARNING)
logging.getLogger().setLevel(logging.ERROR)

# Setup FastAPI App
app_fastapi = FastAPI(title="Sistem Kamera API")
app_fastapi.include_router(camera_router, prefix="/api")

# --- CUSTOM WEB ADMIN CONFIGURATION ---
from fastapi.staticfiles import StaticFiles
import admin_api

app_fastapi.include_router(admin_api.router, prefix="/api/admin")
app_fastapi.mount("/admin", StaticFiles(directory="web_admin", html=True), name="admin")
# ----------------------------------------

def run_fastapi():
    """Jalankan uvicorn server di background thread"""
    uvicorn.run(app_fastapi, host="0.0.0.0", port=8000, log_level="error")

class NGValidationDialog(QDialog):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NG Terdeteksi!")
        self.setStyleSheet("font-size: 18px;")
        
        layout = QVBoxLayout()
        
        # 1. Gambar Bukti Cacat
        self.img_label = QLabel(self)
        self.img_label.setPixmap(pixmap.scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio))
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet("border: 2px solid red;")
        layout.addWidget(self.img_label)
        
        # 2. Pesan
        msg_label = QLabel("Komponen NG! Masukkan PIN Pengawas untuk validasi:", self)
        msg_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(msg_label)
        
        # 3. Input PIN
        self.pin_input = QLineEdit(self)
        self.pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.pin_input)
        
        # 4. Tombol
        btn_layout = QHBoxLayout()
        self.btn_validasi = QPushButton("Validasi", self)
        self.btn_validasi.setStyleSheet("background-color: #ffcccc; font-weight: bold;")
        self.btn_validasi.clicked.connect(self.check_pin)
        
        btn_layout.addWidget(self.btn_validasi)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def check_pin(self):
        if self.pin_input.text() == "1234":
            self.accept()
        else:
            QMessageBox.warning(self, "Ditolak", "PIN Salah! Anda tidak bisa melanjutkan.")
            self.pin_input.clear()

class YoloApp(QWidget):

    def __init__(self):
        super().__init__()
        # Kamera & Model Default
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)  
        self.model = YOLO('yolov8n.pt', verbose=False)
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
        self.setStyleSheet("border:2px solid black; font-size: 24px;")

        self.video_label = QLabel(self)
        self.video_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_label.setMinimumSize(1, 1)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("padding: 0px; margin: 0px; border: 2px solid black; background-color: #111;")
      
        self.status_label = QLabel("Status: STANDBY (Menunggu Sison...)", self)
        self.status_label.setFixedHeight(45)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("background-color: white; color: black; border: 2px solid black; font-size:18px;")
        
        self.part_name = QLabel("Part: None | Qty: 0", self)
        self.part_name.setFixedHeight(45)
        self.part_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.part_name.setStyleSheet("background-color: white; color: black; border: 2px solid black; font-size:18px;")

        self.btn_demo = QPushButton("DEMO SISON", self)
        self.btn_demo.setFixedHeight(45)
        self.btn_demo.setStyleSheet("background-color: #ffcccc; color: black; font-size:18px;")
        self.btn_demo.clicked.connect(self.prompt_demo_sison)

        self.btn_admin = QPushButton("ADMIN DASHBOARD", self)
        self.btn_admin.setFixedHeight(45)
        self.btn_admin.setStyleSheet("background-color: #cce5ff; color: black; font-size:18px;")
        self.btn_admin.clicked.connect(self.prompt_admin_dashboard)

        self.btn_mock = QPushButton("MOCK DETECT", self)
        self.btn_mock.setFixedHeight(45)
        self.btn_mock.setStyleSheet("background-color: #ffffcc; color: black; font-size:18px;")
        self.btn_mock.clicked.connect(self.trigger_mock_detect)

        self.btn_mock_ng = QPushButton("MOCK NG", self)
        self.btn_mock_ng.setFixedHeight(45)
        self.btn_mock_ng.setStyleSheet("background-color: #ff9999; color: black; font-size:18px;")
        self.btn_mock_ng.clicked.connect(self.trigger_mock_ng)

        sublayout = QHBoxLayout()
        sublayout.addWidget(self.status_label)
        sublayout.addWidget(self.btn_admin)
        sublayout.addWidget(self.btn_demo)
        sublayout.addWidget(self.btn_mock)
        sublayout.addWidget(self.btn_mock_ng)

        layout = QVBoxLayout()
        layout.addLayout(sublayout)
        layout.addWidget(self.part_name)
        layout.addWidget(self.video_label)
        self.setLayout(layout)

    def prompt_demo_sison(self):
        import json
        import requests
        
        import time
        default_json = json.dumps({
            "id_trans": f"DEMO-{int(time.time())}",
            "lot": "LOT-999",
            "p_no": "74231-0K550-00",
            "unique_no": "UNQ-000",
            "p_name": "Demo Part",
            "qty": 1
        }, indent=4)
        
        teks, ok = QInputDialog.getMultiLineText(self, "Simulator Sison", "Edit JSON payload (Peringatan: Pastikan format benar!):", default_json)
        if ok and teks:
            try:
                # Validasi format
                data_dict = json.loads(teks)
                
                # Kirim HTTP POST ke API FastAPI kita sendiri
                res = requests.post("http://localhost:8000/api/start", json=data_dict, timeout=3)
                
                if res.status_code == 200:
                    QMessageBox.information(self, "Sukses", "Simulasi Sison Berhasil Dikirim!")
                else:
                    QMessageBox.warning(self, "Gagal", f"Error API: {res.text}")
                    
            except json.JSONDecodeError:
                QMessageBox.warning(self, "Error", "Format JSON Tidak Valid!")
            except Exception as e:
                QMessageBox.critical(self, "Error Jaringan", f"Gagal menghubungi server lokal: {e}")

    def prompt_admin_dashboard(self):
        pin, ok = QInputDialog.getText(self, "Otentikasi Admin", "Masukkan PIN Admin untuk akses Dashboard:")
        if ok and pin == "1234":
            import webbrowser
            webbrowser.open("http://localhost:8000/admin")
        elif ok:
            QMessageBox.warning(self, "Ditolak", "PIN Salah!")

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

        qty_selesai = target_qty - sisa_qty
        self.part_name.setText(f"Part: {p_no} | Target: {target_qty} | Selesai: {qty_selesai}")

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
            import time
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
        import time
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
        self.cap.release()
        print("Program closed.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = YoloApp()
    window.showMaximized()
    sys.exit(app.exec())
