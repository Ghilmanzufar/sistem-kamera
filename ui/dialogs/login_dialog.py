from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton
from database import SessionLocal, User, verify_password

class ShiftLoginDialog(QDialog):
    """
    Dialog Login Operator — muncul di awal aplikasi.
    Jika tombol close (X) ditekan pada login awal, aplikasi akan keluar secara aman.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logged_in_username = ""
        self.logged_in_role = ""
        self.logged_in_fullname = ""
        self.setWindowTitle("Login Operator")
        self.setMinimumWidth(420)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; color: white; font-family: 'Segoe UI'; }
            QLabel { color: #cbd5e1; font-size: 14px; }
            QLineEdit {
                background-color: #1e293b; color: white; border: 1px solid #334155;
                border-radius: 6px; padding: 10px; font-size: 16px;
            }
            QLineEdit:focus { border-color: #3b82f6; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(30, 28, 30, 28)

        title = QLabel("👤 LOGIN OPERATOR")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #3b82f6;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        sub = QLabel("Masukkan Username dan PIN untuk masuk ke sistem")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color: #64748b; font-size: 13px;")
        layout.addWidget(sub)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        layout.addWidget(self.username_input)

        self.pin_input = QLineEdit()
        self.pin_input.setPlaceholderText("PIN / Password")
        self.pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.pin_input)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #f87171; font-size: 12px;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.error_label)

        btn_login = QPushButton("✅  LOGIN")
        btn_login.setFixedHeight(48)
        btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_login.setStyleSheet(
            "background-color: #2563eb; color: white; font-size: 16px; "
            "font-weight: bold; border-radius: 8px;"
        )
        btn_login.clicked.connect(self._do_login)
        layout.addWidget(btn_login)

        self.pin_input.returnPressed.connect(self._do_login)

    def _do_login(self):
        username = self.username_input.text().strip()
        pin = self.pin_input.text().strip()
        if not username or not pin:
            self.error_label.setText("Username dan PIN tidak boleh kosong!")
            return

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == username, User.is_active == True).first()
            if not user or not verify_password(pin, user.password):
                self.error_label.setText("❌ Username atau PIN salah!")
                self.pin_input.clear()
                return
            if user.role not in ["operator", "pengawas", "admin"]:
                self.error_label.setText("❌ Role tidak diizinkan!")
                return
            self.logged_in_username = user.username
            self.logged_in_role = user.role
            self.logged_in_fullname = user.fullname.strip() if getattr(user, 'fullname', None) and user.fullname.strip() else username
            self.accept()
        except Exception as e:
            self.error_label.setText(f"Error: {e}")
        finally:
            db.close()
