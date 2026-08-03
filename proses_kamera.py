import threading
import cv2
import time
import os
import re
from typing import Any
from ultralytics import YOLO

# Import untuk kirim laporan jika selesai
import kirim_ke_sison as kirim_sison

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
        self.progress_sisi: int = 0
        self.cooldown_until: float = 0.0
        self.mock_detect_trigger: bool = False
        self.part_ok_popup: bool = False
        self.current_side: str = "F"      # "F" = Front, "R" = Rear
        self.flip_part_popup: bool = False # trigger instruksi "Balik Part" ke operator
        self.last_inspection_details: dict = {} # 🐎 ponytail: Menyimpan detail inspeksi terakhir

state = SystemState()

# ==============================================================
# HELPER DUAL-SIDE
# ==============================================================
def _get_rules_for_side(all_rules: list, side: str) -> list:
    """Filter aturan berdasarkan prefix sisi ('f-' atau 'r-').
    ponytail: label tanpa prefix → legacy single-side, pakai semua rule.
    """
    prefix = side.lower() + "-"
    filtered = [r for r in all_rules if r.get("nama_komponen", "").lower().startswith(prefix)]
    return filtered if filtered else all_rules

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
        
        if os.path.exists(model_path):
            print(f"Loading custom model for {p_no}: {model_path}")
            try:
                return YOLO(model_path, verbose=False)
            except Exception as e:
                print(f"Error loading model {p_no}: {e}")
        print(f"[WARN] Tidak ada model untuk {p_no}. Gunakan MOCK DETECT untuk demo.")
        return None

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
            current_side = state.current_side
            
        now = time.time()
        pesan_ui = f"Status: {status}"
        color_status = (255, 255, 0)
        _debug_interval = getattr(KameraProses, '_last_debug_print', 0)

        if status == "RUNNING" and qty > 0:
            label_counts = {}
            label_max_conf = {} # 🐎 ponytail: Simpan max confidence per label
            detected_confidences = []
            min_conf_failed = False

            if model is not None:
                results = model.track(frame, persist=True, verbose=False)
                for result in results:
                    if result.boxes is not None:
                        for box in result.boxes:
                            cls = int(box.cls[0])
                            label_name = model.names[cls].lower()
                            conf = float(box.conf[0]) if hasattr(box, 'conf') and box.conf is not None else 0.0
                            label_counts[label_name] = label_counts.get(label_name, 0) + 1
                            label_max_conf[label_name] = max(label_max_conf.get(label_name, 0.0), conf)
                            detected_confidences.append(conf)
                            
                            # Cari min_confidence label ini di aturan aktif sisi
                            req = next((r for r in aturan_sisi if r.get("nama_komponen", "").lower() == label_name), None)
                            min_conf = req.get("min_confidence", 0.70) if req else 0.70
                            
                            # Warna Box: Merah jika conf < min_conf, Hijau jika conf >= min_conf
                            if conf >= min_conf:
                                box_color = (0, 255, 0) # Hijau
                            else:
                                box_color = (0, 0, 255) # Merah
                                min_conf_failed = True

                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
                            text = f"{label_name.upper()} ({conf*100:.0f}%)"
                            cv2.putText(frame, text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)
            else:
                pesan_ui = "Mode Demo: Tidak ada model custom. Gunakan tombol MOCK DETECT."
                color_status = (255, 165, 0)  # Orange

            # CEK MOCK DETECT TRIGGER
            was_mock_triggered = False
            with state.lock:
                if getattr(state, 'mock_detect_trigger', False):
                    was_mock_triggered = True
                    for req in state.aturan_sisi:
                        lbl = req.get("nama_komponen", "").lower()
                        min_c = req.get("min_confidence", 0.70)
                        label_counts[lbl] = 1
                        label_max_conf[lbl] = min_c + 0.05
                        detected_confidences.append(min_c + 0.05)
                        print(f"[MOCK] Injeksi {lbl} dengan conf {min_c + 0.05:.2f}")
                    state.mock_detect_trigger = False

            # Filter rule sesuai sisi aktif
            aturan_aktif = _get_rules_for_side(aturan_sisi, current_side)
            has_rear = any(r.get("nama_komponen", "").lower().startswith("r-") for r in aturan_sisi)

            # Hitung Statistik Confidence & Total Label (per sisi aktif)
            required_labels = list(set(r.get("nama_komponen", "").lower() for r in aturan_aktif if r.get("nama_komponen")))
            target_avg_conf = aturan_aktif[0].get("avg_confidence", 0.75) if aturan_aktif else 0.75
            target_coverage = aturan_aktif[0].get("min_coverage", 1.0) if aturan_aktif else 1.0
            
            current_avg_conf = (sum(detected_confidences) / len(detected_confidences)) if detected_confidences else 0.0
            detected_required_count = sum(1 for req_lbl in required_labels if label_counts.get(req_lbl, 0) > 0)
            total_required_count = len(required_labels)

            # NG Detection
            if label_counts.get("ng", 0) > 0:
                with state.lock:
                    state.status = "NG"
                status = "NG"
            
            # Logika Inspeksi Berbasis Confidence & Label Complete
            elif total_required_count > 0:
                detected_ratio = detected_required_count / total_required_count if total_required_count > 0 else 1.0
                labels_complete = (detected_ratio >= target_coverage)
                avg_conf_ok = (current_avg_conf >= target_avg_conf)
                
                # 🐎 ponytail: Update Pesan UI dengan warna merah jika belum menyentuh target
                lbl_color = "#ef4444" if not labels_complete else "#10b981"
                avg_color = "#ef4444" if not avg_conf_ok else "#10b981"
                
                # BGR colors for OpenCV
                lbl_color_bgr = (0, 0, 255) if not labels_complete else (0, 255, 0)
                avg_color_bgr = (0, 0, 255) if not avg_conf_ok else (0, 255, 0)
                
                lbl_html = f"<span style='color:{lbl_color};'>{detected_required_count}/{total_required_count}</span>"
                avg_html = f"<span style='color:{avg_color};'>{current_avg_conf*100:.0f}%/{target_avg_conf*100:.0f}%</span>"
                
                pesan_ui = f"Inspeksi: Labels {lbl_html} (Min {target_coverage*100:.0f}%) | AvgConf: {avg_html}"
                
                if labels_complete and avg_conf_ok and not min_conf_failed:
                    color_status = (0, 255, 0)
                else:
                    color_status = (0, 255, 255)
                    
                # Setup array of text pieces for OpenCV multi-color rendering
                cv2_text_parts = [
                    (f"Inspeksi: Labels ", color_status),
                    (f"{detected_required_count}/{total_required_count}", lbl_color_bgr),
                    (f" (Min {target_coverage*100:.0f}%) | AvgConf: ", color_status),
                    (f"{current_avg_conf*100:.0f}%/{target_avg_conf*100:.0f}%", avg_color_bgr)
                ]

                # Validasi Sukses: Popup muncul otomatis jika semua rule terpenuhi
                if labels_complete and avg_conf_ok and not min_conf_failed:
                    with state.lock:
                        found_labels = []
                        for req_lbl in required_labels:
                            if label_counts.get(req_lbl, 0) > 0:
                                c = label_max_conf.get(req_lbl, 0.0)
                                found_labels.append(f"- {req_lbl.upper()} : {c*100:.0f}%")
                                
                        state.last_inspection_details = {
                            "label_terdeteksi": f"{detected_required_count}/{total_required_count} ({detected_ratio*100:.0f}%)",
                            "avg_confidence": f"{current_avg_conf*100:.0f}% / {target_avg_conf*100:.0f}%",
                            "found_labels": "\n".join(found_labels)
                        }
                        
                        if current_side == "F" and has_rear:
                            # Front OK dan ada sisi Rear → minta operator balik part
                            state.current_side = "R"
                            state.flip_part_popup = True
                            pesan_ui = "Sisi Depan OK! Balik Part ke sisi Belakang."
                            color_status = (0, 255, 165)
                        else:
                            # Front tanpa Rear (single/legacy) ATAU Rear sudah OK → hitung 1 part selesai
                            state.qty -= 1
                            state.current_side = "F"  # reset ke Front untuk part berikutnya
                            state.part_ok_popup = True
                            threading.Thread(target=log_inspeksi_db, args=(state.id_trans, state.p_no, "OK")).start()
                            
                            if state.qty <= 0:
                                threading.Thread(target=kirim_sison.SisonSender.send_callback, args=(state.id_trans, 1)).start()
                                state.status = "STANDBY"
                                pesan_ui = "INSPEKSI SELESAI!"
                                color_status = (0, 255, 0)
                            else:
                                pesan_ui = "Part OK! Lanjut part berikutnya."
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

        # Draw Overlay Text (Left-aligned)
        # Draw Overlay Text (Left-aligned)
        if 'cv2_text_parts' in locals():
            x_offset, y_offset = 20, 50
            for text_part, color_part in cv2_text_parts:
                cv2.putText(frame, text_part, (x_offset, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color_part, 2)
                size, _ = cv2.getTextSize(text_part, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
                x_offset += size[0]
        else:
            pesan_ui_cv2 = re.sub(r'<[^>]+>', '', pesan_ui)
            cv2.putText(frame, pesan_ui_cv2, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color_status, 2)
        
        # 🐎 ponytail: Sisa Qty dan Sisi dipindahkan ke UI PyQt (BASIC_APP.py)
        
        return frame, pesan_ui
