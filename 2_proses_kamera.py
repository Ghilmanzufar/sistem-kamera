import threading
import cv2
import time
import os
from typing import Any
from ultralytics import YOLO

# Import untuk kirim laporan jika selesai
import importlib
kirim_sison = importlib.import_module("3_kirim_ke_sison")

# Import DB untuk history log
from database_config import SessionLocal, Transaction, InspectionLog
from sqlalchemy.sql import func

def log_inspeksi_db(id_trans: str, part_no: str, status_deteksi: str):
    """Fungsi helper yang berjalan di background thread untuk mencatat history ke DB"""
    try:
        with SessionLocal() as db:
            # 1. Catat log inspeksi per item
            log = InspectionLog(id_trans=id_trans, part_no=part_no, detection_status=status_deteksi, confidence_score=1.0)
            db.add(log)
            
            # 2. Update qty actual di tabel transaksi
            trans = db.query(Transaction).filter(Transaction.id_trans == id_trans).first()
            if trans:
                trans.qty_actual += 1
                if trans.qty_actual >= trans.target_qty:
                    trans.status = 2 # 2 = Selesai
                    trans.end_time = func.now()
            
            db.commit()
    except Exception as e:
        print(f"Gagal mencatat log inspeksi ke DB: {e}")

def log_ng_db(id_trans: str, part_no: str, image_path: str):
    """Fungsi helper untuk mencatat history NG ke DB"""
    try:
        with SessionLocal() as db:
            log = InspectionLog(id_trans=id_trans, part_no=part_no, detection_status="NG", image_path=image_path, confidence_score=1.0)
            db.add(log)
            db.commit()
    except Exception as e:
        print(f"Gagal mencatat log NG ke DB: {e}")

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
        self.daftar_sisi: list = []
        self.daftar_sisi: list = []
        self.progress_sisi: int = 0
        self.cooldown_until: float = 0.0
        self.mock_detect_trigger: bool = False

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
            daftar_sisi = state.daftar_sisi
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
                        
            # CEK MOCK DETECT TRIGGER
            with state.lock:
                if getattr(state, 'mock_detect_trigger', False):
                    # Inject label_counts sesuai aturan_sisi aktif
                    if len(state.daftar_sisi) > 0 and state.progress_sisi < len(state.daftar_sisi):
                        nama_sisi_aktif = state.daftar_sisi[state.progress_sisi]
                        syarat_sisi_ini = [r for r in state.aturan_sisi if r.get("sisi") == nama_sisi_aktif]
                        for req in syarat_sisi_ini:
                            label_counts[req["nama_komponen"]] = req["qty"]
                            print(f"[MOCK] Injeksi {req['nama_komponen']} sejumlah {req['qty']}")
                    state.mock_detect_trigger = False
            
            # NG Detection
            if label_counts.get("ng", 0) > 0 and now >= cooldown_until:
                with state.lock:
                    state.status = "NG"
                status = "NG"
            
            # Logika Multi Sisi (Flat List Native)
            elif len(daftar_sisi) > 0 and now >= cooldown_until:
                if progress_sisi < len(daftar_sisi):
                    nama_sisi_aktif = daftar_sisi[progress_sisi]
                    
                    # Filter aturan flat berdasarkan sisi aktif
                    syarat_sisi_ini = [r for r in aturan_sisi if r.get("sisi") == nama_sisi_aktif]
                    
                    # Bangun pesan UI spesifik
                    info_kebutuhan = ", ".join([f"{r['nama_komponen']}({r['qty']})" for r in syarat_sisi_ini])
                    pesan_ui = f"Cek {nama_sisi_aktif}: Butuh {info_kebutuhan}"
                    color_status = (0, 255, 255)
                    
                    # Validasi
                    sisi_valid = True
                    for req in syarat_sisi_ini:
                        if label_counts.get(req["nama_komponen"], 0) < req["qty"]:
                            sisi_valid = False
                            break
                            
                    if sisi_valid and len(syarat_sisi_ini) > 0:
                        with state.lock:
                            state.progress_sisi += 1
                            if state.progress_sisi >= len(state.daftar_sisi):
                                state.qty -= 1
                                state.progress_sisi = 0
                                
                                # --- Panggil pencatatan database di background ---
                                threading.Thread(target=log_inspeksi_db, args=(state.id_trans, state.p_no, "OK")).start()
                                
                                if state.qty <= 0:
                                    # Panggil Sison API di thread terpisah (agar tidak memblokir kamera)
                                    threading.Thread(target=kirim_sison.SisonSender.send_callback, args=(state.id_trans, 1)).start()
                                    state.status = "STANDBY"
                                    state.cooldown_until = now + 5.0
                                    pesan_ui = "INSPEKSI SELESAI! (Dikirim ke Sison)"
                                    color_status = (0, 255, 0)
                                else:
                                    state.cooldown_until = now + 2.0
                                    pesan_ui = "Part LENGKAP! Ganti part."
                                    color_status = (0, 255, 0)
                            else:
                                state.cooldown_until = now + 2.0
                                pesan_ui = f"{nama_sisi_aktif} OK! Putar part."
                                color_status = (0, 255, 0)

        elif status == "NG":
            pesan_ui = "STATUS: NG! INPUT PIN (1234) UNTUK VALIDASI."
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
