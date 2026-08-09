from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database_config import get_db, PartRule, User, InspectionLog, Transaction, CameraConfig, SisonConfig, GlobalSettings, AuditLog, log_audit_event, hash_password, verify_password
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from collections import defaultdict
import os
import shutil
import tempfile
import base64
import json
import hmac
import hashlib
import time
import secrets
from typing import Optional
from datetime import datetime, timedelta

admin_security = HTTPBearer()

def _get_secret_key() -> str:
    """
    👱 Ponytail Security: Ambil SECRET_KEY dari environment (.env).
    Jika belum ada atau masih bernilai default rentan, buat token acak 64-karakter dan simpan ke .env secara otomatis.
    """
    secret = os.getenv("SECRET_KEY", "").strip()
    if not secret or secret == "sugity_super_secret_key_2026":
        env_path = os.path.join(os.getcwd(), ".env")
        new_secret = secrets.token_hex(32)
        
        env_lines = []
        key_found = False
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("SECRET_KEY="):
                        env_lines.append(f"SECRET_KEY={new_secret}\n")
                        key_found = True
                    else:
                        env_lines.append(line)
        if not key_found:
            env_lines.append(f"\nSECRET_KEY={new_secret}\n")
        
        try:
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(env_lines)
            os.environ["SECRET_KEY"] = new_secret
            print(f"[SECURITY] 🔒 Secret key aman (64-char) berhasil di-generate dan disimpan ke .env!")
            return new_secret
        except Exception:
            os.environ["SECRET_KEY"] = new_secret
            return new_secret
    return secret

def create_admin_token(username: str, role: str, expires_in_seconds: Optional[int] = None) -> str:
    """👱 Ponytail Token Generator: Buat signed token dengan timestamp kedaluwarsa (Default 10 Menit)."""
    if expires_in_seconds is None:
        expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10"))
        expires_in_seconds = expire_minutes * 60
    secret = _get_secret_key()
    exp = int(time.time()) + expires_in_seconds
    payload = {"u": username, "r": role, "exp": exp}
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    sig = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"

def decode_and_verify_token(token: str) -> dict:
    secret = _get_secret_key()
    parts = token.split(".")
    if len(parts) == 1 and secrets.compare_digest(token, secret):
        return {"u": "pengawas", "r": "pengawas", "exp": int(time.time()) + 600}
    if len(parts) != 2:
        raise HTTPException(status_code=401, detail="Format token tidak valid")
    payload_b64, sig = parts
    expected_sig = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    if not secrets.compare_digest(sig, expected_sig):
        raise HTTPException(status_code=401, detail="Tanda tangan token tidak valid / Ditolak")
    
    padding = '=' * (-len(payload_b64) % 4)
    try:
        payload_json = base64.urlsafe_b64decode(payload_b64 + padding).decode()
        payload = json.loads(payload_json)
    except Exception:
        raise HTTPException(status_code=401, detail="Payload token tidak dapat dibaca")
        
    if time.time() > payload.get("exp", 0):
        raise HTTPException(status_code=401, detail="Token telah kedaluwarsa (Batas 10 Menit Habis). Silakan login kembali.")
    return payload

def verify_admin_auth(request: Request, credentials: HTTPAuthorizationCredentials = Depends(admin_security)) -> dict:
    """👱 Ponytail: Proteksi endpoint admin dengan verifikasi token & hak akses role (Pengawas / Operator)."""
    payload = decode_and_verify_token(credentials.credentials)
    role = payload.get("r", "pengawas")
    
    # Peran Operator HANYA boleh mengakses /inspection-logs dan /logout
    if role == "operator":
        path = request.url.path
        if not (path.endswith("/inspection-logs") or path.endswith("/logout")):
            raise HTTPException(status_code=403, detail="Akses ditolak. Peran Operator hanya diizinkan melihat History Inspeksi.")
            
    return payload

def get_current_user_name(credentials: HTTPAuthorizationCredentials = Depends(admin_security)) -> str:
    payload = decode_and_verify_token(credentials.credentials)
    return payload.get("u", "SYSTEM")

router = APIRouter(dependencies=[Depends(verify_admin_auth)])
public_router = APIRouter()

# --- RATE LIMITER (BRUTE FORCE PROTECTION) ---
_failed_login_attempts = defaultdict(list)
import threading
_login_rate_lock = threading.Lock()

def _check_rate_limit(client_ip: str):
    now = time.time()
    with _login_rate_lock:
        _failed_login_attempts[client_ip] = [t for t in _failed_login_attempts[client_ip] if now - t < 60]
        if len(_failed_login_attempts[client_ip]) >= 5:
            time_left = int(60 - (now - _failed_login_attempts[client_ip][0]))
            raise HTTPException(
                status_code=429, 
                detail=f"Terlalu banyak percobaan login gagal. Silakan tunggu {max(1, time_left)} detik sebelum mencoba lagi."
            )

