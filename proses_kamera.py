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

def log_inspeksi_db(id_trans: str, part_no: str, status_deteksi: str, conf_score: float = 1.0, method: str = "AI"):
    """Fungsi helper yang berjalan di background thread untuk mencatat history ke DB"""
    try:
        with SessionLocal() as db:
            # 1. Catat log inspeksi per item
            log = InspectionLog(id_trans=id_trans, part_no=part_no, detection_status=status_deteksi, confidence_score=conf_score, method=method)
            db.add(log)
            
            # 2. Update qty actual di tabel transaksi
            trans = db.query(Transaction).filter(Transaction.id_trans == id_trans).first()
            if trans:
                trans.qty_actual += 1
                if trans.qty_actual >= trans.target_qty:
                    trans.status = 1  # 👱 Ponytail: 1 = SUKSES / OK (sesuai spesifikasi workflow.md)
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
        self.manual_pass_trigger: bool = False
        self.manual_reject_trigger: bool = False
        self.inspection_mode: str = "AI" # "AI" or "MANUAL"
        self.part_ok_popup: bool = False
        self.current_side: str = "F"      # "F" = Front, "R" = Rear
        self.flip_part_popup: bool = False # trigger instruksi "Balik Part" ke operator
        self.last_inspection_details: dict = {} # 🐎 ponytail: Menyimpan detail inspeksi terakhir
        self.completed_time: float = 0.0

    def reset_to_standby(self):
        with self.lock:
            self.status = "STANDBY"
            self.id_trans = ""
            self.p_no = ""
            self.qty = 0
            self.target_qty = 0
            self.aturan_sisi = []
            self.daftar_sisi = []
            self.progress_sisi = 0
            self.current_side = "F"
            self.completed_time = 0.0
            self.manual_pass_trigger = False
            self.manual_reject_trigger = False
            self.mock_detect_trigger = False
            self.inspection_mode = "AI"

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

            # CEK MANUAL PASS / REJECT TRIGGER (Zero-Downtime Industrial Fallback)
            manual_pass = False
            manual_reject = False
            with state.lock:
                if getattr(state, 'manual_pass_trigger', False):
                    manual_pass = True
                    state.manual_pass_trigger = False
                elif getattr(state, 'manual_reject_trigger', False):
                    manual_reject = True
                    state.manual_reject_trigger = False

            if manual_pass:
                with state.lock:
                    state.qty -= 1
                    state.part_ok_popup = True
                    cur_pno = state.p_no
                    cur_id = state.id_trans
                    rem_qty = state.qty
                    state.last_inspection_details = {
                        "label_terdeteksi": "Pemeriksaan Visual Manual",
                        "avg_confidence": "100% (Manual Pass)",
                        "found_labels": "- INSPEKSI VISUAL OPERATOR : OK"
                    }
                
                threading.Thread(target=log_inspeksi_db, args=(cur_id, cur_pno, "OK", 1.0, "MANUAL")).start()
                
                if rem_qty <= 0:
                    with state.lock:
                        state.status = "COMPLETED"
                        state.completed_time = time.time()
                    threading.Thread(target=kirim_sison.SisonSender.send_callback, args=(cur_id, 1)).start()
                    pesan_ui = "INSPEKSI MANUAL SELESAI (OK)!"
                    color_status = (0, 255, 0)
                else:
                    pesan_ui = f"Part Manual OK! Sisa: {rem_qty} PCS"
                    color_status = (0, 255, 0)

            elif manual_reject:
                with state.lock:
                    state.status = "NG"
                    cur_pno = state.p_no
                    cur_id = state.id_trans
                threading.Thread(target=log_inspeksi_db, args=(cur_id, cur_pno, "NG", 0.0, "MANUAL")).start()
                threading.Thread(target=kirim_sison.SisonSender.send_callback, args=(cur_id, 2)).start()
                pesan_ui = "STATUS: NG (MANUAL REJECT)! INPUT PIN UNTUK VALIDASI."
                color_status = (0, 0, 255)

            elif model is not None:
                with state.lock:
                    state.inspection_mode = "AI"
                # 👱 Ponytail: Injeksi conf=0.20 di level Torch/engine untuk memangkas kalkulasi bounding box sampah & mendongkrak FPS
                results = model.track(frame, persist=True, verbose=False, conf=0.20)
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
                with state.lock:
                    state.inspection_mode = "MANUAL"
                pesan_ui = "MODE MANUAL: Model AI Tidak Ditemukan. Tekan [PASS MANUAL] jika part OK."
                color_status = (0, 165, 255)  # Orange

            # Filter rule sesuai sisi aktif
            aturan_aktif = _get_rules_for_side(aturan_sisi, current_side)
            has_rear = any(r.get("nama_komponen", "").lower().startswith("r-") for r in aturan_sisi)

            # CEK MOCK DETECT TRIGGER
            was_mock_triggered = False
            with state.lock:
                if getattr(state, 'mock_detect_trigger', False):
                    was_mock_triggered = True
                    target_rules = aturan_aktif if aturan_aktif else aturan_sisi
                    if target_rules:
                        for req in target_rules:
                            lbl = req.get("nama_komponen", "").lower()
                            label_counts[lbl] = 1
                            label_max_conf[lbl] = 0.95
                            detected_confidences.append(0.95)
                            print(f"[MOCK] Injeksi {lbl} (sisi {current_side}) dengan conf 0.95")
                    else:
                        label_counts["mock_component"] = 1
                        label_max_conf["mock_component"] = 0.95
                        detected_confidences.append(0.95)
                        print(f"[MOCK] Injeksi mock_component dengan conf 0.95")
                    state.mock_detect_trigger = False

            # Tampilan HUD khusus jika Mode Manual aktif tanpa deteksi AI
            if model is None and not was_mock_triggered and not manual_pass and not manual_reject:
                orange_bgr = (0, 165, 255)
                green_bgr = (0, 255, 0)
                white_bgr = (255, 255, 255)
                cv2_text_parts = [
                    ("MODE MANUAL: ", orange_bgr),
                    ("Model AI Belum Ada. ", white_bgr),
                    ("Tekan [PASS MANUAL (OK)]", green_bgr)
                ]

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
                
                # 🐎 ponytail: Warna kuning disamakan persis antara OpenCV BGR (0, 255, 255) dan HTML (#ffff00 / Kuning Cerah Murni)
                yellow_bgr = (0, 255, 255)
                yellow_html = "#ffff00"
                
                lbl_color = "#ef4444" if not labels_complete else "#10b981"
                avg_color = "#ef4444" if not avg_conf_ok else "#10b981"
                
                lbl_color_bgr = (0, 0, 255) if not labels_complete else (0, 255, 0)
                avg_color_bgr = (0, 0, 255) if not avg_conf_ok else (0, 255, 0)
                
                lbl_html = f"<span style='color:{lbl_color};'>{detected_required_count}/{total_required_count}</span>"
                avg_html = f"<span style='color:{avg_color};'>{current_avg_conf*100:.0f}%/{target_avg_conf*100:.0f}%</span>"
                
                pesan_ui = f"<span style='color:{yellow_html};'>Inspeksi: Labels</span> {lbl_html} <span style='color:{yellow_html};'>(Min {target_coverage*100:.0f}%) | AvgConf:</span> {avg_html}"
                color_status = yellow_bgr
                    
                # Setup array of text pieces for OpenCV multi-color rendering
                cv2_text_parts = [
                    (f"Inspeksi: Labels ", yellow_bgr),
                    (f"{detected_required_count}/{total_required_count}", lbl_color_bgr),
                    (f" (Min {target_coverage*100:.0f}%) | AvgConf: ", yellow_bgr),
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
                            threading.Thread(target=log_inspeksi_db, args=(state.id_trans, state.p_no, "OK", current_avg_conf)).start()
                            
                            if state.qty <= 0:
                                state.status = "COMPLETED"
                                state.completed_time = time.time()
                                threading.Thread(target=kirim_sison.SisonSender.send_callback, args=(state.id_trans, 1)).start()
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
                state.completed_time = time.time()
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
        
        # 🐎 ponytail 4: Draw Center Crosshair / Positioning Guide Frame
        fh, fw = frame.shape[:2]
        cx, cy = fw // 2, fh // 2

        # Draw subtle guide crosshair in center
        cv2.line(frame, (cx - 20, cy), (cx + 20, cy), (100, 100, 100), 1)
        cv2.line(frame, (cx, cy - 20), (cx, cy + 20), (100, 100, 100), 1)
        
        # Draw subtle corner brackets (Guide Box) in center area
        bw, bh = int(fw * 0.45), int(fh * 0.45)
        x1, y1 = cx - bw // 2, cy - bh // 2
        x2, y2 = cx + bw // 2, cy + bh // 2
        
        corner_len = 20
        guide_color = (120, 120, 120)
        # Top-left corner
        cv2.line(frame, (x1, y1), (x1 + corner_len, y1), guide_color, 2)
        cv2.line(frame, (x1, y1), (x1, y1 + corner_len), guide_color, 2)
        # Top-right corner
        cv2.line(frame, (x2, y1), (x2 - corner_len, y1), guide_color, 2)
        cv2.line(frame, (x2, y1), (x2, y1 + corner_len), guide_color, 2)
        # Bottom-left corner
        cv2.line(frame, (x1, y2), (x1 + corner_len, y2), guide_color, 2)
        cv2.line(frame, (x1, y2), (x1, y2 - corner_len), guide_color, 2)
        # Bottom-right corner
        cv2.line(frame, (x2, y2), (x2 - corner_len, y2), guide_color, 2)
        cv2.line(frame, (x2, y2), (x2, y2 - corner_len), guide_color, 2)

        # 🐎 ponytail 3: Live Checklist Overlay di pojok kanan atas video frame
        if 'required_labels' in locals() and required_labels:
            checklist_x = fw - 280
            checklist_y = 40
            
            box_height = 25 + len(required_labels) * 22
            cv2.rectangle(frame, (checklist_x - 10, checklist_y - 25), (fw - 15, checklist_y + box_height - 25), (15, 23, 42), -1)
            cv2.rectangle(frame, (checklist_x - 10, checklist_y - 25), (fw - 15, checklist_y + box_height - 25), (0, 255, 255), 1)
            
            cv2.putText(frame, "CHECKLIST LABEL:", (checklist_x, checklist_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
            
            for idx, req_lbl in enumerate(required_labels):
                lbl_y = checklist_y + 15 + (idx * 22)
                has_found = label_counts.get(req_lbl, 0) > 0
                c_score = label_max_conf.get(req_lbl, 0.0)
                
                if has_found:
                    chk_text = f"[OK] {req_lbl.upper()} ({c_score*100:.0f}%)"
                    chk_color = (0, 255, 0) # Green
                else:
                    chk_text = f"[  ] {req_lbl.upper()}"
                    chk_color = (0, 0, 255) # Red
                    
                cv2.putText(frame, chk_text, (checklist_x, lbl_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, chk_color, 1)

        return frame, pesan_ui
