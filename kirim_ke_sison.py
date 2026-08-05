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
        # 👱 Ponytail: Coba kirim callback HTTP ke Sison, jatuh ke logging jika server Sison belum aktif/mocked.
        url = _get_callback_url()
        payload = {"id_trans": id_trans, "status": status}
        try:
            res = requests.post(url, json=payload, timeout=2.0)
            print(f"[SISON CALLBACK] Berhasil terkirim ke {url}: {payload} | Status: {res.status_code}")
        except Exception as e:
            print(f"[MOCK SISON / OFFLINE] Gagal kirim ke {url}, mode lokal aktif. Data: {payload} | Notice: {e}")

