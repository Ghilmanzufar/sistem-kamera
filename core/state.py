import threading

class SystemState:
    """Thread-safe singleton state untuk sinkronisasi data antar thread & modul."""
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
        self.inspection_mode: str = "AI"  # "AI" or "MANUAL"
        self.part_ok_popup: bool = False
        self.current_side: str = "F"      # "F" = Front, "R" = Rear
        self.flip_part_popup: bool = False
        self.last_inspection_details: dict = {}
        self.completed_time: float = 0.0
        self.operator_name: str = ""       # Nama lengkap operator
        self.operator_username: str = ""   # Username operator (untuk SSO Dashboard)
        self.operator_role: str = ""       # Role operator (operator/pengawas/admin)
        self.operator_login_time: float = 0.0

    def reset_to_standby(self):
        """Mereset status mesin ke STANDBY untuk menyambut transaksi SISON berikutnya."""
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
