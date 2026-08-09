import json
import time
import random
import requests
from PyQt6.QtWidgets import QInputDialog, QMessageBox
from database import SessionLocal, SisonConfig

def show_demo_sison_dialog(parent):
    """Menampilkan dialog input JSON interaktif untuk simulasi trigger SISON."""
    default_json = json.dumps({
        "id_trans": f"DEMO-{int(time.time())}",
        "lot": f"LOT-{random.randint(1000, 9999)}",
        "p_no": "74231-0K550-00",
        "unique_no": f"UNQ-{random.randint(1000, 9999)}",
        "p_name": random.choice(["Demo Part A", "Demo Part B", "Demo Part C"]),
        "qty": 1
    }, indent=4)
    
    teks, ok = QInputDialog.getMultiLineText(parent, "Simulator Sison", "Edit JSON payload (Peringatan: Pastikan format benar!):", default_json)
    if ok and teks:
        try:
            data_dict = json.loads(teks)
            db_session = SessionLocal()
            try:
                cfg = db_session.query(SisonConfig).first()
                api_key = cfg.api_key if cfg else "kamera-secret-key"
            finally:
                db_session.close()

            res = requests.post("http://localhost:8000/api/start", json=data_dict, headers={"Authorization": f"Bearer {api_key}"}, timeout=3)
            if res.status_code == 200:
                QMessageBox.information(parent, "Sukses", "Simulasi Sison Berhasil Dikirim!")
            else:
                QMessageBox.warning(parent, "Gagal", f"Error API: {res.text}")
                
        except json.JSONDecodeError:
            QMessageBox.warning(parent, "Error", "Format JSON Tidak Valid!")
        except Exception as e:
            QMessageBox.critical(parent, "Error Jaringan", f"Gagal menghubungi server lokal: {e}")