def _record_failed_attempt(client_ip: str):
    with _login_rate_lock:
        _failed_login_attempts[client_ip].append(time.time())

def _clear_failed_attempts(client_ip: str):
    with _login_rate_lock:
        if client_ip in _failed_login_attempts:
            del _failed_login_attempts[client_ip]

class LoginSchema(BaseModel):
    username: str
    password: str

SERVER_START_TIME = time.time()

def _get_uptime_string(seconds: float) -> str:
    s = int(seconds)
    hours = s // 3600
    minutes = (s % 3600) // 60
    secs = s % 60
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"

@public_router.get("/health")
def get_system_health(db: Session = Depends(get_db)):
    """
    👱 Ponytail Industrial Telemetry:
    Endpoint observabilitas terpadu untuk memantau status Database, Buffer Queue, Disk Storage, Model AI, dan Uptime.
    """
    now = time.time()
    uptime_sec = round(now - SERVER_START_TIME, 1)
    
    # 1. Database Health & Latency
    db_status = "CONNECTED"
    db_latency_ms = 0.0
    try:
        t0 = time.time()
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_latency_ms = round((time.time() - t0) * 1000, 1)
    except Exception as e:
        db_status = f"ERROR: {str(e)}"

    # 2. Offline Buffer Queue Status
    from offline_buffer import get_buffered_count
    buffer_queue = get_buffered_count()

    # 3. Disk Space Telemetry (Standard Library shutil)
    try:
        total_b, used_b, free_b = shutil.disk_usage(os.getcwd())
        total_gb = round(total_b / (1024**3), 2)
        free_gb = round(free_b / (1024**3), 2)
        used_gb = round(used_b / (1024**3), 2)
        used_pct = round((used_b / total_b) * 100, 1)
        free_pct = round((free_b / total_b) * 100, 1)
        is_disk_low = free_pct < 10.0
    except Exception:
        total_gb, free_gb, used_gb, used_pct, free_pct, is_disk_low = 0, 0, 0, 0, 0, False

    # 4. State & AI Model Telemetry
    from proses_kamera import state, model_cache
    with state.lock:
        app_status = state.status
        active_part = state.p_no
        qty_progress = f"{state.target_qty - state.qty}/{state.target_qty}" if state.target_qty > 0 else "-"
        inspection_mode = getattr(state, "inspection_mode", "AI")

    # Evaluasi status sistem menyeluruh
    is_healthy = (db_status == "CONNECTED") and not is_disk_low
    overall_status = "HEALTHY" if is_healthy else ("DEGRADED" if not is_disk_low else "DISK_SPACE_LOW")

    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "uptime": {
            "seconds": uptime_sec,
            "human": _get_uptime_string(uptime_sec)
        },
        "database": {
            "status": db_status,
            "latency_ms": db_latency_ms,
            "offline_buffer_unsynced_count": buffer_queue
        },
        "inspection_engine": {
            "system_state": app_status,
            "active_part_no": active_part or "STANDBY",
            "progress": qty_progress,
            "mode": inspection_mode,
            "cached_models_count": len(model_cache._cache)
        },
        "disk_storage": {
            "total_gb": total_gb,
            "used_gb": used_gb,
            "free_gb": free_gb,
            "used_percent": used_pct,
            "free_percent": free_pct,
            "is_low_space_warning": is_disk_low
        },
        "network": {
            "local_ip": _get_local_ip(),
            "port": 8000
        }
    }

@public_router.post("/admin-login")
def admin_login(creds: LoginSchema, request: Request, db: Session = Depends(get_db)):
    """👱 Ponytail: Endpoint otentikasi dengan proteksi Brute-Force Rate Limiter & Token Expiration 10 Menit."""
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    user = db.query(User).filter(User.username == creds.username).first()
    if not user or not verify_password(creds.password, user.password):
        _record_failed_attempt(client_ip)
        raise HTTPException(status_code=401, detail="Username atau PIN salah!")
    if not getattr(user, 'is_active', True) or user.role not in ["pengawas", "operator"]:
        _record_failed_attempt(client_ip)
        raise HTTPException(status_code=403, detail="Akun tidak berwenang mengakses Dashboard!")
    
    _clear_failed_attempts(client_ip)
    token = create_admin_token(user.username, user.role)
    log_audit_event(db, user.username, "LOGIN", f"Berhasil masuk sebagai {user.role.upper()} (IP: {client_ip})")
    return {"token": token, "role": user.role, "username": user.username}

@router.post("/logout")
def admin_logout(db: Session = Depends(get_db), auth: dict = Depends(verify_admin_auth)):
    """👱 Ponytail: Catat aktivitas keluar (LOGOUT) dari Dashboard."""
    username = auth.get("u", "ADMIN")
    log_audit_event(db, username, "LOGOUT", "User keluar dari Dashboard")
    return {"success": True}

