import os
import re
import time
import threading
from collections import OrderedDict
import cv2
from ultralytics import YOLO

from database import SessionLocal, Transaction, InspectionLog
from integrations import SisonSender, save_to_offline_buffer
from sqlalchemy.sql import func

from .state import state
from .rules import get_rules_for_side, calculate_inspection_metrics

def log_inspeksi_db(id_trans: str, part_no: str, status_deteksi: str, conf_score: float = 1.0, method: str = "AI", operator_name: str = ""):
    """Mencatat riwayat log inspeksi ke PostgreSQL dengan fallback ke offline buffer jika database down."""
    try:
        with SessionLocal() as db:
            log = InspectionLog(
                id_trans=id_trans,
                part_no=part_no,
                detection_status=status_deteksi,
                confidence_score=conf_score,
                method=method,
                operator_name=operator_name or None
            )
            db.add(log)
            
            trans = db.query(Transaction).filter(Transaction.id_trans == id_trans).first()
            if trans:
                trans.qty_actual += 1
                if trans.qty_actual >= trans.target_qty:
                    trans.status = 1
                    trans.end_time = func.now()
            
            db.commit()
    except Exception as e:
        print(f"[DB WARN] Gagal mencatat log inspeksi ke PostgreSQL ({e}). Mengalihkan ke Offline Buffer...")
        save_to_offline_buffer("INSPECTION_LOG", {
            "id_trans": id_trans,
            "part_no": part_no,
            "detection_status": status_deteksi,
            "confidence_score": conf_score,
            "method": method,
            "operator_name": operator_name
        })

def log_ng_db(id_trans: str, part_no: str, image_path: str, operator_name: str = ""):
    """Mencatat riwayat part cacat (NG) beserta file snapshot ke DB/Buffer."""
    try:
        with SessionLocal() as db:
            log = InspectionLog(
                id_trans=id_trans,
                part_no=part_no,
                detection_status="NG",
                image_path=image_path,
                confidence_score=1.0,
                operator_name=operator_name or None
            )
            db.add(log)
            db.commit()
    except Exception as e:
        print(f"[DB WARN] Gagal mencatat log NG ke PostgreSQL ({e}). Mengalihkan ke Offline Buffer...")
        save_to_offline_buffer("NG_LOG", {
            "id_trans": id_trans,
            "part_no": part_no,
            "image_path": image_path,
            "operator_name": operator_name
        })

class ModelCache:
    """In-Memory LRU Model Cache dengan hot-reload otomatis jika file bobot .pt/.onnx diupdate."""
    def __init__(self, max_models: int = 5):
        self.max_models = max_models
        self._cache = OrderedDict()
        self._lock = threading.Lock()

    def get(self, p_no: str):
        if not p_no:
            return None

        weights_dir = os.path.join(os.getcwd(), "weights")
        if not os.path.exists(weights_dir):
            os.makedirs(weights_dir)

        onnx_path = os.path.join(weights_dir, f"{p_no}.onnx")
        pt_path = os.path.join(weights_dir, f"{p_no}.pt")

        if os.path.exists(onnx_path):
            model_path = onnx_path
            fmt_type = "ONNX"
        elif os.path.exists(pt_path):
            model_path = pt_path
            fmt_type = "PyTorch PT"
        else:
            default_onnx = os.path.join(weights_dir, "yolov8n.onnx")
            default_pt = os.path.join(weights_dir, "yolov8n.pt")
            if os.path.exists(default_onnx):
                model_path = default_onnx
                fmt_type = "ONNX Default"
            elif os.path.exists(default_pt):
                model_path = default_pt
                fmt_type = "PyTorch Default"
            else:
                return None

        try:
            mtime = os.path.getmtime(model_path)
        except OSError:
            mtime = 0.0

        cache_key = (p_no, mtime, model_path)

        with self._lock:
            if cache_key in self._cache:
                self._cache.move_to_end(cache_key)
                return self._cache[cache_key]

            keys_to_remove = [k for k in self._cache if k[0] == p_no]
            for k in keys_to_remove:
                del self._cache[k]

            print(f"[MODEL CACHE] 🧠 Memuat model format {fmt_type}: {model_path} (Part: {p_no})")
            try:
                model = YOLO(model_path, task="detect", verbose=False)
                self._cache[cache_key] = model
                self._cache.move_to_end(cache_key)

                if len(self._cache) > self.max_models:
                    evicted_key, _ = self._cache.popitem(last=False)
                    print(f"[MODEL CACHE] 🗑️ Mengosongkan model lama dari RAM: {evicted_key[0]}")
                    try:
                        import gc
                        gc.collect()
                        import torch
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                    except Exception:
                        pass

                return model
            except Exception as e:
                print(f"[MODEL CACHE ERROR] Gagal memuat model {model_path}: {e}")
                return None

    def clear(self):
        with self._lock:
            self._cache.clear()

