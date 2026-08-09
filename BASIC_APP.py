"""
🚀 Sistem Kamera Inspeksi AI & Quality Control
Entry point aplikasi desktop PyQt6 & runner background FastAPI.
Seluruh modul telah dipecah secara clean & modular ke dalam:
- core/         : Engine inferensi YOLOv8, State, Rules, dan Kamera capture
- database/     : Koneksi DB, Model ORM, Seeder, dan Migrasi
- api/          : FastAPI server, Auth, dan Router REST Web Admin
- integrations/ : Webhook SISON dan SQLite Offline Buffer
- ui/           : Desktop UI PyQt6, Dialogs, dan Heads-Up Display
"""
import sys
import os
import logging
import warnings
from dotenv import load_dotenv

# 1. Load Environment Configuration
load_dotenv()

# 2. Mute verbose OpenCV & Ultralytics terminal logging
os.environ["OPENCV_LOG_LEVEL"] = "FATAL"
os.environ["OPENCV_VIDEOIO_DEBUG"] = "0"
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.getLogger('ultralytics').setLevel(logging.WARNING)
logging.getLogger().setLevel(logging.ERROR)

import cv2
if hasattr(cv2, 'setLogLevel'):
    cv2.setLogLevel(0)

from PyQt6.QtWidgets import QApplication
from ui import YoloApp

def main():
    """Jalankan aplikasi desktop PyQt6."""
    app = QApplication(sys.argv)
    window = YoloApp()
    window.showMaximized()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
