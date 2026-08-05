from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database_config import get_db, PartRule, User, InspectionLog, Transaction, CameraConfig, SisonConfig, GlobalSettings, hash_password, verify_password
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from collections import defaultdict
import os
import shutil
import tempfile
from typing import Optional
from datetime import datetime

admin_security = HTTPBearer()
import secrets

def verify_admin_auth(credentials: HTTPAuthorizationCredentials = Depends(admin_security)):
    """👱 Ponytail: Proteksi endpoint admin dari akses tanpa token (curl/unauthorized) dengan constant-time comparison."""
    secret = os.getenv("SECRET_KEY", "sugity_super_secret_key_2026")
    if not secrets.compare_digest(credentials.credentials, secret):
        raise HTTPException(status_code=401, detail="Token Admin Tidak Valid / Ditolak")

router = APIRouter(dependencies=[Depends(verify_admin_auth)])
public_router = APIRouter()

class LoginSchema(BaseModel):
    username: str
    password: str

@public_router.post("/admin-login")
def admin_login(creds: LoginSchema, db: Session = Depends(get_db)):
    """👱 Ponytail: Endpoint otentikasi admin untuk antarmuka Web Dashboard."""
    user = db.query(User).filter(User.username == creds.username).first()
    if not user or not verify_password(creds.password, user.password):
        raise HTTPException(status_code=401, detail="Username atau PIN salah!")
    if not getattr(user, 'is_active', True) or user.role not in ["admin", "pengawas"]:
        raise HTTPException(status_code=403, detail="Akun tidak berwenang mengakses Dashboard!")
    secret = os.getenv("SECRET_KEY", "sugity_super_secret_key_2026")
    return {"token": secret, "role": user.role, "username": user.username}

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
            
    # Default jika tidak ada filter: 50 terbaru
    trans = query.order_by(Transaction.start_time.desc()).limit(50).all()
    return trans

@router.get("/ng-logs")
def get_ng_logs(date_filter: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(InspectionLog).filter(InspectionLog.detection_status == 'NG')
    
    if date_filter:
        try:
            f_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            start_date = datetime(f_date.year, f_date.month, f_date.day, 0, 0, 0)
            end_date = datetime(f_date.year, f_date.month, f_date.day, 23, 59, 59)
            query = query.filter(InspectionLog.created_at >= start_date, InspectionLog.created_at <= end_date)
        except ValueError:
            pass
            
    return query.order_by(InspectionLog.created_at.desc()).limit(100).all()

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
def save_rule(rule_data: PartRuleSchema, db: Session = Depends(get_db)):
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
        return {"success": True, "message": "Rule saved successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/rules/{p_no}")
def delete_rule(p_no: str, db: Session = Depends(get_db)):
    deleted_count = db.query(PartRule).filter(PartRule.p_no == p_no).delete()
    if deleted_count > 0:
        db.commit()
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
    return {
        "default_avg_conf": gs.default_avg_conf,
        "default_min_conf": gs.default_min_conf,
        "default_min_coverage": gs.default_min_coverage
    }

@router.post("/global-rule")
def update_global_rule(data: GlobalRuleSchema, db: Session = Depends(get_db)):
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
    return {"success": True, "message": "Global rule disimpan dan diaplikasikan ke semua part."}

# --- MODELS API ---
WEIGHTS_DIR = os.path.join(os.getcwd(), "weights")

@router.get("/models")
def get_models():
    if not os.path.exists(WEIGHTS_DIR):
        os.makedirs(WEIGHTS_DIR)
    
    models = []
    for filename in os.listdir(WEIGHTS_DIR):
        if filename.endswith(".pt"):
            part_no = filename[:-3] # hapus .pt
            file_path = os.path.join(WEIGHTS_DIR, filename)
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            models.append({
                "part_no": part_no,
                "filename": filename,
                "size_mb": round(size_mb, 2)
            })
    return models

@router.post("/models")
def upload_model(part_no: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
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
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(username=user.username, password=hash_password(user.password), role=user.role, fullname=user.fullname, is_active=user.is_active)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.put("/users/{user_id}")
def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db)):
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
    return db_user

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return {"status": "ok"}

@router.put("/models/{part_no}")
def rename_model(part_no: str, data: RenameModelSchema):
    old_path = os.path.join(WEIGHTS_DIR, f"{part_no}.pt")
    new_path = os.path.join(WEIGHTS_DIR, f"{data.new_part_no}.pt")
    
    if not os.path.exists(old_path):
        raise HTTPException(status_code=404, detail="Model not found")
        
    if os.path.exists(new_path):
        raise HTTPException(status_code=400, detail="A model with the new name already exists")
        
    os.rename(old_path, new_path)
    return {"success": True, "message": "Model renamed successfully"}

@router.delete("/models/{part_no}")
def delete_model(part_no: str):
    file_path = os.path.join(WEIGHTS_DIR, f"{part_no}.pt")
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"success": True, "message": "Model deleted"}
    raise HTTPException(status_code=404, detail="Model not found")

# --- CAMERA API ---
@router.get("/cameras")
def get_cameras(db: Session = Depends(get_db)):
    return db.query(CameraConfig).all()

@router.post("/cameras")
def create_camera(cam: CameraConfigCreate, db: Session = Depends(get_db)):
    db_cam = CameraConfig(name=cam.name, source=cam.source, is_active=False)
    db.add(db_cam)
    db.commit()
    db.refresh(db_cam)
    return db_cam

@router.put("/cameras/{cam_id}/activate")
def activate_camera(cam_id: int, db: Session = Depends(get_db)):
    # Deactivate all
    db.query(CameraConfig).update({CameraConfig.is_active: False})
    # Activate selected
    db_cam = db.query(CameraConfig).filter(CameraConfig.id == cam_id).first()
    if not db_cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    db_cam.is_active = True
    db.commit()
    return {"status": "ok", "message": f"Camera {db_cam.name} activated"}

@router.delete("/cameras/{cam_id}")
def delete_camera(cam_id: int, db: Session = Depends(get_db)):
    db_cam = db.query(CameraConfig).filter(CameraConfig.id == cam_id).first()
    if not db_cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    db.delete(db_cam)
    db.commit()
    return {"status": "ok"}


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
def update_sison_config(data: SisonConfigUpdate, db: Session = Depends(get_db)):
    cfg = _get_or_create_sison_config(db)
    cfg.callback_url = data.callback_url
    cfg.api_key = data.api_key
    db.commit()
    return {"success": True, "message": "Konfigurasi Sison berhasil disimpan"}
