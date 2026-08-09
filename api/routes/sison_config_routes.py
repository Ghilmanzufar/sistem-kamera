from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, SisonConfig, log_audit_event
from api.auth import get_current_user_name
from integrations import SisonSender

router = APIRouter()

class SisonConfigSchema(BaseModel):
    callback_url: str
    api_key: Optional[str] = "kamera-secret-key"

@router.get("/sison-config")
def get_sison_config(db: Session = Depends(get_db)):
    cfg = db.query(SisonConfig).first()
    if not cfg:
        cfg = SisonConfig(callback_url="http://localhost:3000/api/kamera/callback", api_key="kamera-secret-key")
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg

@router.put("/sison-config")
def update_sison_config(cfg_data: SisonConfigSchema, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    cfg = db.query(SisonConfig).first()
    if not cfg:
        cfg = SisonConfig()
        db.add(cfg)
    cfg.callback_url = cfg_data.callback_url
    if cfg_data.api_key:
        cfg.api_key = cfg_data.api_key
    db.commit()
    log_audit_event(db, uname, "UPDATE_SISON_CONFIG", f"Mengubah konfigurasi Sison Callback URL: {cfg_data.callback_url}")
    return {"message": "Sison config updated successfully", "config": cfg}

@router.post("/sison-config/test-ping")
def test_sison_ping(db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    """Menguji konektivitas webhook ke endpoint callback SISON."""
    cfg = db.query(SisonConfig).first()
    url = cfg.callback_url if cfg and cfg.callback_url else "http://localhost:3000/api/kamera/callback"
    result = SisonSender.test_ping(url)
    log_audit_event(db, uname, "TEST_SISON_PING", f"Tes koneksi ke {url}: Status {result.get('status_code', 'FAIL')} (Latency: {result.get('latency_ms')}ms)")
    return result
