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
        try:
            url = _get_callback_url()
            payload = {"id_trans": id_trans, "status": status}
            # Timeout diset sangat kecil agar kamera tidak freeze jika Sison offline
            res = requests.post(url, json=payload, timeout=1.0)
            print(f"Berhasil mengirim CALLBACK ke Sison. Status: {res.status_code} | Payload: {payload}")
        except requests.exceptions.RequestException as e:
            print(f"Gagal kirim callback ke Sison (Sison Offline/Error): {e}")
        except Exception as e:
            print(f"Error tidak terduga saat callback: {e}")

