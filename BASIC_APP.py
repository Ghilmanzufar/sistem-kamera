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
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget, QApplication, QMessageBox, QPushButton, QHBoxLayout, QSizePolicy, QInputDialog, QFileDialog
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

def run_fastapi():
    """Jalankan uvicorn server di background thread"""
    uvicorn.run(app_fastapi, host="0.0.0.0", port=8000, log_level="error")


class YoloApp(QWidget):
    # PyQt Signal untuk aman mengeksekusi Override UI jika ditekan tombol
    btn_override_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        # Kamera & Model Default
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)  
        self.model = YOLO('yolov8n.pt', verbose=False)
        self.current_loaded_p_no = "" # Untuk mendeteksi perubahan part number dari Sison

        # UI & Timers
        self.initUI()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30) # Refresh 30 FPS
        
        self.btn_override_signal.connect(self.handle_manual_override)
        
        # Start FastAPI
        self.api_thread = threading.Thread(target=run_fastapi, daemon=True)
        self.api_thread.start()

    def initUI(self):
        self.setWindowTitle("Sistem Kamera Inspeksi")
        self.setStyleSheet("border:2px solid black; font-size: 24px;")

        self.video_label = QLabel(self)
        self.video_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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

        # Tombol Import Model YOLO (Manajemen Manual Opsi 3)
        self.btn_import = QPushButton("IMPORT MODEL (.pt)", self)
        self.btn_import.setFixedHeight(45)
        self.btn_import.setStyleSheet("background-color: #ccffcc; color: black; font-size:18px;")
        self.btn_import.clicked.connect(self.prompt_import_model)

        self.btn_override = QPushButton("MANUAL OVERRIDE (PIN)", self)
        self.btn_override.setFixedHeight(45)
        self.btn_override.setStyleSheet("background-color: #ffcccc; color: black; font-size:18px;")
        self.btn_override.clicked.connect(self.prompt_manual_override)

        sublayout = QHBoxLayout()
        sublayout.addWidget(self.btn_import)
        sublayout.addWidget(self.status_label)
        sublayout.addWidget(self.btn_override)

        layout = QVBoxLayout()
        layout.addLayout(sublayout)
        layout.addWidget(self.part_name)
        layout.addWidget(self.video_label)
        self.setLayout(layout)

    def prompt_import_model(self):
        pin, ok = QInputDialog.getText(self, "Otentikasi Pengawas", "Masukkan PIN Supervisor untuk manajemen file:")
        if ok and pin == "1234":
            # Buka File Dialog
            file_path, _ = QFileDialog.getOpenFileName(self, "Pilih File Model YOLO", "", "YOLO Model (*.pt)")
            if file_path:
                p_no, ok_p_no = QInputDialog.getText(self, "Tentukan Part Number", "Masukkan Part Number (contoh: 74231-0k550):")
                if ok_p_no and p_no.strip() != "":
                    weights_dir = os.path.join(os.getcwd(), "weights")
                    os.makedirs(weights_dir, exist_ok=True)
                    dest_path = os.path.join(weights_dir, f"{p_no.strip()}.pt")
                    try:
                        shutil.copy(file_path, dest_path)
                        QMessageBox.information(self, "Sukses", f"Model berhasil diimpor dan disimpan sebagai:\n{dest_path}")
                    except Exception as e:
                        QMessageBox.critical(self, "Gagal", f"Terjadi kesalahan saat mengopi file:\n{str(e)}")
                else:
                    QMessageBox.warning(self, "Batal", "Part Number tidak boleh kosong.")
        elif ok:
            QMessageBox.warning(self, "Ditolak", "PIN Salah!")

    def prompt_manual_override(self):
        with state.lock:
            current_status = state.status
            
        if current_status == "NG":
            pin, ok = QInputDialog.getText(self, "Override NG", "Masukkan PIN Supervisor:")
            if ok:
                self.btn_override_signal.emit(pin)

    @pyqtSlot(str)
    def handle_manual_override(self, pin):
        if pin == "1234":
            with state.lock:
                import time
                state.status = "RUNNING"
                state.cooldown_until = time.time() + 2.0
        else:
            QMessageBox.warning(self, "Error", "PIN Salah!")

    def update_frame(self):
        # 1. Update text info dari State (Thread-safe)
        with state.lock:
            p_no = state.p_no
            target_qty = state.target_qty

        self.part_name.setText(f"Part: {p_no} | Target Qty: {target_qty}")

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

    def closeEvent(self, event):
        self.cap.release()
        print("Program closed.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = YoloApp()
    window.showMaximized()
    sys.exit(app.exec())
