import threading
import cv2
import time
import os
from typing import Any
from ultralytics import YOLO

# Import untuk kirim laporan jika selesai
import importlib
kirim_sison = importlib.import_module("3_kirim_ke_sison")

# ==============================================================
# STATE (Pusat Data Antar Thread)
# ==============================================================
class SystemState:
    def __init__(self):
        self.lock = threading.Lock()
        self.status: str = "STANDBY"
        self.id_trans: str = ""
        self.p_no: str = ""
        self.qty: int = 0
        self.target_qty: int = 0
        self.aturan_sisi: list = []
        self.progress_sisi: int = 0
        self.cooldown_until: float = 0.0

state = SystemState()

# ==============================================================
# LOGIKA YOLO & MESIN STATUS
# ==============================================================
class KameraProses:
    @staticmethod
    def load_model(p_no: str):
        """
        Load model YOLO berdasarkan p_no dari folder weights/.
        Jika tidak ada, fallback ke yolov8n.pt bawaan.
        """
        weights_dir = os.path.join(os.getcwd(), "weights")
        if not os.path.exists(weights_dir):
            os.makedirs(weights_dir)
            
        model_path = os.path.join(weights_dir, f"{p_no}.pt")
        
        try:
            if os.path.exists(model_path):
                print(f"Loading custom model for {p_no}: {model_path}")
                return YOLO(model_path, verbose=False)
            else:
                return YOLO("yolov8n.pt", verbose=False)
        except Exception as e:
            print(f"Error loading model {p_no}: {e}")
            return YOLO("yolov8n.pt", verbose=False)

    @staticmethod
    def proses_frame(frame, model):
        """
        Mengevaluasi state machine dan menjalankan tracking YOLO.
        """
        with state.lock:
            status = state.status
            qty = state.qty
            target_qty = state.target_qty
            progress_sisi = state.progress_sisi
            aturan_sisi = state.aturan_sisi
            cooldown_until = state.cooldown_until
            id_trans = state.id_trans
            
        now = time.time()
        pesan_ui = f"Status: {status}"
        color_status = (255, 255, 0)

        if status == "RUNNING" and qty > 0:
            results = model.track(frame, persist=True, verbose=False)
            label_counts = {}
            
            for result in results:
                if result.boxes is not None:
                    for box in result.boxes:
                        cls = int(box.cls[0])
                        label_name = model.names[cls].lower()
                        label_counts[label_name] = label_counts.get(label_name, 0) + 1
                        
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(frame, label_name, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # NG Detection
            if label_counts.get("ng", 0) > 0 and now >= cooldown_until:
                with state.lock:
                    state.status = "NG"
                status = "NG"
            
            # Logika Multi Sisi
            elif len(aturan_sisi) > 0 and now >= cooldown_until:
                if progress_sisi < len(aturan_sisi):
                    sisi_aktif = aturan_sisi[progress_sisi]
                    syarat = sisi_aktif.get("komponen_wajib", {})
                    nama_sisi = sisi_aktif.get("nama_sisi", f"Sisi {progress_sisi + 1}")
                    
                    pesan_ui = f"Tunggu {nama_sisi}..."
                    color_status = (0, 255, 255)
                    
                    sisi_valid = True
                    for label, wajib_qty in syarat.items():
                        if label_counts.get(label, 0) < wajib_qty:
                            sisi_valid = False
                            break
                            
                    if sisi_valid and len(syarat) > 0:
                        with state.lock:
                            state.progress_sisi += 1
                            if state.progress_sisi >= len(state.aturan_sisi):
                                state.qty -= 1
                                state.progress_sisi = 0
                                state.cooldown_until = now + 2.0
                                pesan_ui = "Part LENGKAP! Ganti part."
                                color_status = (0, 255, 0)
                            else:
                                state.cooldown_until = now + 2.0
                                pesan_ui = f"{nama_sisi} OK! Putar part."
                                color_status = (0, 255, 0)

        elif status == "NG":
            pesan_ui = "STATUS: NG! INPUT PIN (1234) UNTUK OVERRIDE."
            color_status = (0, 0, 255)
            overlay = frame.copy()
            cv2.rectangle(overlay, (0,0), (frame.shape[1], frame.shape[0]), (0,0,255), -1)
            cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
            
        elif status == "RUNNING" and qty <= 0 and target_qty > 0:
            with state.lock:
                state.status = "COMPLETED"
            status = "COMPLETED"
            kirim_sison.SisonSender.send_callback(id_trans, 1)
            pesan_ui = "INSPEKSI SELESAI. MENGHUBUNGI SISON..."
            color_status = (0, 255, 0)
            
        elif status == "COMPLETED":
            pesan_ui = "SELESAI. TUNGGU INSTRUKSI SISON."
            color_status = (0, 255, 0)

        # Draw Overlay Text
        cv2.putText(frame, pesan_ui, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color_status, 3)
        with state.lock:
            sisa_qty_str = f"Sisa Qty: {state.qty} / {state.target_qty}"
        cv2.putText(frame, sisa_qty_str, (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        return frame, pesan_ui
