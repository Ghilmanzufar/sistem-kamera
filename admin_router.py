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

def create_admin_token(username: str, role: str, expires_in_seconds: int = 300) -> str:
    """👱 Ponytail Token Generator: Buat signed token dengan timestamp kedaluwarsa (Default 5 Menit)."""
    secret = os.getenv("SECRET_KEY", "sugity_super_secret_key_2026")
    exp = int(time.time()) + expires_in_seconds
    payload = {"u": username, "r": role, "exp": exp}
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    sig = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"

def decode_and_verify_token(token: str) -> dict:
    secret = os.getenv("SECRET_KEY", "sugity_super_secret_key_2026")
    parts = token.split(".")
    if len(parts) == 1 and secrets.compare_digest(token, secret):
        return {"u": "pengawas", "r": "pengawas", "exp": int(time.time()) + 300}
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
        raise HTTPException(status_code=401, detail="Token telah kedaluwarsa (Batas 5 Menit Habis). Silakan login kembali.")
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

class LoginSchema(BaseModel):
    username: str
    password: str

@public_router.post("/admin-login")
def admin_login(creds: LoginSchema, db: Session = Depends(get_db)):
    """👱 Ponytail: Endpoint otentikasi dengan Token Expiration 5 Menit."""
    user = db.query(User).filter(User.username == creds.username).first()
    if not user or not verify_password(creds.password, user.password):
        raise HTTPException(status_code=401, detail="Username atau PIN salah!")
    if not getattr(user, 'is_active', True) or user.role not in ["pengawas", "operator"]:
        raise HTTPException(status_code=403, detail="Akun tidak berwenang mengakses Dashboard!")
    
    token = create_admin_token(user.username, user.role, expires_in_seconds=300)
    log_audit_event(db, user.username, "LOGIN", f"Berhasil masuk sebagai {user.role.upper()}")
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
    for log, target_qty, qty_actual in logs_raw:
        result.append({
            "id": log.id,
            "created_at": log.created_at,
            "id_trans": log.id_trans,
            "part_no": log.part_no,
            "detection_status": log.detection_status,
            "confidence_score": log.confidence_score,
            "target_qty": target_qty if target_qty is not None else "-",
            "qty_actual": qty_actual if qty_actual is not None else "-"
        })
    return result

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

    models = []
    for filename in os.listdir(WEIGHTS_DIR):
        if filename.endswith(".pt"):
            part_no = filename[:-3] # hapus .pt
            file_path = os.path.join(WEIGHTS_DIR, filename)
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M')
            models.append({
                "part_no": part_no,
                "filename": filename,
                "size_mb": round(size_mb, 2),
                "last_modified": mtime,
                "is_active": (part_no.lower() == active_pno.lower()) if active_pno else False
            })
    return models

@router.get("/models/{part_no}/download")
def download_model(part_no: str):
    file_path = os.path.join(WEIGHTS_DIR, f"{part_no}.pt")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Model file not found")
    return FileResponse(file_path, filename=f"{part_no}.pt", media_type="application/octet-stream")

@router.get("/models/{part_no}/detail")
def get_model_detail(part_no: str, db: Session = Depends(get_db)):
    file_path = os.path.join(WEIGHTS_DIR, f"{part_no}.pt")
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
        "filename": f"{part_no}.pt",
        "size_mb": size_mb,
        "last_modified": mtime,
        "komponen_count": len(components),
        "komponen": components
    }

