from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QMessageBox
from database import SessionLocal, User, verify_password

def authenticate_and_get_role(username: str, pin: str, allowed_roles: list) -> str:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username, User.is_active == True).first()
        if not user or not verify_password(pin, user.password):
            return None
        if user.role not in allowed_roles:
            return None
        return user.role
    except Exception as e:
        print(f"Auth error: {e}")
        return None
    finally:
        db.close()

class NGValidationDialog(QDialog):
    """Dialog Abnormality Cacat (NG) dengan tampilan foto bukti cacat & validasi PIN Pengawas."""
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NG Terdeteksi!")
        self.setStyleSheet("background-color: #222; color: white; font-size: 24px;")
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 1. Gambar Bukti Cacat
        self.img_label = QLabel(self)
        self.img_label.setPixmap(pixmap.scaled(800, 600, Qt.AspectRatioMode.KeepAspectRatio))
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet("border: 3px solid #ff4444; background-color: black;")
        layout.addWidget(self.img_label)
        
        # 2. Pesan
        msg_label = QLabel("⚠️ KOMPONEN NG TERDETEKSI! ⚠️\nPanggil Pengawas dan masukkan PIN untuk mematikan sirene.", self)
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_label.setStyleSheet("color: #ff4444; font-weight: bold; font-size: 26px;")
        layout.addWidget(msg_label)
        
        # 3. Input Username
        self.username_input = QLineEdit(self)
        self.username_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.username_input.setPlaceholderText("Masukkan Username...")
        self.username_input.setStyleSheet("background-color: white; color: black; font-size: 32px; padding: 10px; border-radius: 8px; margin-bottom: 10px;")
        layout.addWidget(self.username_input)
        
        # 4. Input PIN
        self.pin_input = QLineEdit(self)
        self.pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pin_input.setPlaceholderText("Masukkan PIN (misal: 1234)...")
        self.pin_input.setStyleSheet("background-color: white; color: black; font-size: 32px; padding: 10px; border-radius: 8px;")
        layout.addWidget(self.pin_input)
        
        # 5. Tombol Validasi
        btn_layout = QHBoxLayout()
        self.btn_validasi = QPushButton("VALIDASI PIN", self)
        self.btn_validasi.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_validasi.setStyleSheet("""
            QPushButton {
                background-color: #ff4444; 
                color: white; 
                font-weight: bold; 
                font-size: 28px; 
                padding: 15px; 
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #ff6666;
            }
        """)
        self.btn_validasi.clicked.connect(self.check_pin)
        
        btn_layout.addWidget(self.btn_validasi)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def check_pin(self):
        role = authenticate_and_get_role(self.username_input.text(), self.pin_input.text(), ["pengawas", "admin"])
        if role:
            self.accept()
        else:
            QMessageBox.warning(self, "Ditolak", "Username/PIN Salah atau Anda bukan Pengawas!")
            self.pin_input.clear()
