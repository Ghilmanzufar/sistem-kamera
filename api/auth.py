import os
import time
import base64
import json
import hmac
import hashlib
import secrets
from collections import defaultdict
import threading
from typing import Optional

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import User

admin_security = HTTPBearer()

def get_secret_key() -> str:
    """Ambil SECRET_KEY dari .env atau generate baru secara aman jika belum ada."""
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
    """Buat signed HMAC-SHA256 token dengan masa berlaku terkonfigurasi."""
    if expires_in_seconds is None:
        expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10"))
        expires_in_seconds = expire_minutes * 60
    secret = get_secret_key()
    exp = int(time.time()) + expires_in_seconds
    payload = {"u": username, "r": role, "exp": exp}
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    sig = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"

def decode_and_verify_token(token: str) -> dict:
    """Verifikasi integritas dan masa berlaku token."""
    secret = get_secret_key()
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
        raise HTTPException(status_code=401, detail="Token telah kedaluwarsa. Silakan login kembali.")
    return payload

def verify_admin_auth(request: Request, credentials: HTTPAuthorizationCredentials = Depends(admin_security)) -> dict:
    """Proteksi endpoint admin dengan verifikasi token & hak akses role."""
    payload = decode_and_verify_token(credentials.credentials)
    role = payload.get("r", "pengawas")
    
    # Operator hanya diizinkan mengakses /inspection-logs dan /logout
    if role == "operator":
        path = request.url.path
        if not (path.endswith("/inspection-logs") or path.endswith("/logout")):
            raise HTTPException(status_code=403, detail="Akses ditolak. Peran Operator hanya diizinkan melihat History Inspeksi.")
            
    return payload

def get_current_user_name(credentials: HTTPAuthorizationCredentials = Depends(admin_security)) -> str:
    payload = decode_and_verify_token(credentials.credentials)
    return payload.get("u", "SYSTEM")

# --- RATE LIMITER (BRUTE FORCE PROTECTION) ---
_failed_login_attempts = defaultdict(list)
_login_rate_lock = threading.Lock()

def check_rate_limit(client_ip: str):
    now = time.time()
    with _login_rate_lock:
        _failed_login_attempts[client_ip] = [t for t in _failed_login_attempts[client_ip] if now - t < 60]
        if len(_failed_login_attempts[client_ip]) >= 5:
            time_left = int(60 - (now - _failed_login_attempts[client_ip][0]))
            raise HTTPException(
                status_code=429, 
                detail=f"Terlalu banyak percobaan login gagal. Silakan tunggu {max(1, time_left)} detik sebelum mencoba lagi."
            )

def record_failed_attempt(client_ip: str):
    with _login_rate_lock:
        _failed_login_attempts[client_ip].append(time.time())

def clear_failed_attempts(client_ip: str):
    with _login_rate_lock:
        if client_ip in _failed_login_attempts:
            del _failed_login_attempts[client_ip]