@router.post("/models")
def upload_model(part_no: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    if not file.filename.endswith('.pt'):
        raise HTTPException(status_code=400, detail="Only .pt files are allowed")
    
    if not os.path.exists(WEIGHTS_DIR):
        os.makedirs(WEIGHTS_DIR)
        
    file_path = os.path.join(WEIGHTS_DIR, f"{part_no}.pt")
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Auto-generate PartRule dari label .pt jika tersedia
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

        log_audit_event(db, uname, "UPLOAD_MODEL", f"Mengunggah model AI {part_no}.pt")
        return {"success": True, "message": f"Model for {part_no} uploaded and rules auto-generated!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/models/preview-labels")
async def preview_model_labels(file: UploadFile = File(...)):
    """Baca label names dari file .pt sementara — tidak disimpan permanen."""
    if not file.filename.endswith('.pt'):
        raise HTTPException(status_code=400, detail="Only .pt files are allowed")
    
    try:
        import torch
    except ImportError:
        raise HTTPException(status_code=500, detail="torch tidak terinstall di server")

    # Tulis ke tempfile, baca labels, lalu hapus
    tmp = tempfile.NamedTemporaryFile(suffix=".pt", delete=False)
    try:
        shutil.copyfileobj(file.file, tmp)
        tmp.close()

        ckpt = torch.load(tmp.name, map_location="cpu", weights_only=False)

        # YOLO menyimpan names di ckpt['model'].names  → {0: 'nama', 1: 'nama', ...}
        names = None
        if isinstance(ckpt, dict) and 'model' in ckpt:
            raw = getattr(ckpt['model'], 'names', None)
            if raw is not None:
                names = {str(k): v for k, v in raw.items()}
        
        if names is None:
            raise HTTPException(status_code=422, detail="Label names tidak ditemukan di file .pt ini. Pastikan file adalah model YOLO yang valid.")

        return {"label_count": len(names), "labels": names}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal membaca file .pt: {str(e)}")
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
    old_path = os.path.join(WEIGHTS_DIR, f"{part_no}.pt")
    new_path = os.path.join(WEIGHTS_DIR, f"{data.new_part_no}.pt")
    
    if not os.path.exists(old_path):
        raise HTTPException(status_code=404, detail="Model not found")
        
    if os.path.exists(new_path):
        raise HTTPException(status_code=400, detail="A model with the new name already exists")
        
    os.rename(old_path, new_path)
    log_audit_event(db, uname, "RENAME_MODEL", f"Mengubah nama model {part_no}.pt menjadi {data.new_part_no}.pt")
    return {"success": True, "message": "Model renamed successfully"}

@router.delete("/models/{part_no}")
def delete_model(part_no: str, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    file_path = os.path.join(WEIGHTS_DIR, f"{part_no}.pt")
    if os.path.exists(file_path):
        os.remove(file_path)
        log_audit_event(db, uname, "DELETE_MODEL", f"Menghapus file model {part_no}.pt")
        return {"success": True, "message": "Model deleted"}
    raise HTTPException(status_code=404, detail="Model not found")

# --- CAMERA API ---
import subprocess

def _scan_hardware_cameras(db: Session):
    """Pindai kamera hardware USB terhubung ke komputer dan sinkronkan dengan Database."""
    pnp_names = []
    try:
        cmd = 'powershell -NoProfile -Command "Get-PnpDevice -Class Camera, Image -Status OK | Select-Object -ExpandProperty FriendlyName"'
        res = subprocess.check_output(cmd, shell=True, timeout=5).decode(errors='ignore')
        pnp_names = [line.strip() for line in res.splitlines() if line.strip()]
    except Exception:
        pass

    existing_cams = db.query(CameraConfig).all()
    existing_sources = {c.source for c in existing_cams}
    
    new_added = False
    sources_to_check = pnp_names if pnp_names else ["Kamera USB Utama (Index 0)"]
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
        
    return db.query(CameraConfig).all()

@router.get("/cameras")
def get_cameras(db: Session = Depends(get_db)):
    cams = db.query(CameraConfig).all()
    if not cams:
        cams = _scan_hardware_cameras(db)
    return cams

@router.post("/cameras/scan")
def scan_cameras(db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    cams = _scan_hardware_cameras(db)
    log_audit_event(db, uname, "SCAN_CAMERAS", f"Memindai ulang kamera hardware. Total {len(cams)} kamera terdaftar.")
    return cams


@router.post("/cameras")
def create_camera(cam: CameraConfigCreate, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    db_cam = CameraConfig(name=cam.name, source=cam.source, is_active=False)
    db.add(db_cam)
    db.commit()
    db.refresh(db_cam)
    log_audit_event(db, uname, "CREATE_CAMERA", f"Menambah kamera {cam.name} (Source: {cam.source})")
    return db_cam

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
    return db_cam

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
class SisonConfigUpdate(BaseModel):
    callback_url: str
    api_key: str

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
    return {"callback_url": cfg.callback_url, "api_key": cfg.api_key}

@router.put("/sison-config")
def update_sison_config(data: SisonConfigUpdate, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    cfg = _get_or_create_sison_config(db)
    cfg.callback_url = data.callback_url
    cfg.api_key = data.api_key
    db.commit()
    log_audit_event(db, uname, "UPDATE_SISON_CONFIG", f"Mengubah konfigurasi Sison Callback ke {data.callback_url}")
    return {"success": True, "message": "Konfigurasi Sison berhasil disimpan"}
