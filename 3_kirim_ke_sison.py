import requests

class SisonSender:
    @staticmethod
    def send_callback(id_trans: str, status: int = 1):
        try:
            # URL callback ini sesuaikan dengan konfigurasi Sison Anda
            url = "http://localhost:3000/api/kamera/callback"
            payload = {"id_trans": id_trans, "status": status}
            # Sengaja dikomen sementara saat dev agar tidak error connection refused
            # requests.post(url, json=payload, timeout=2) 
            print(f"Berhasil mengirim CALLBACK ke Sison: {payload}")
        except Exception as e:
            print(f"Gagal kirim callback ke Sison: {e}")
