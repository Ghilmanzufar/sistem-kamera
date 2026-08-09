import time
import requests
from database import SessionLocal, SisonConfig

def get_callback_url() -> str:
    """Baca URL callback Sison dari DB. Fallback ke default jika error."""
    try:
        with SessionLocal() as db:
            cfg = db.query(SisonConfig).first()
            return cfg.callback_url if cfg and cfg.callback_url else "http://localhost:3000/api/kamera/callback"
    except Exception:
        return "http://localhost:3000/api/kamera/callback"

class SisonSender:
    @staticmethod
    def send_callback(id_trans: str, status: int = 1, max_retries: int = 3, retry_delay: float = 1.0) -> dict:
        """
        Mengirim status hasil inspeksi (1=OK, 2=NG) ke server SISON dengan Auto-Retry hingga 3x
        jika terjadi network glitch / timeout jaringan.
        """
        url = get_callback_url()
        payload = {"id_trans": id_trans, "status": status}
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                res = requests.post(url, json=payload, timeout=2.5)
                if res.status_code in [200, 201, 204]:
                    print(f"[SISON CALLBACK] Sukses terkirim ke {url} (Percobaan ke-{attempt}): {payload} | Status: {res.status_code}")
                    return {"success": True, "attempt": attempt, "status_code": res.status_code}
                else:
                    last_error = f"HTTP Status {res.status_code}: {res.text[:100]}"
                    print(f"[SISON CALLBACK WARN] Percobaan ke-{attempt} gagal dengan kode {res.status_code}. Menunggu {retry_delay}s...")
            except Exception as e:
                last_error = str(e)
                print(f"[SISON CALLBACK WARN] Percobaan ke-{attempt} gagal: {e}. Menunggu {retry_delay}s...")

            if attempt < max_retries:
                time.sleep(retry_delay)

        print(f"[SISON CALLBACK OFFLINE] Gagal setelah {max_retries}x percobaan ke {url}. Data: {payload} | Notice: {last_error}")
        return {"success": False, "attempts": max_retries, "error": last_error}

    @staticmethod
    def test_ping(url: str, timeout: float = 3.0) -> dict:
        """Menguji konektivitas ke server SISON (Test Webhook Endpoint)."""
        test_payload = {"ping": "kamera_inspection", "test": True, "timestamp": int(time.time())}
        start_t = time.time()
        try:
            res = requests.post(url, json=test_payload, timeout=timeout)
            latency_ms = round((time.time() - start_t) * 1000, 1)
            return {
                "success": True,
                "status_code": res.status_code,
                "latency_ms": latency_ms,
                "response": res.text[:200]
            }
        except Exception as e:
            latency_ms = round((time.time() - start_t) * 1000, 1)
            return {
                "success": False,
                "error": str(e),
                "latency_ms": latency_ms
            }
