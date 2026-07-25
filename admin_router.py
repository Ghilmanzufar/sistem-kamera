from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database_config import get_db, PartRule, User, InspectionLog, Transaction, CameraConfig, SisonConfig
from collections import defaultdict
import os
import shutil
from typing import Optional
from datetime import datetime

router = APIRouter()

# --- SCHEMAS ---
class ComponentSchema(BaseModel):
    sisi: str
    nama_komponen: str
    qty: int

class PartRuleSchema(BaseModel):
    p_no: str
    komponen: list[ComponentSchema]

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

from typing import Optional
from datetime import datetime

@router.get("/ng-logs")
def get_ng_logs(date_filter: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(InspectionLog).filter(InspectionLog.detection_status == 'NG')
    
    if date_filter:
        try:
            # Parse date_filter (YYYY-MM-DD)
            filter_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            # SQLite DateTime can be filtered by casting to date using func.date()
            # Tapi SQLAlchemy func.date() kadang rewel di SQLite, cara paling aman:
            start_date = datetime(filter_date.year, filter_date.month, filter_date.day, 0, 0, 0)
            end_date = datetime(filter_date.year, filter_date.month, filter_date.day, 23, 59, 59)
            query = query.filter(InspectionLog.created_at >= start_date, InspectionLog.created_at <= end_date)
        except ValueError:
            pass # abaikan jika format salah
            
    logs = query.order_by(InspectionLog.created_at.desc()).limit(100).all()
    return logs

# --- PART RULES API ---
@router.get("/rules")
def get_all_rules(db: Session = Depends(get_db)):
    rules_raw = db.query(PartRule).all()
    
    # Group by p_no
    grouped = defaultdict(list)
    for r in rules_raw:
        grouped[r.p_no].append({
            "sisi": r.sisi,
            "nama_komponen": r.nama_komponen,
            "qty": r.qty
        })
        
    result = []
    for p_no, comps in grouped.items():
        result.append({
            "p_no": p_no,
            "komponen": comps
        })
    return result

@router.post("/rules")
def save_rule(rule_data: PartRuleSchema, db: Session = Depends(get_db)):
    try:
        # Hapus semua komponen lama untuk p_no ini
        db.query(PartRule).filter(PartRule.p_no == rule_data.p_no).delete()
        db.flush()

        # Bulk insert komponen baru
        for c in rule_data.komponen:
            new_comp = PartRule(
                p_no=rule_data.p_no,
                sisi=c.sisi,
                nama_komponen=c.nama_komponen,
                qty=c.qty
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
def upload_model(part_no: str = Form(...), file: UploadFile = File(...)):
    if not file.filename.endswith('.pt'):
        raise HTTPException(status_code=400, detail="Only .pt files are allowed")
    
    if not os.path.exists(WEIGHTS_DIR):
        os.makedirs(WEIGHTS_DIR)
        
    file_path = os.path.join(WEIGHTS_DIR, f"{part_no}.pt")
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"success": True, "message": f"Model for {part_no} uploaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- USERS API ---
@router.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()

@router.post("/users")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(username=user.username, password=user.password, role=user.role, fullname=user.fullname, is_active=user.is_active)
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
        db_user.password = user.password
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
