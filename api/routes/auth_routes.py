import os
import time
import socket
import shutil
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db, User, verify_password, log_audit_event
from integrations import get_buffered_count
from core import state, model_cache
from api.auth import (
    create_admin_token,
    verify_admin_auth,
    check_rate_limit,
    record_failed_attempt,
    clear_failed_attempts
)

router = APIRouter()
SERVER_START_TIME = time.time()

class LoginSchema(BaseModel):
    username: str
    password: str

def get_local_ip() -> str:
    """Ambil IP lokal PC saat ini."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def get_uptime_string(seconds: float) -> str:
    s = int(seconds)
    hours = s // 3600
    minutes = (s % 3600) // 60
    secs = s % 60
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"

@router.get("/health")
def get_system_health(db: Session = Depends(get_db)):
    """Telemetry status lengkap untuk frontend SystemHealth & Sidebar."""
    now = time.time()
    uptime_sec = round(now - SERVER_START_TIME, 1)
    
    # 1. Database Health & Latency
    db_status = "CONNECTED"
    db_latency_ms = 0.0
    try:
        t0 = time.time()
        db.execute(text("SELECT 1"))
        db_latency_ms = round((time.time() - t0) * 1000, 1)
    except Exception as e:
        db_status = f"ERROR: {str(e)}"

    # 2. Offline Buffer Queue Status
    buffer_queue = get_buffered_count()

    # 3. Disk Space Telemetry
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
    with state.lock:
        app_status = state.status
        active_part = state.p_no
        qty_progress = f"{state.target_qty - state.qty}/{state.target_qty}" if state.target_qty > 0 else "-"
        inspection_mode = getattr(state, "inspection_mode", "AI")

    is_healthy = (db_status == "CONNECTED") and not is_disk_low
    overall_status = "HEALTHY" if is_healthy else ("DEGRADED" if not is_disk_low else "DISK_SPACE_LOW")

    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "uptime": {
            "seconds": uptime_sec,
            "human": get_uptime_string(uptime_sec)
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
            "local_ip": get_local_ip(),
            "port": 8000
        }
    }

@router.get("/status")
def get_system_status():
    """Endpoint status cepat untuk memantau status inspeksi yang sedang berjalan."""
    with state.lock:
        return {
            "status": state.status,
            "id_trans": state.id_trans,
            "p_no": state.p_no,
            "qty_remaining": state.qty,
            "target_qty": state.target_qty,
            "current_side": state.current_side,
            "mode": getattr(state, "inspection_mode", "AI"),
            "operator": state.operator_name
        }

@router.post("/admin-login")
def admin_login(creds: LoginSchema, request: Request, db: Session = Depends(get_db)):
    """Otentikasi Web Admin dengan proteksi Brute-Force Rate Limiter & Token Signing."""
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip)

    user = db.query(User).filter(User.username == creds.username).first()
    if not user or not verify_password(creds.password, user.password):
        record_failed_attempt(client_ip)
        raise HTTPException(status_code=401, detail="Username atau PIN salah!")
    if not getattr(user, 'is_active', True) or user.role not in ["pengawas", "operator", "admin"]:
        record_failed_attempt(client_ip)
        raise HTTPException(status_code=403, detail="Akun tidak berwenang mengakses Dashboard!")
    
    clear_failed_attempts(client_ip)
    token = create_admin_token(user.username, user.role)
    log_audit_event(db, user.username, "LOGIN", f"Berhasil masuk sebagai {user.role.upper()} (IP: {client_ip})")
    return {"token": token, "role": user.role, "username": user.username}

@router.post("/logout")
def admin_logout_root(db: Session = Depends(get_db), auth: dict = Depends(verify_admin_auth)):
    username = auth.get("u", "ADMIN")
    log_audit_event(db, username, "LOGOUT", "User keluar dari Dashboard")
    return {"success": True}

@router.post("/admin/logout")
def admin_logout_admin(db: Session = Depends(get_db), auth: dict = Depends(verify_admin_auth)):
    username = auth.get("u", "ADMIN")
    log_audit_event(db, username, "LOGOUT", "User keluar dari Dashboard")
    return {"success": True}
