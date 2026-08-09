import sys
import os
import time
import threading
import webbrowser
import cv2

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QMessageBox, QDialog, QFrame, QSizePolicy
)
from PyQt6.QtGui import QImage, QPixmap

from database import SessionLocal, CameraConfig
from core import state, KameraProses, create_capture_device, log_inspeksi_db, log_ng_db
from api import run_fastapi, create_admin_token
from integrations import SisonSender, start_buffer_sync_worker
from ui.dialogs import ShiftLoginDialog, NGValidationDialog, show_demo_sison_dialog

def cleanup_old_ng_records(days: int = 30):
    """Otomatis hapus file foto NG yang berumur > 30 hari untuk menghemat ruang harddisk."""
    folder = "ng_records"
    if not os.path.exists(folder):
        return
    now = time.time()
    cutoff = now - (days * 86400)
    deleted_count = 0
    try:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path) and filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                if os.path.getmtime(file_path) < cutoff:
                    os.remove(file_path)
                    deleted_count += 1
        if deleted_count > 0:
            print(f"[CLEANUP] Otomatis menghapus {deleted_count} foto NG lama (> {days} hari).")
    except Exception as e:
        print(f"[CLEANUP WARN] Gagal menjalankan pembersihan foto NG: {e}")

def start_periodic_cleanup():
    def loop():
        while True:
            cleanup_old_ng_records(days=30)
            time.sleep(86400)  # Cek setiap 24 jam
    t = threading.Thread(target=loop, daemon=True)
    t.start()

