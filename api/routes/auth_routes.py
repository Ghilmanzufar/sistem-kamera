import shutil
import time
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, User, verify_password, log_audit_event
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

@router.get("/health")
def health_check():
    """Health check dan informasi sisa kapasitas penyimpanan harddisk."""
    try:
        total, used, free = shutil.disk_usage(".")
        free_gb = round(free / (1024 ** 3), 2)
        total_gb = round(total / (1024 ** 3), 2)
        used_gb = round(used / (1024 ** 3), 2)
        free_pct = round((free / total) * 100, 1)
        used_pct = round((used / total) * 100, 1)
    except Exception:
        free_gb, total_gb, used_gb, free_pct, used_pct = 0, 0, 0, 0, 0

    return {
        "status": "healthy",
        "service": "kamera_inspection_backend",
        "uptime": _get_uptime_string(time.time() - SERVER_START_TIME),
        "disk_storage": {
            "free_gb": free_gb,
            "total_gb": total_gb,
            "used_gb": used_gb,
            "free_percent": free_pct,
            "used_percent": used_pct,
            "is_low_space_warning": free_pct < 10.0
        },
        "database": "connected",
        "network": {
            "host": "localhost",
            "port": 8000
        }
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

@router.post("/admin/logout")
def admin_logout(db: Session = Depends(get_db), auth: dict = Depends(verify_admin_auth)):
    """Catat aktivitas keluar (LOGOUT) dari Dashboard."""
    username = auth.get("u", "ADMIN")
    log_audit_event(db, username, "LOGOUT", "User keluar dari Dashboard")
    return {"success": True}