# --- SCHEMAS ---
class ComponentSchema(BaseModel):
    sisi: Optional[str] = "-"
    nama_komponen: str
    qty: Optional[int] = 1
    min_confidence: Optional[float] = 0.70

class PartRuleSchema(BaseModel):
    p_no: str
    avg_confidence: Optional[float] = 0.75
    min_coverage: Optional[float] = 1.0
    komponen: list[ComponentSchema]

class GlobalRuleSchema(BaseModel):
    default_avg_conf: float
    default_min_conf: float
    default_min_coverage: float

class RenameModelSchema(BaseModel):
    new_part_no: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str
    fullname: str
    is_active: bool = True

class UserUpdate(BaseModel):
    username: str
    password: Optional[str] = None
    role: str
    fullname: str
    is_active: bool = True

class CameraConfigCreate(BaseModel):
    name: str
    source: str

class CameraConfigUpdate(BaseModel):
    name: str
    source: str


# --- MONITORING API ---
@router.get("/transactions")
def get_transactions(date_filter: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Transaction)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            start_date = datetime(filter_date.year, filter_date.month, filter_date.day, 0, 0, 0)
            end_date = datetime(filter_date.year, filter_date.month, filter_date.day, 23, 59, 59)
            query = query.filter(Transaction.start_time >= start_date, Transaction.start_time <= end_date)
            return query.order_by(Transaction.start_time.desc()).all()
        except ValueError:
            pass
            
    trans = query.order_by(Transaction.start_time.desc()).limit(50).all()
    return trans