class YoloApp(QWidget):
    """Main Desktop Window untuk Operator & Live Video Stream Inspeksi."""
    def __init__(self):
        super().__init__()
        
        # Baca konfigurasi sumber kamera dari database
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
            print(f"[SYSTEM] Menggunakan sumber kamera dari DB: {cam_source}")
        except Exception as e:
            print(f"[WARNING] Gagal membaca DB, fallback ke index 0. Error: {e}")
            cam_source = 0

        self.is_cam_active = (active_cam is not None)
        self.cam_source = cam_source
        self.last_cam_check_time = 0.0
        self.is_reconnecting = False
        self.reconnect_attempts = 0
        
        if self.is_cam_active:
            self._open_camera()
        else:
            self.cap = cv2.VideoCapture()
        
        self.model = None
        self.current_loaded_p_no = ""
        self.last_model_mtime = 0.0
        self.ng_popup_active = False

        # 1. Wajib Login Operator sebelum layar kamera aktif
        self._run_shift_login()

        # 2. Inisialisasi UI & Timers
        self.initUI()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # 30 FPS
        
        # 3. Start FastAPI, Auto Cleanup, & Offline Buffer Sync Worker
        self.api_thread = threading.Thread(target=run_fastapi, daemon=True)
        self.api_thread.start()
        start_periodic_cleanup()
        start_buffer_sync_worker()

    def _open_camera(self):
        self.cap = create_capture_device(self.cam_source)

    def _attempt_reconnect_async(self):
        """Thread background watchdog untuk reconnect kamera tanpa membekukan UI."""
        if self.is_reconnecting or not self.is_cam_active:
            return
        self.is_reconnecting = True
        self.reconnect_attempts += 1

        def worker():
            try:
                try:
                    if self.cap and self.cap.isOpened():
                        self.cap.release()
                except Exception:
                    pass

                time.sleep(1.0)
                new_cap = create_capture_device(self.cam_source)
                if new_cap.isOpened():
                    ret, test_frame = new_cap.read()
                    if ret and test_frame is not None:
                        self.cap = new_cap
                        self.reconnect_attempts = 0
                        print(f"[CAMERA WATCHDOG] ✅ Kamera ({self.cam_source}) berhasil terhubung kembali!")
                    else:
                        new_cap.release()
            except Exception as e:
                print(f"[CAMERA WATCHDOG WARN] Percobaan reconnect ke-{self.reconnect_attempts} gagal: {e}")
            finally:
                self.is_reconnecting = False

        t = threading.Thread(target=worker, daemon=True)
        t.start()

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
        self.hud_frame.setFixedHeight(115)
        hud_layout = QHBoxLayout(self.hud_frame)
        hud_layout.setContentsMargins(20, 8, 20, 8)

        self.part_name = QLabel("<span style='color:#ffff00; font-size:14px; font-weight:bold;'>PART NUMBER</span><br/><span style='color:#f8fafc; font-size:24px; font-weight:bold;'>MENUNGGU SISON...</span>", self)
        self.part_name.setStyleSheet("border: none; background: transparent;")
        self.part_name.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        status_container = QWidget(self)
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(0,0,0,0)
        status_layout.setSpacing(0)
        
        self.status_label = QLabel("<span style='color:#94a3b8; font-size:13px;'>STATUS KAMERA</span><br/><span style='color:#cbd5e1; font-size:22px; font-weight:bold;'>STANDBY</span>", self)
        self.status_label.setStyleSheet("border: none; background: transparent;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.info_label = QLabel("<span style='color:#cbd5e1; font-size:13px; font-weight:bold;'>QTY: - | SISI: -</span>", self)
        self.info_label.setStyleSheet("border: none; background: transparent;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.info_label)
        
        self.btn_admin = QPushButton("⚙️ DASHBOARD", self)
        self.btn_admin.setFixedHeight(40)
        self.btn_admin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_admin.setStyleSheet("background-color: #2563eb; color: white; font-size:14px; font-weight:bold; border-radius: 5px; padding: 0 14px;")
        self.btn_admin.clicked.connect(self.prompt_admin_dashboard)

        self.operator_badge = QLabel("", self)
        self.operator_badge.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: bold; border: none; background: transparent;")
        self.operator_badge.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._update_operator_badge()

        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        right_layout.addWidget(self.operator_badge, alignment=Qt.AlignmentFlag.AlignRight)
        right_layout.addWidget(self.btn_admin, alignment=Qt.AlignmentFlag.AlignRight)

        hud_layout.addWidget(self.part_name, stretch=1)
        hud_layout.addWidget(status_container, stretch=1)
        hud_layout.addWidget(right_container, stretch=1)

        self.btn_pass_manual = QPushButton("✅ PASS MANUAL (OK)", self)
        self.btn_pass_manual.setFixedHeight(38)
        self.btn_pass_manual.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pass_manual.setStyleSheet("background-color: #059669; color: white; font-size:14px; font-weight:bold; border-radius: 6px; padding: 0 14px;")
        self.btn_pass_manual.clicked.connect(self.trigger_manual_pass)
        self.btn_pass_manual.setVisible(False)

        self.btn_reject_manual = QPushButton("❌ REJECT (NG)", self)
        self.btn_reject_manual.setFixedHeight(38)
        self.btn_reject_manual.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reject_manual.setStyleSheet("background-color: #dc2626; color: white; font-size:14px; font-weight:bold; border-radius: 6px; padding: 0 14px;")
        self.btn_reject_manual.clicked.connect(self.trigger_manual_reject)
        self.btn_reject_manual.setVisible(False)

        self.btn_demo = QPushButton("🚀 DEMO SISON", self)
        self.btn_demo.setFixedHeight(38)
        self.btn_demo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_demo.setStyleSheet("background-color: #475569; color: white; font-size:14px; font-weight:bold; border-radius: 6px; padding: 0 10px;")
        self.btn_demo.clicked.connect(self.prompt_demo_sison)

        self.btn_mock = QPushButton("📷 MOCK DETECT", self)
        self.btn_mock.setFixedHeight(38)
        self.btn_mock.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mock.setStyleSheet("background-color: #334155; color: #94a3b8; font-size:13px; font-weight:bold; border-radius: 6px; padding: 0 10px;")
        self.btn_mock.clicked.connect(self.trigger_mock_detect)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.addWidget(self.btn_pass_manual)
        toolbar_layout.addWidget(self.btn_reject_manual)
        toolbar_layout.addWidget(self.btn_demo)
        toolbar_layout.addWidget(self.btn_mock)
        toolbar_layout.addStretch()

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        layout.addWidget(self.hud_frame)
        layout.addLayout(toolbar_layout)
        layout.addWidget(self.video_label)
        self.setLayout(layout)

    def prompt_demo_sison(self):
        show_demo_sison_dialog(self)

    def prompt_admin_dashboard(self):
        with state.lock:
            uname = state.operator_username or "op"
            urole = state.operator_role or "operator"
        token = create_admin_token(username=uname, role=urole, expires_in_seconds=86400)
        webbrowser.open(f"http://localhost:8000/admin/?sso={token}&u={uname}&r={urole}")

    def _run_shift_login(self):
        dialog = ShiftLoginDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            with state.lock:
                state.operator_name = dialog.logged_in_fullname
                state.operator_username = dialog.logged_in_username
                state.operator_role = dialog.logged_in_role
                state.operator_login_time = time.time()
            print(f"[LOGIN] ✅ Operator login: {dialog.logged_in_fullname} (User: {dialog.logged_in_username}, Role: {dialog.logged_in_role})")
        else:
            print("[SYSTEM] Login dibatalkan oleh pengguna. Menutup aplikasi...")
            if hasattr(self, 'cap') and self.cap and self.cap.isOpened():
                self.cap.release()
            sys.exit(0)

    def _update_operator_badge(self):
        if not hasattr(self, 'operator_badge'):
            return
        with state.lock:
            name = state.operator_name
            login_ts = state.operator_login_time
        if name and login_ts:
            import datetime as dt
            waktu_str = dt.datetime.fromtimestamp(login_ts).strftime("%H:%M")
            self.operator_badge.setText(f"👤 {name}  |  🕒 {waktu_str}")
        else:
            self.operator_badge.setText("")

    def trigger_manual_pass(self):
        with state.lock:
            curr_status = state.status
        if curr_status not in ["RUNNING", "OK"]:
            QMessageBox.information(self, "Info", "Sistem dalam posisi STANDBY.\nTidak ada transaksi aktif yang dapat divalidasi secara manual.")
            return
        with state.lock:
            state.manual_pass_trigger = True

    def trigger_manual_reject(self):
        with state.lock:
            curr_status = state.status
        if curr_status not in ["RUNNING", "OK"]:
            QMessageBox.information(self, "Info", "Sistem dalam posisi STANDBY.\nTidak ada transaksi aktif yang dapat di-reject.")
            return
        with state.lock:
            state.manual_reject_trigger = True

    def trigger_mock_detect(self):
        with state.lock:
            curr_status = state.status
        if curr_status not in ["RUNNING", "OK"]:
            QMessageBox.information(self, "Info", "Sistem dalam posisi STANDBY.\nSilakan klik '🚀 DEMO SISON' terlebih dahulu untuk memulai simulasi transaksi!")
            return
        with state.lock:
            state.mock_detect_trigger = True

    def update_frame(self):
        with state.lock:
            p_no = state.p_no
            target_qty = state.target_qty
            sisa_qty = state.qty
            current_status = state.status
            inspection_mode = getattr(state, 'inspection_mode', 'AI')

        qty_selesai = target_qty - sisa_qty
        
        if p_no:
            self.part_name.setText(f"<span style='color:#ffff00; font-size:28px; font-weight:bold;'>{p_no}</span><br/><span style='color:#22c55e; font-size:18px; font-weight:bold;'>Target: {target_qty} PCS | Selesai: {qty_selesai} PCS</span>")
        else:
            self.part_name.setText("<span style='color:#ffff00; font-size:16px; font-weight:bold;'>PART NUMBER</span><br/><span style='color:#f8fafc; font-size:28px; font-weight:bold;'>MENUNGGU SISON...</span>")

        status_color = "#cbd5e1"
        status_text = "STANDBY"
        
        is_running = current_status in ["OK", "RUNNING"]
        is_manual_mode = is_running and (inspection_mode == "MANUAL" or self.model is None)

        self.btn_pass_manual.setVisible(is_manual_mode)
        self.btn_reject_manual.setVisible(is_manual_mode)
        self.btn_pass_manual.setEnabled(is_manual_mode)
        self.btn_reject_manual.setEnabled(is_manual_mode)

        if is_running:
            if is_manual_mode:
                status_color = "#f59e0b"
                status_text = "MODE MANUAL (VISUAL)"
            else:
                status_color = "#22c55e"
                status_text = "INSPEKSI AI AKTIF" if current_status == "OK" else "PROSES (AI AUTO)"
            self.hud_frame.setStyleSheet("#hud { background-color: #0f172a; border: none; border-radius: 10px; }")
        elif current_status == "COMPLETED":
            status_color = "#38bdf8"
            status_text = "SELESAI (OK)"
            self.hud_frame.setStyleSheet("#hud { background-color: #0f172a; border: none; border-radius: 10px; }")
            if state.completed_time > 0 and (time.time() - state.completed_time) >= 5.0:
                state.reset_to_standby()
        elif current_status == "NG":
            status_color = "#ef4444"
            status_text = "NG TERDETEKSI"
            blink = "red" if int(time.time() * 2) % 2 == 0 else "transparent"
            self.hud_frame.setStyleSheet(f"#hud {{ background-color: #0f172a; border: 4px solid {blink}; border-radius: 10px; }}")
        else:
            self.hud_frame.setStyleSheet("#hud { background-color: #0f172a; border: none; border-radius: 10px; }")
            
        self.status_label.setText(f"<span style='color:#94a3b8; font-size:13px;'>STATUS KAMERA</span><br/><span style='color:{status_color}; font-size:22px; font-weight:bold;'>{status_text}</span>")

        # Lazy & Hot-reload model
        model_path = os.path.join(os.getcwd(), "weights", f"{p_no}.pt")
        curr_mtime = os.path.getmtime(model_path) if os.path.exists(model_path) else 0.0
        if p_no != "" and (p_no != self.current_loaded_p_no or curr_mtime > getattr(self, 'last_model_mtime', 0.0)):
            self.model = KameraProses.load_model(p_no)
            self.current_loaded_p_no = p_no
            self.last_model_mtime = curr_mtime

        # Dynamic Camera Switch & Toggle Sync dari Database
        now_ts = time.time()
        if now_ts - self.last_cam_check_time >= 1.0:
            self.last_cam_check_time = now_ts
            try:
                db_cam_session = SessionLocal()
                active_cam = db_cam_session.query(CameraConfig).filter(CameraConfig.is_active == True).first()
                if active_cam:
                    new_src = active_cam.source
                    if isinstance(new_src, str) and new_src.isdigit():
                        new_src = int(new_src)
                    if not self.is_cam_active or self.cam_source != new_src or not self.cap.isOpened():
                        self.is_cam_active = True
                        self.cam_source = new_src
                        if self.cap.isOpened():
                            self.cap.release()
                        self._open_camera()
                        print(f"[SYSTEM] Saklar Kamera Aktif: {active_cam.name} (Source: {new_src})")
                else:
                    if self.is_cam_active:
                        self.is_cam_active = False
                        if self.cap.isOpened():
                            self.cap.release()
                        print("[SYSTEM] Saklar Kamera Standby (OFF): Video feed dihentikan.")
                db_cam_session.close()
            except Exception:
                pass

        if not self.is_cam_active:
            self.video_label.setText("<span style='color:#94a3b8; font-size:24px; font-weight:bold;'>⏸️ KAMERA STANDBY (OFF)<br/><span style='color:#64748b; font-size:15px; font-weight:normal;'>Kamera dimatikan dari Admin Dashboard.<br/>Nyalakan saklar kamera untuk melanjutkan live video stream.</span></span>")
            return

        try:
            ret, frame = self.cap.read() if (self.cap and self.cap.isOpened()) else (False, None)
        except Exception:
            ret, frame = False, None

        if not ret or frame is None:
            attempt_text = f" (Mencoba Reconnect ke-{self.reconnect_attempts}...)" if self.reconnect_attempts > 0 else ""
            self.video_label.setText(
                f"<span style='color:#ef4444; font-size:24px; font-weight:bold;'>⚠️ KAMERA GAGAL DIAKSES / TERPUTUS{attempt_text}</span><br/>"
                f"<span style='color:#f87171; font-size:15px; font-weight:normal;'>Mencoba menyambungkan kembali ke sumber [{self.cam_source}]...<br/>"
                f"Periksa kabel USB kamera atau setting sumber kamera di Admin Dashboard.</span>"
            )
            self._attempt_reconnect_async()
            return
        
        frame, pesan_ui = KameraProses.proses_frame(frame, self.model)
        self.status_label.setText(f"<span style='color:#94a3b8; font-size:13px;'>STATUS KAMERA</span><br/><span style='color:{status_color}; font-size:18px; font-weight:bold;'>{pesan_ui}</span>")
        
        if p_no and current_status != "STANDBY":
            side_text = "FRONT" if state.current_side == "F" else "REAR"
            self.info_label.setText(f"<span style='color:#10b981; font-size:13px; font-weight:bold;'>SISA QTY: {sisa_qty}/{target_qty}  |  SISI: {side_text}</span>")
        else:
            self.info_label.setText("<span style='color:#cbd5e1; font-size:13px; font-weight:bold;'>QTY: - | SISI: -</span>")
            
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap(qt_image).scaled(self.video_label.width(), self.video_label.height(), Qt.AspectRatioMode.KeepAspectRatio)
        self.video_label.setPixmap(pixmap)

        # Popup Part OK & Balik Sisi
        should_popup_ok = False
        should_popup_flip = False
        with state.lock:
            if getattr(state, 'part_ok_popup', False):
                state.part_ok_popup = False
                should_popup_ok = True
            if getattr(state, 'flip_part_popup', False):
                state.flip_part_popup = False
                should_popup_flip = True

        if should_popup_flip or should_popup_ok:
            details = state.last_inspection_details
            lbl_terdeteksi = details.get("label_terdeteksi", "-")
            avg_conf = details.get("avg_confidence", "-")
            found_labels = details.get("found_labels", "-")
            found_labels_html = found_labels.replace('\n', '<br>')
            
            if should_popup_flip:
                title = "BALIK PART"
                header_msg = "🔄 SISI DEPAN OK!"
                sub_msg = "Balik Part ke SISI BELAKANG."
            else:
                title = "INSPEKSI OK"
                header_msg = "✅ PART BERHASIL TERDETEKSI!"
                sub_msg = "Semua label terdeteksi dan memenuhi standar confidence."
                
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(title)
            msg_box.setIcon(QMessageBox.Icon.Information)
            
            html_text = f"""
            <h3 style='margin-bottom: 5px;'>{header_msg}</h3>
            <p style='color: #ffffff; font-size: 15px; font-weight: bold;'>{sub_msg}</p>
            <hr>
            <table cellpadding='4'>
                <tr>
                    <td><b>Label Terdeteksi</b></td>
                    <td>: {lbl_terdeteksi}</td>
                </tr>
                <tr>
                    <td><b>Rata-rata Confidence</b></td>
                    <td>: {avg_conf}</td>
                </tr>
            </table>
            <br>
            <b>Label yang ditemukan:</b><br>
            <div style='font-family: monospace; color: #10b981; margin-top: 5px;'>
                {found_labels_html}
            </div>
            """
            msg_box.setText(html_text)
            msg_box.exec()

        # Tangani Abnormality NG Popup
        with state.lock:
            status_kamera = state.status

        if status_kamera == "NG" and not self.ng_popup_active:
            self.ng_popup_active = True
            print("\n[HARDWARE] SIRENE ABNORMAL ON!")
            
            self.last_ng_pixmap = pixmap
            os.makedirs("ng_records", exist_ok=True)
            timestamp = int(time.time())
            filename = f"ng_records/NG_{state.id_trans}_{timestamp}.jpg"
            cv2.imwrite(filename, frame)
            print(f"[SYSTEM] Gambar cacat disimpan di: {filename}")
            
            threading.Thread(target=log_ng_db, args=(state.id_trans, state.p_no, filename, state.operator_name)).start()
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
            self.show_ng_popup()

    def closeEvent(self, event):
        with state.lock:
            current_status = state.status
            
        if current_status not in ["STANDBY", "COMPLETED"]:
            QMessageBox.warning(self, "Peringatan", f"Aplikasi sedang berjalan (Status: {current_status})!\nSelesaikan inspeksi terlebih dahulu sebelum menutup aplikasi.")
            event.ignore()
            return
            
        self.cap.release()
        print("Program closed.")
        event.accept()
