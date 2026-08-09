import subprocess
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, CameraConfig, log_audit_event
from api.auth import get_current_user_name

router = APIRouter()

class CameraConfigCreate(BaseModel):
    name: str
    source: str

class CameraConfigUpdate(BaseModel):
    name: str
    source: str

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
    db.query(CameraConfig).update({CameraConfig.is_active: False})
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

    if was_active:
        remaining_cam = db.query(CameraConfig).first()
        if remaining_cam:
            remaining_cam.is_active = True
            db.commit()
            log_audit_event(db, uname, "AUTO_ACTIVATE_CAMERA", f"Otomatis mengaktifkan {remaining_cam.name} setelah kamera aktif dihapus")

    log_audit_event(db, uname, "DELETE_CAMERA", f"Menghapus kamera {cam_name} (ID: #{cam_id})")
    return {"status": "ok", "was_active": was_active}
