import subprocess
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, CameraConfig, log_audit_event
from api.auth import get_current_user_name

router = APIRouter()

class CameraSchema(BaseModel):
    name: str
    source: str
    is_active: Optional[bool] = False

@router.get("/cameras")
def get_cameras(db: Session = Depends(get_db)):
    return db.query(CameraConfig).all()

@router.post("/cameras")
def add_camera(cam: CameraSchema, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    db_cam = CameraConfig(name=cam.name, source=cam.source, is_active=cam.is_active)
    db.add(db_cam)
    db.commit()
    db.refresh(db_cam)
    log_audit_event(db, uname, "ADD_CAMERA", f"Menambahkan kamera: {cam.name} (Source: {cam.source})")
    return db_cam

@router.post("/cameras/{cam_id}/set-active")
def set_active_camera(cam_id: int, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    target = db.query(CameraConfig).filter(CameraConfig.id == cam_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Camera config not found")
    db.query(CameraConfig).update({CameraConfig.is_active: False})
    target.is_active = True
    db.commit()
    log_audit_event(db, uname, "SET_ACTIVE_CAMERA", f"Mengaktifkan kamera: {target.name} (Source: {target.source})")
    return {"message": f"Kamera {target.name} diatur sebagai aktif", "camera": target}

@router.post("/cameras/{cam_id}/toggle-power")
def toggle_camera_power(cam_id: int, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    target = db.query(CameraConfig).filter(CameraConfig.id == cam_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Camera config not found")
    new_state = not target.is_active
    target.is_active = new_state
    db.commit()
    action_text = "Menyalakan (POWER ON)" if new_state else "Mematikan (POWER OFF)"
    log_audit_event(db, uname, "TOGGLE_CAMERA_POWER", f"{action_text} kamera: {target.name}")
    return {"message": f"Kamera {target.name} berhasil di-{action_text.lower()}", "is_active": new_state}

@router.delete("/cameras/{cam_id}")
def delete_camera(cam_id: int, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    target = db.query(CameraConfig).filter(CameraConfig.id == cam_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Camera not found")
    cam_name = target.name
    db.delete(target)
    db.commit()
    log_audit_event(db, uname, "DELETE_CAMERA", f"Menghapus kamera: {cam_name}")
    return {"message": f"Kamera {cam_name} berhasil dihapus"}

@router.post("/cameras/scan-hardware")
def scan_hardware_cameras(db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    """Memindai perangkat kamera USB yang terhubung secara fisik ke sistem."""
    try:
        cmd = ['powershell', '-NoProfile', '-Command', 'Get-PnpDevice -Class Camera, Image -Status OK | Select-Object -ExpandProperty FriendlyName']
        res = subprocess.check_output(cmd, timeout=5).decode(errors='ignore')
        lines = [line.strip() for line in res.splitlines() if line.strip()]
        
        added = []
        for idx, dev_name in enumerate(lines):
            existing = db.query(CameraConfig).filter(CameraConfig.name == dev_name).first()
            if not existing:
                db_cam = CameraConfig(name=dev_name, source=str(idx), is_active=False)
                db.add(db_cam)
                added.append(dev_name)
        db.commit()
        log_audit_event(db, uname, "SCAN_CAMERAS", f"Memindai hardware: {len(lines)} terdeteksi, {len(added)} baru ditambahkan")
        return {"detected": lines, "added": added, "total": len(lines)}
    except Exception as e:
        return {"error": str(e), "detected": []}