model_cache = ModelCache(max_models=5)

class KameraProses:
    @staticmethod
    def load_model(p_no: str):
        return model_cache.get(p_no)

    @staticmethod
    def proses_frame(frame, model):
        with state.lock:
            status = state.status
            qty = state.qty
            target_qty = state.target_qty
            aturan_sisi = state.aturan_sisi
            current_side = state.current_side
            
        pesan_ui = f"Status: {status}"
        color_status = (255, 255, 0)

        if status == "RUNNING" and qty > 0:
            label_counts = {}
            label_max_conf = {}
            detected_confidences = []
            min_conf_failed = False

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
                
                threading.Thread(target=log_inspeksi_db, args=(cur_id, cur_pno, "OK", 1.0, "MANUAL", state.operator_name)).start()
                
                if rem_qty <= 0:
                    with state.lock:
                        state.status = "COMPLETED"
                        state.completed_time = time.time()
                    threading.Thread(target=SisonSender.send_callback, args=(cur_id, 1)).start()
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
                threading.Thread(target=log_inspeksi_db, args=(cur_id, cur_pno, "NG", 0.0, "MANUAL", state.operator_name)).start()
                threading.Thread(target=SisonSender.send_callback, args=(cur_id, 2)).start()
                pesan_ui = "STATUS: NG (MANUAL REJECT)! INPUT PIN UNTUK VALIDASI."
                color_status = (0, 0, 255)

            elif model is not None:
                with state.lock:
                    state.inspection_mode = "AI"
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
                            
                            req = next((r for r in aturan_sisi if r.get("nama_komponen", "").lower() == label_name), None)
                            min_conf = req.get("min_confidence", 0.70) if req else 0.70
                            
                            if conf >= min_conf:
                                box_color = (0, 255, 0)
                            else:
                                box_color = (0, 0, 255)
                                min_conf_failed = True

                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
                            text = f"{label_name.upper()} ({conf*100:.0f}%)"
                            cv2.putText(frame, text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)
            else:
                with state.lock:
                    state.inspection_mode = "MANUAL"
                pesan_ui = "MODE MANUAL: Model AI Tidak Ditemukan. Tekan [PASS MANUAL] jika part OK."
                color_status = (0, 165, 255)

            aturan_aktif = get_rules_for_side(aturan_sisi, current_side)
            has_rear = any(r.get("nama_komponen", "").lower().startswith("r-") for r in aturan_sisi)

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
                    else:
                        label_counts["mock_component"] = 1
                        label_max_conf["mock_component"] = 0.95
                        detected_confidences.append(0.95)
                    state.mock_detect_trigger = False

            metrics = calculate_inspection_metrics(aturan_aktif, label_counts, detected_confidences)
            required_labels = metrics["required_labels"]
            target_avg_conf = metrics["target_avg_conf"]
            target_coverage = metrics["target_coverage"]
            current_avg_conf = metrics["current_avg_conf"]
            detected_required_count = metrics["detected_required_count"]
            total_required_count = metrics["total_required_count"]
            detected_ratio = metrics["detected_ratio"]
            labels_complete = metrics["labels_complete"]
            avg_conf_ok = metrics["avg_conf_ok"]

            if label_counts.get("ng", 0) > 0:
                with state.lock:
                    state.status = "NG"
                status = "NG"
            elif total_required_count > 0:
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
                    
                cv2_text_parts = [
                    (f"Inspeksi: Labels ", yellow_bgr),
                    (f"{detected_required_count}/{total_required_count}", lbl_color_bgr),
                    (f" (Min {target_coverage*100:.0f}%) | AvgConf: ", yellow_bgr),
                    (f"{current_avg_conf*100:.0f}%/{target_avg_conf*100:.0f}%", avg_color_bgr)
                ]

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
                            state.current_side = "R"
                            state.flip_part_popup = True
                            pesan_ui = "Sisi Depan OK! Balik Part ke sisi Belakang."
                            color_status = (0, 255, 165)
                        else:
                            state.qty -= 1
                            state.current_side = "F"
                            state.part_ok_popup = True
                            threading.Thread(target=log_inspeksi_db, args=(state.id_trans, state.p_no, "OK", current_avg_conf, "AI", state.operator_name)).start()
                            
                            if state.qty <= 0:
                                state.status = "COMPLETED"
                                state.completed_time = time.time()
                                threading.Thread(target=SisonSender.send_callback, args=(state.id_trans, 1)).start()
                                pesan_ui = "INSPEKSI SELESAI!"
                                color_status = (0, 255, 0)
                            else:
                                pesan_ui = "Part OK! Lanjut part berikutnya."
                                color_status = (0, 255, 0)

            elif was_mock_triggered:
                with state.lock:
                    state.qty -= 1
                    state.current_side = "F"
                    state.part_ok_popup = True
                    cur_pno = state.p_no
                    cur_id = state.id_trans
                    rem_qty = state.qty
                    state.last_inspection_details = {
                        "label_terdeteksi": "Simulasi Mock Detect",
                        "avg_confidence": "95%",
                        "found_labels": "- MOCK COMPONENT : 95%"
                    }
                threading.Thread(target=log_inspeksi_db, args=(cur_id, cur_pno, "OK", 0.95, "AI", state.operator_name)).start()
                if rem_qty <= 0:
                    with state.lock:
                        state.status = "COMPLETED"
                        state.completed_time = time.time()
                    threading.Thread(target=SisonSender.send_callback, args=(cur_id, 1)).start()
                    pesan_ui = "INSPEKSI SELESAI!"
                    color_status = (0, 255, 0)
                else:
                    pesan_ui = "Part Mock OK! Lanjut part berikutnya."
                    color_status = (0, 255, 0)

        elif status == "NG":
            pesan_ui = "STATUS: NG! INPUT PIN UNTUK VALIDASI."
            color_status = (0, 0, 255)
            overlay = frame.copy()
            cv2.rectangle(overlay, (0,0), (frame.shape[1], frame.shape[0]), (0,0,255), -1)
            cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
            
        elif status == "RUNNING" and qty <= 0 and target_qty > 0:
            with state.lock:
                state.status = "COMPLETED"
                state.completed_time = time.time()
            status = "COMPLETED"
            SisonSender.send_callback(state.id_trans, 1)
            pesan_ui = "INSPEKSI SELESAI. MENGHUBUNGI SISON..."
            color_status = (0, 255, 0)
            
        elif status == "COMPLETED":
            pesan_ui = "SELESAI. TUNGGU INSTRUKSI SISON."
            color_status = (0, 255, 0)

        # Render overlay teks
        if 'cv2_text_parts' in locals():
            x_offset, y_offset = 20, 50
            for text_part, color_part in cv2_text_parts:
                cv2.putText(frame, text_part, (x_offset, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color_part, 2)
                size, _ = cv2.getTextSize(text_part, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
                x_offset += size[0]
        else:
            pesan_ui_cv2 = re.sub(r'<[^>]+>', '', pesan_ui)
            cv2.putText(frame, pesan_ui_cv2, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color_status, 2)
        
        # Center crosshair guide
        fh, fw = frame.shape[:2]
        cx, cy = fw // 2, fh // 2
        cv2.line(frame, (cx - 20, cy), (cx + 20, cy), (100, 100, 100), 1)
        cv2.line(frame, (cx, cy - 20), (cx, cy + 20), (100, 100, 100), 1)
        
        bw, bh = int(fw * 0.45), int(fh * 0.45)
        x1, y1 = cx - bw // 2, cy - bh // 2
        x2, y2 = cx + bw // 2, cy + bh // 2
        corner_len = 20
        guide_color = (120, 120, 120)
        cv2.line(frame, (x1, y1), (x1 + corner_len, y1), guide_color, 2)
        cv2.line(frame, (x1, y1), (x1, y1 + corner_len), guide_color, 2)
        cv2.line(frame, (x2, y1), (x2 - corner_len, y1), guide_color, 2)
        cv2.line(frame, (x2, y1), (x2, y1 + corner_len), guide_color, 2)
        cv2.line(frame, (x1, y2), (x1 + corner_len, y2), guide_color, 2)
        cv2.line(frame, (x1, y2), (x1, y2 - corner_len), guide_color, 2)
        cv2.line(frame, (x2, y2), (x2 - corner_len, y2), guide_color, 2)
        cv2.line(frame, (x2, y2), (x2, y2 - corner_len), guide_color, 2)

        # Live Checklist Overlay pojok kanan atas
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
                    chk_color = (0, 255, 0)
                else:
                    chk_text = f"[  ] {req_lbl.upper()}"
                    chk_color = (0, 0, 255)
                cv2.putText(frame, chk_text, (checklist_x, lbl_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, chk_color, 1)

        return frame, pesan_ui
