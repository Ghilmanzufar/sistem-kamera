from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, SisonConfig, log_audit_event
from api.auth import get_current_user_name
from integrations import SisonSender
from .auth_routes import get_local_ip

router = APIRouter()

class SisonConfigUpdate(BaseModel):
    callback_url: str
    api_key: str

class SisonTestPingRequest(BaseModel):
    callback_url: str

def get_or_create_sison_config(db: Session) -> SisonConfig:
    cfg = db.query(SisonConfig).first()
    if not cfg:
        cfg = SisonConfig()
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg

@router.get("/sison-config")
def get_sison_config(db: Session = Depends(get_db)):
    cfg = get_or_create_sison_config(db)
    return {
        "callback_url": cfg.callback_url,
        "api_key": cfg.api_key,
        "server_ip": get_local_ip(),
        "server_port": 8000
    }

@router.put("/sison-config")
def update_sison_config(data: SisonConfigUpdate, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    cfg = get_or_create_sison_config(db)
    cfg.callback_url = data.callback_url
    cfg.api_key = data.api_key
    db.commit()
    log_audit_event(db, uname, "UPDATE_SISON_CONFIG", f"Mengubah konfigurasi Sison Callback ke {data.callback_url}")
    return {"success": True, "message": "Konfigurasi Sison berhasil disimpan"}

@router.post("/sison-test-ping")
def test_sison_ping(req: SisonTestPingRequest):
    """Uji konektivitas webhook ke endpoint server SISON."""
    if not req.callback_url or not req.callback_url.startswith("http"):
        raise HTTPException(status_code=400, detail="URL Webhook tidak valid (harus diawali http:// atau https://)")
    res = SisonSender.test_ping(req.callback_url)
    return res
