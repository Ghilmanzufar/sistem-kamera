import time
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Import state dan database
from 2_proses_kamera import state
from database_config import get_db, PartRule

router = APIRouter()

# --- VALIDASI DATA MASUK (SCHEMAS) ---
class StartRequest(BaseModel):
    id_trans: str
    lot: str
    p_no: str
    unique_no: str
    p_name: str
    qty: int

class OverrideRequest(BaseModel):
    pin: str

# --- PINTU MASUK API (ROUTES) ---
@router.post("/start")
def api_start(req: StartRequest, db: Session = Depends(get_db)):
    # Query nyata ke database PostgreSQL
    rule = db.query(PartRule).filter(PartRule.p_no == req.p_no).first()
    aturan = rule.aturan_sisi if rule else []

    with state.lock:
        state.id_trans = req.id_trans
        state.p_no = req.p_no
        state.qty = req.qty
        state.target_qty = req.qty
        state.aturan_sisi = aturan
        state.progress_sisi = 0
        state.status = "RUNNING"
    return {"success": True, "message": "Kamera menerima perintah mulai"}

@router.post("/override")
def api_override(req: OverrideRequest):
    if req.pin == "1234":
        with state.lock:
            if state.status == "NG":
                state.status = "RUNNING"
                state.cooldown_until = time.time() + 2.0
        return {"success": True, "message": "Override berhasil"}
    return {"success": False, "message": "PIN Salah!"}