@router.delete("/transactions/running")
def clear_running_transactions(db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    """👱 Ponytail: Hapus seluruh transaksi berstatus RUNNING (status=2) dari database."""
    deleted_count = db.query(Transaction).filter(Transaction.status == 2).delete()
    db.commit()
    log_audit_event(db, uname, "DELETE_RUNNING_TRANS", f"Menghapus {deleted_count} transaksi ber-status RUNNING")
    return {"success": True, "count": deleted_count, "message": f"Berhasil menghapus {deleted_count} transaksi RUNNING."}

@router.get("/inspection-logs")
def get_inspection_logs(
    date_filter: Optional[str] = None, 
    month_filter: Optional[str] = None,
    part_filter: Optional[str] = None, 
    status_filter: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    """👱 Ponytail: Ambil riwayat log inspeksi kamera (OK & NG) dengan filter tanggal/bulan, part_no, dan status."""
    query = db.query(
        InspectionLog,
        Transaction.lot_no,
        Transaction.unique_no,
        Transaction.part_name,
        Transaction.target_qty,
        Transaction.qty_actual
    ).outerjoin(Transaction, InspectionLog.id_trans == Transaction.id_trans)
    
    if month_filter:
        try:
            f_month = datetime.strptime(month_filter, "%Y-%m").date()
            start_date = datetime(f_month.year, f_month.month, 1, 0, 0, 0)
            if f_month.month == 12:
                end_date = datetime(f_month.year + 1, 1, 1, 0, 0, 0) - timedelta(seconds=1)
            else:
                end_date = datetime(f_month.year, f_month.month + 1, 1, 0, 0, 0) - timedelta(seconds=1)
            query = query.filter(InspectionLog.created_at >= start_date, InspectionLog.created_at <= end_date)
        except ValueError:
            pass
    elif date_filter:
        try:
            f_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            start_date = datetime(f_date.year, f_date.month, f_date.day, 0, 0, 0)
            end_date = datetime(f_date.year, f_date.month, f_date.day, 23, 59, 59)
            query = query.filter(InspectionLog.created_at >= start_date, InspectionLog.created_at <= end_date)
        except ValueError:
            pass

    if part_filter and part_filter.strip():
        query = query.filter(InspectionLog.part_no.ilike(f"%{part_filter.strip()}%"))

    if status_filter and status_filter.strip() and status_filter != "ALL":
        query = query.filter(InspectionLog.detection_status == status_filter.strip())
            
    logs_raw = query.order_by(InspectionLog.created_at.desc()).limit(500).all()
    
    result = []
    for log, lot_no, unique_no, part_name, target_qty, qty_actual in logs_raw:
        result.append({
            "id": log.id,
            "created_at": log.created_at,
            "id_trans": log.id_trans,
            "part_no": log.part_no,
            "part_name": part_name or "-",
            "lot_no": lot_no or "-",
            "unique_no": unique_no or "-",
            "detection_status": log.detection_status,
            "confidence_score": log.confidence_score,
            "method": getattr(log, 'method', 'AI') or 'AI',
            "target_qty": target_qty if target_qty is not None else "-",
            "qty_actual": qty_actual if qty_actual is not None else "-"
        })
    return result

@router.delete("/inspection-logs")
def clear_all_inspection_logs(db: Session = Depends(get_db), auth: dict = Depends(verify_admin_auth)):
    """👱 Ponytail: Hapus seluruh riwayat log inspeksi dan catat di audit logs."""
    username = auth.get("u", "ADMIN")
    deleted_count = db.query(InspectionLog).delete()
    log_audit_event(db, username, "DELETE_ALL_INSPECTION_LOGS", f"Menghapus seluruh {deleted_count} data riwayat inspeksi")
    db.commit()
    return {"success": True, "message": f"Berhasil menghapus {deleted_count} data riwayat inspeksi."}
@router.get("/audit-logs")
def get_audit_logs(date_filter: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(AuditLog)
    if date_filter:
        try:
            f_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            start_date = datetime(f_date.year, f_date.month, f_date.day, 0, 0, 0)
            end_date = datetime(f_date.year, f_date.month, f_date.day, 23, 59, 59)
            query = query.filter(AuditLog.timestamp >= start_date, AuditLog.timestamp <= end_date)
        except ValueError:
            pass
    raw_logs = query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    result = []
    for log in raw_logs:
        ts_str = log.timestamp.isoformat() if log.timestamp else datetime.now().isoformat()
        result.append({
            "id": log.id,
            "timestamp": ts_str,
            "created_at": ts_str,
            "username": log.username or "SYSTEM",
            "action": log.action,
            "details": log.details or ""
        })
    return result

# --- PART RULES API ---
@router.get("/rules")
def get_all_rules(db: Session = Depends(get_db)):
    rules_raw = db.query(PartRule).all()
    
    # Group by p_no
    grouped = defaultdict(list)
    avg_conf_map = {}
    for r in rules_raw:
        min_c = getattr(r, 'min_confidence', 0.70)
        if min_c is None: min_c = 0.70
        avg_c = getattr(r, 'avg_confidence', 0.75)
        if avg_c is None: avg_c = 0.75
        min_cov = getattr(r, 'min_coverage', 1.0)
        if min_cov is None: min_cov = 1.0

        grouped[r.p_no].append({
            "sisi": r.sisi or "-",
            "nama_komponen": r.nama_komponen,
            "qty": r.qty or 1,
            "min_confidence": min_c
        })
        avg_conf_map[r.p_no] = avg_c
        
    result = []
    for p_no, comps in grouped.items():
        # Get min_coverage from the first component of this p_no (they are all the same)
        # Re-fetch or just extract from first row
        min_cov = 1.0
        if rules_raw:
            first_rule = next((x for x in rules_raw if x.p_no == p_no), None)
            if first_rule and getattr(first_rule, 'min_coverage', None) is not None:
                min_cov = first_rule.min_coverage

        result.append({
            "p_no": p_no,
            "avg_confidence": avg_conf_map.get(p_no, 0.75),
            "min_coverage": min_cov,
            "komponen": comps
        })
    return result

@router.post("/rules")
def save_rule(rule_data: PartRuleSchema, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    try:
        # Hapus semua komponen lama untuk p_no ini
        db.query(PartRule).filter(PartRule.p_no == rule_data.p_no).delete()
        db.flush()

        avg_c = rule_data.avg_confidence if rule_data.avg_confidence is not None else 0.75
        min_cov = rule_data.min_coverage if rule_data.min_coverage is not None else 1.0

        # Bulk insert komponen baru
        for c in rule_data.komponen:
            min_c = c.min_confidence if c.min_confidence is not None else 0.70
            new_comp = PartRule(
                p_no=rule_data.p_no,
                sisi=c.sisi or "-",
                nama_komponen=c.nama_komponen,
                qty=c.qty or 1,
                min_confidence=min_c,
                avg_confidence=avg_c,
                min_coverage=min_cov
            )
            db.add(new_comp)

        db.commit()
        log_audit_event(db, uname, "SAVE_RULE", f"Menyimpan rule part {rule_data.p_no} ({len(rule_data.komponen)} komponen)")
        return {"success": True, "message": "Rule saved successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/rules/{p_no}")
def delete_rule(p_no: str, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    deleted_count = db.query(PartRule).filter(PartRule.p_no == p_no).delete()
    if deleted_count > 0:
        db.commit()
        log_audit_event(db, uname, "DELETE_RULE", f"Menghapus rule part {p_no}")
        return {"success": True, "message": "Rule deleted"}
    raise HTTPException(status_code=404, detail="Rule not found")

# --- GLOBAL RULES API ---
def _get_or_create_global_settings(db: Session) -> GlobalSettings:
    gs = db.query(GlobalSettings).first()
    if not gs:
        gs = GlobalSettings()
        db.add(gs)
        db.commit()
        db.refresh(gs)
    return gs

@router.get("/global-rule")
def get_global_rule(db: Session = Depends(get_db)):
    gs = _get_or_create_global_settings(db)
    total_parts = db.query(PartRule.p_no).distinct().count()
    return {
        "default_avg_conf": gs.default_avg_conf,
        "default_min_conf": gs.default_min_conf,
        "default_min_coverage": gs.default_min_coverage,
        "total_parts": total_parts
    }

@router.post("/global-rule")
def update_global_rule(data: GlobalRuleSchema, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    # 1. Simpan ke GlobalSettings
    gs = _get_or_create_global_settings(db)
    gs.default_avg_conf = data.default_avg_conf
    gs.default_min_conf = data.default_min_conf
    gs.default_min_coverage = data.default_min_coverage
    
    # 2. Bulk Update tabel PartRule
    db.query(PartRule).update({
        PartRule.avg_confidence: data.default_avg_conf,
        PartRule.min_confidence: data.default_min_conf,
        PartRule.min_coverage: data.default_min_coverage
    })
    db.commit()
    log_audit_event(db, uname, "UPDATE_GLOBAL_RULE", f"Bulk update rule global (Avg: {data.default_avg_conf*100:.0f}%, MinConf: {data.default_min_conf*100:.0f}%, Coverage: {data.default_min_coverage*100:.0f}%)")
    return {"success": True, "message": "Global rule disimpan dan diaplikasikan ke semua part."}

# --- MODELS API ---
WEIGHTS_DIR = os.path.join(os.getcwd(), "weights")

@router.get("/models")
def get_models(db: Session = Depends(get_db)):
    if not os.path.exists(WEIGHTS_DIR):
        os.makedirs(WEIGHTS_DIR)
    
    # Cek transaksi running untuk indikator aktif
    active_trans = db.query(Transaction).filter(Transaction.status == 2).first()
    active_pno = active_trans.part_no if active_trans else ""

    parts_dict = {}
    for filename in os.listdir(WEIGHTS_DIR):
        if filename.endswith(".pt") or filename.endswith(".onnx"):
            is_onnx = filename.endswith(".onnx")
            part_no = filename[:-5] if is_onnx else filename[:-3]
            file_path = os.path.join(WEIGHTS_DIR, filename)
            size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M')

            if part_no not in parts_dict:
                parts_dict[part_no] = {
                    "part_no": part_no,
                    "has_pt": False,
                    "has_onnx": False,
                    "pt_size_mb": None,
                    "onnx_size_mb": None,
                    "last_modified": mtime,
                    "is_active": (part_no.lower() == active_pno.lower()) if active_pno else False
                }

            if is_onnx:
                parts_dict[part_no]["has_onnx"] = True
                parts_dict[part_no]["onnx_size_mb"] = size_mb
            else:
                parts_dict[part_no]["has_pt"] = True
                parts_dict[part_no]["pt_size_mb"] = size_mb

    for p_no, item in parts_dict.items():
        if item["has_onnx"]:
            item["format"] = "ONNX"
            item["filename"] = f"{p_no}.onnx"
            item["size_mb"] = item["onnx_size_mb"]
        else:
            item["format"] = "PT"
            item["filename"] = f"{p_no}.pt"
            item["size_mb"] = item["pt_size_mb"]

    return list(parts_dict.values())

@router.post("/models/{part_no}/convert-onnx")
def convert_model_to_onnx(part_no: str, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    """👱 Ponytail: Export model PyTorch (.pt) ke format ONNX ultra-ringan dengan 1-click."""
    pt_path = os.path.join(WEIGHTS_DIR, f"{part_no}.pt")
    if not os.path.exists(pt_path):
        raise HTTPException(status_code=404, detail=f"Berkas model {part_no}.pt tidak ditemukan!")

    try:
        from ultralytics import YOLO
        import time as pytime
        t_start = pytime.time()
        
        print(f"[ONNX EXPORT] Memulai konversi model {pt_path} ke format ONNX...")
        yolo_model = YOLO(pt_path)
        exported_path = yolo_model.export(format="onnx", dynamic=False, simplify=True)
        duration_s = round(pytime.time() - t_start, 2)
        
        # Bersihkan cache model agar instant switch ke ONNX
        from proses_kamera import model_cache
        model_cache.clear()

        onnx_file = f"{part_no}.onnx"
        onnx_path = os.path.join(WEIGHTS_DIR, onnx_file)
        onnx_size = round(os.path.getsize(onnx_path) / (1024 * 1024), 2) if os.path.exists(onnx_path) else 0

        log_audit_event(db, uname, "CONVERT_ONNX", f"Export model {part_no}.pt ke format ONNX ({onnx_size} MB dalam {duration_s}s)")
        return {
            "success": True, 
            "message": f"Model {part_no} berhasil dikonversi ke format ONNX ({onnx_size} MB) dalam {duration_s} detik!",
            "onnx_size_mb": onnx_size,
            "duration_seconds": duration_s
        }
    except Exception as e:
        print(f"[ONNX EXPORT ERROR] {e}")
        raise HTTPException(status_code=500, detail=f"Gagal mengonversi ke ONNX: {str(e)}")

@router.get("/models/{part_no}/download")
def download_model(part_no: str, fmt: Optional[str] = None):
    if fmt == "onnx" or (fmt is None and os.path.exists(os.path.join(WEIGHTS_DIR, f"{part_no}.onnx"))):
        file_path = os.path.join(WEIGHTS_DIR, f"{part_no}.onnx")
        filename = f"{part_no}.onnx"
    else:
        file_path = os.path.join(WEIGHTS_DIR, f"{part_no}.pt")
        filename = f"{part_no}.pt"

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Model file not found")
    return FileResponse(file_path, filename=filename, media_type="application/octet-stream")

@router.get("/models/{part_no}/detail")
def get_model_detail(part_no: str, db: Session = Depends(get_db)):
    pt_path = os.path.join(WEIGHTS_DIR, f"{part_no}.pt")
    onnx_path = os.path.join(WEIGHTS_DIR, f"{part_no}.onnx")
    
    file_path = onnx_path if os.path.exists(onnx_path) else pt_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Model file not found")
    
    rules = db.query(PartRule).filter(PartRule.p_no == part_no).all()
    components = [{
        "sisi": r.sisi or "-",
        "nama_komponen": r.nama_komponen,
        "qty": r.qty or 1,
        "min_confidence": r.min_confidence or 0.70
    } for r in rules]

    mtime = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
    size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)

    return {
        "part_no": part_no,
        "filename": os.path.basename(file_path),
        "format": "ONNX" if os.path.exists(onnx_path) else "PT",
        "has_pt": os.path.exists(pt_path),
        "has_onnx": os.path.exists(onnx_path),
        "size_mb": size_mb,
        "last_modified": mtime,
        "komponen_count": len(components),
        "komponen": components
    }

@router.post("/models")
def upload_model(part_no: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.pt', '.onnx']:
        raise HTTPException(status_code=400, detail="Hanya file berekstensi .pt atau .onnx yang diizinkan")
    
    if not os.path.exists(WEIGHTS_DIR):
        os.makedirs(WEIGHTS_DIR)
        
    file_path = os.path.join(WEIGHTS_DIR, f"{part_no}{ext}")
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        from proses_kamera import model_cache
        model_cache.clear()

        # Auto-generate PartRule jika file adalah .pt
        if ext == '.pt':
            try:
                import torch
                ckpt = torch.load(file_path, map_location="cpu", weights_only=False)
                names = None
                if isinstance(ckpt, dict) and 'model' in ckpt:
                    raw = getattr(ckpt['model'], 'names', None)
                    if raw is not None:
                        names = [str(v) for k, v in sorted(raw.items(), key=lambda x: int(x[0]))]
                if names:
                    gs = _get_or_create_global_settings(db)
                    db.query(PartRule).filter(PartRule.p_no == part_no).delete()
                    db.flush()
                    for label in names:
                        db.add(PartRule(
                            p_no=part_no,
                            sisi="-",
                            nama_komponen=label,
                            qty=1,
                            min_confidence=gs.default_min_conf,
                            avg_confidence=gs.default_avg_conf,
                            min_coverage=gs.default_min_coverage
                        ))
                    db.commit()
            except Exception as e_lbl:
                print(f"Notice auto-generate rule: {e_lbl}")

        log_audit_event(db, uname, "UPLOAD_MODEL", f"Mengunggah model AI {part_no}{ext}")
        return {"success": True, "message": f"Model for {part_no}{ext} uploaded successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/models/preview-labels")
async def preview_model_labels(file: UploadFile = File(...)):
    """Baca label names dari file .pt sementara — tidak disimpan permanen."""
    if not file.filename.endswith('.pt'):
        return {"label_count": 0, "labels": {}, "note": "Preview label otomatis hanya tersedia untuk file .pt"}
    
    try:
        import torch
    except ImportError:
        raise HTTPException(status_code=500, detail="torch tidak terinstall di server")

    tmp = tempfile.NamedTemporaryFile(suffix=".pt", delete=False)
    try:
        shutil.copyfileobj(file.file, tmp)
        tmp.close()

        ckpt = torch.load(tmp.name, map_location="cpu", weights_only=False)

        names = None
        if isinstance(ckpt, dict) and 'model' in ckpt:
            raw = getattr(ckpt['model'], 'names', None)
            if raw is not None:
                names = {str(k): v for k, v in raw.items()}
        
        if names is None:
            return {"label_count": 0, "labels": {}}

        return {"label_count": len(names), "labels": names}

    except Exception as e:
        return {"label_count": 0, "labels": {}, "error": str(e)}
    finally:
        os.unlink(tmp.name)


@router.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()

@router.post("/users")
def create_user(user: UserCreate, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    db_user = User(username=user.username, password=hash_password(user.password), role=user.role, fullname=user.fullname, is_active=user.is_active)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    log_audit_event(db, uname, "CREATE_USER", f"Membuat user baru: {user.username} ({user.fullname}, Role: {user.role.upper()})")
    return db_user

@router.put("/users/{user_id}")
def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.username = user.username
    if user.password:
        db_user.password = hash_password(user.password)
    db_user.role = user.role
    db_user.fullname = user.fullname
    db_user.is_active = user.is_active
    db.commit()
    db.refresh(db_user)
    log_audit_event(db, uname, "UPDATE_USER", f"Mengubah data user {user.username} (Role: {user.role.upper()})")
    return db_user

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    target_username = db_user.username
    db.delete(db_user)
    db.commit()
    log_audit_event(db, uname, "DELETE_USER", f"Menghapus user {target_username} (ID: #{user_id})")
    return {"status": "ok"}

@router.put("/models/{part_no}")
def rename_model(part_no: str, data: RenameModelSchema, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    renamed = False
    for ext in [".pt", ".onnx"]:
        old_path = os.path.join(WEIGHTS_DIR, f"{part_no}{ext}")
        new_path = os.path.join(WEIGHTS_DIR, f"{data.new_part_no}{ext}")
        if os.path.exists(old_path):
            os.rename(old_path, new_path)
            renamed = True
            
    if not renamed:
        raise HTTPException(status_code=404, detail="Model not found")
        
    from proses_kamera import model_cache
    model_cache.clear()
    log_audit_event(db, uname, "RENAME_MODEL", f"Mengubah nama model {part_no} menjadi {data.new_part_no}")
    return {"success": True, "message": "Model renamed successfully"}

@router.delete("/models/{part_no}")
def delete_model(part_no: str, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    deleted = False
    for ext in [".pt", ".onnx"]:
        file_path = os.path.join(WEIGHTS_DIR, f"{part_no}{ext}")
        if os.path.exists(file_path):
            os.remove(file_path)
            deleted = True

    if deleted:
        from proses_kamera import model_cache
        model_cache.clear()
        log_audit_event(db, uname, "DELETE_MODEL", f"Menghapus file model {part_no}")
        return {"success": True, "message": "Model deleted"}
    raise HTTPException(status_code=404, detail="Model not found")

# --- CAMERA API ---
import subprocess

def _camera_to_dict(c: CameraConfig) -> dict:
    return {
        "id": c.id,
        "name": c.name or "Kamera",
        "source": c.source or "0",
        "is_active": bool(c.is_active)
    }

def _scan_hardware_cameras(db: Session):
    """Pindai kamera hardware USB terhubung ke komputer dan sinkronkan dengan Database."""
    pnp_names = []
    try:
        cmd = ['powershell', '-NoProfile', '-Command', 'Get-PnpDevice -Class Camera, Image -Status OK | Select-Object -ExpandProperty FriendlyName']
        res = subprocess.check_output(cmd, timeout=5).decode(errors='ignore')
        pnp_names = [line.strip() for line in res.splitlines() if line.strip()]
    except Exception:
        pass

    existing_cams = db.query(CameraConfig).all()
    existing_sources = {c.source for c in existing_cams}
    
    new_added = False
    sources_to_check = pnp_names if pnp_names else ["USB 2.0 Camera"]
    for idx, cam_name in enumerate(sources_to_check):
        src_str = str(idx)
        if src_str not in existing_sources:
            is_first = (db.query(CameraConfig).count() == 0)
            db_cam = CameraConfig(name=cam_name, source=src_str, is_active=is_first)
            db.add(db_cam)
            existing_sources.add(src_str)
            new_added = True
            
    if new_added:
        db.commit()
        
    cams = db.query(CameraConfig).order_by(CameraConfig.id.asc()).all()
    return [_camera_to_dict(c) for c in cams]

@router.get("/cameras")
def get_cameras(db: Session = Depends(get_db)):
    cams = db.query(CameraConfig).order_by(CameraConfig.id.asc()).all()
    if not cams:
        return _scan_hardware_cameras(db)
    return [_camera_to_dict(c) for c in cams]

@router.post("/cameras/scan")
def scan_cameras(db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    cams = _scan_hardware_cameras(db)
    log_audit_event(db, uname, "SCAN_CAMERAS", f"Memindai ulang kamera hardware. Total {len(cams)} kamera terdaftar.")
    return cams

@router.post("/cameras")
def create_camera(cam: CameraConfigCreate, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    is_first = (db.query(CameraConfig).count() == 0)
    db_cam = CameraConfig(name=cam.name, source=cam.source, is_active=is_first)
    db.add(db_cam)
    db.commit()
    db.refresh(db_cam)
    log_audit_event(db, uname, "CREATE_CAMERA", f"Menambah kamera {cam.name} (Source: {cam.source})")
    return _camera_to_dict(db_cam)

@router.put("/cameras/{cam_id}")
def update_camera(cam_id: int, cam: CameraConfigUpdate, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    db_cam = db.query(CameraConfig).filter(CameraConfig.id == cam_id).first()
    if not db_cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    db_cam.name = cam.name
    db_cam.source = cam.source
    db.commit()
    db.refresh(db_cam)
    log_audit_event(db, uname, "UPDATE_CAMERA", f"Mengubah kamera ID #{cam_id} menjadi {cam.name} (Source: {cam.source})")
    return _camera_to_dict(db_cam)

@router.put("/cameras/{cam_id}/toggle")
def toggle_camera(cam_id: int, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    db_cam = db.query(CameraConfig).filter(CameraConfig.id == cam_id).first()
    if not db_cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    new_state = not db_cam.is_active
    if new_state:
        db.query(CameraConfig).update({CameraConfig.is_active: False})
        db_cam.is_active = True
    else:
        db_cam.is_active = False
        
    db.commit()
    status_text = "ON (Aktif)" if db_cam.is_active else "OFF (Standby)"
    log_audit_event(db, uname, "TOGGLE_CAMERA", f"Mengubah status kamera #{cam_id} ({db_cam.name}) menjadi {status_text}")
    return {"status": "ok", "is_active": db_cam.is_active, "message": f"Kamera {db_cam.name} disetel {status_text}"}

@router.put("/cameras/{cam_id}/activate")
def activate_camera(cam_id: int, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    # Deactivate all
    db.query(CameraConfig).update({CameraConfig.is_active: False})
    # Activate selected
    db_cam = db.query(CameraConfig).filter(CameraConfig.id == cam_id).first()
    if not db_cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    db_cam.is_active = True
    db.commit()
    log_audit_event(db, uname, "ACTIVATE_CAMERA", f"Mengaktifkan kamera {db_cam.name} (Source: {db_cam.source})")
    return {"status": "ok", "message": f"Camera {db_cam.name} activated"}

@router.delete("/cameras/{cam_id}")
def delete_camera(cam_id: int, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    db_cam = db.query(CameraConfig).filter(CameraConfig.id == cam_id).first()
    if not db_cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    cam_name = db_cam.name
    was_active = db_cam.is_active
    db.delete(db_cam)
    db.commit()

    # Jika yang dihapus adalah kamera aktif, tunjuk kamera lain jika ada
    if was_active:
        remaining_cam = db.query(CameraConfig).first()
        if remaining_cam:
            remaining_cam.is_active = True
            db.commit()
            log_audit_event(db, uname, "AUTO_ACTIVATE_CAMERA", f"Otomatis mengaktifkan {remaining_cam.name} setelah kamera aktif dihapus")

    log_audit_event(db, uname, "DELETE_CAMERA", f"Menghapus kamera {cam_name} (ID: #{cam_id})")
    return {"status": "ok", "was_active": was_active}


# --- SISON CONFIG API ---
import socket
from kirim_ke_sison import SisonSender

def _get_local_ip() -> str:
    """Ambil IP lokal PC saat ini."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class SisonConfigUpdate(BaseModel):
    callback_url: str
    api_key: str

class SisonTestPingRequest(BaseModel):
    callback_url: str

def _get_or_create_sison_config(db: Session) -> SisonConfig:
    """Ambil config Sison (singleton). Buat baris default jika belum ada."""
    cfg = db.query(SisonConfig).first()
    if not cfg:
        cfg = SisonConfig()
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg

@router.get("/sison-config")
def get_sison_config(db: Session = Depends(get_db)):
    cfg = _get_or_create_sison_config(db)
    return {
        "callback_url": cfg.callback_url,
        "api_key": cfg.api_key,
        "server_ip": _get_local_ip(),
        "server_port": 8000
    }

@router.put("/sison-config")
def update_sison_config(data: SisonConfigUpdate, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    cfg = _get_or_create_sison_config(db)
    cfg.callback_url = data.callback_url
    cfg.api_key = data.api_key
    db.commit()
    log_audit_event(db, uname, "UPDATE_SISON_CONFIG", f"Mengubah konfigurasi Sison Callback ke {data.callback_url}")
    return {"success": True, "message": "Konfigurasi Sison berhasil disimpan"}

@router.post("/sison-test-ping")
def test_sison_ping(req: SisonTestPingRequest):
    """👱 Ponytail: Uji konektivitas webhook ke endpoint server SISON."""
    if not req.callback_url or not req.callback_url.startswith("http"):
        raise HTTPException(status_code=400, detail="URL Webhook tidak valid (harus diawali http:// atau https://)")
    res = SisonSender.test_ping(req.callback_url)
    return res
