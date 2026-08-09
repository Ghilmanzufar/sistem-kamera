import sqlite3
import json
import time
import threading
import os
from database import SessionLocal, InspectionLog, Transaction
from sqlalchemy.sql import func

DB_FILE = "offline_buffer.db"

def init_offline_buffer():
    """Inisialisasi tabel buffer lokal SQLite jika belum ada."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS buffered_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[OFFLINE BUFFER INIT ERROR] {e}")

def save_to_offline_buffer(log_type: str, data: dict):
    """Simpan payload ke SQLite lokal saat PostgreSQL tidak dapat diakses."""
    try:
        init_offline_buffer()
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO buffered_logs (log_type, payload) VALUES (?, ?)",
            (log_type, json.dumps(data))
        )
        conn.commit()
        conn.close()
        print(f"[OFFLINE BUFFER] 📦 Menyimpan 1 data ({log_type}) ke offline buffer lokal.")
    except Exception as e:
        print(f"[OFFLINE BUFFER SAVE ERROR] Gagal menyimpan ke SQLite lokal: {e}")

def get_buffered_count() -> int:
    """Ambil jumlah antrean log yang belum tersinkronisasi."""
    try:
        if not os.path.exists(DB_FILE):
            return 0
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM buffered_logs")
        cnt = cursor.fetchone()[0]
        conn.close()
        return cnt
    except Exception:
        return 0

def flush_offline_buffer() -> int:
    """Sinkronisasi data dari SQLite ke PostgreSQL jika koneksi sudah pulih."""
    if not os.path.exists(DB_FILE):
        return 0

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, log_type, payload FROM buffered_logs ORDER BY id ASC LIMIT 50")
        rows = cursor.fetchall()
        if not rows:
            conn.close()
            return 0

        synced_ids = []
        with SessionLocal() as db:
            for row_id, log_type, payload_str in rows:
                try:
                    payload = json.loads(payload_str)
                    if log_type == "INSPECTION_LOG":
                        log = InspectionLog(
                            id_trans=payload.get("id_trans"),
                            part_no=payload.get("part_no"),
                            detection_status=payload.get("detection_status"),
                            confidence_score=payload.get("confidence_score", 1.0),
                            method=payload.get("method", "AI"),
                            operator_name=payload.get("operator_name"),
                            image_path=payload.get("image_path")
                        )
                        db.add(log)
                        
                        id_trans = payload.get("id_trans")
                        if id_trans:
                            trans = db.query(Transaction).filter(Transaction.id_trans == id_trans).first()
                            if trans:
                                trans.qty_actual += 1
                                if trans.qty_actual >= trans.target_qty:
                                    trans.status = 1
                                    trans.end_time = func.now()
                    elif log_type == "NG_LOG":
                        log = InspectionLog(
                            id_trans=payload.get("id_trans"),
                            part_no=payload.get("part_no"),
                            detection_status="NG",
                            image_path=payload.get("image_path"),
                            operator_name=payload.get("operator_name"),
                            confidence_score=1.0,
                            method="AI"
                        )
                        db.add(log)
                    
                    synced_ids.append(row_id)
                except Exception as row_err:
                    print(f"[OFFLINE BUFFER ROW ERROR] Gagal proses row #{row_id}: {row_err}")
                    break
            
            if synced_ids:
                db.commit()
                # Hapus dari SQLite yang sudah sukses di-commit ke PostgreSQL
                cursor.execute(f"DELETE FROM buffered_logs WHERE id IN ({','.join(map(str, synced_ids))})")
                conn.commit()
                print(f"[OFFLINE BUFFER SYNC] ✅ Berhasil mem-flush {len(synced_ids)} log dari buffer ke PostgreSQL.")

        conn.close()
        return len(synced_ids)
    except Exception:
        # PostgreSQL masih down / offline, biarkan antrean tetap di SQLite
        return 0

def start_buffer_sync_worker():
    """Background worker yang memeriksa dan mem-flush buffer saat PostgreSQL online."""
    init_offline_buffer()
    def loop():
        while True:
            try:
                cnt = get_buffered_count()
                if cnt > 0:
                    flush_offline_buffer()
            except Exception:
                pass
            time.sleep(5.0)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
