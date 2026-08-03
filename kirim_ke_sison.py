import requests
from database_config import SessionLocal, SisonConfig

def _get_callback_url() -> str:
    """Baca URL callback Sison dari DB. Fallback ke default jika error."""
    try:
        with SessionLocal() as db:
            cfg = db.query(SisonConfig).first()
            return cfg.callback_url if cfg else "http://localhost:3000/api/kamera/callback"
    except Exception:
        return "http://localhost:3000/api/kamera/callback"

class SisonSender:
    @staticmethod
    def send_callback(id_trans: str, status: int = 1):
        # ponytail: Callback ke Sison API dinonaktifkan sementara untuk pengujian lokal.
        # Ceiling: Hapus return di bawah ini untuk mengaktifkan kembali integrasi Sison.
        print(f"[MOCK SISON] Callback Sison dinonaktifkan sementara. (id_trans: {id_trans})")
        return

