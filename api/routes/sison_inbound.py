from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from core import state
from database import get_db, PartRule, Transaction, SessionLocal, SisonConfig

router = APIRouter()
security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validasi Bearer token dari Sison terhadap api_key di tabel SisonConfig."""
    db = SessionLocal()
    try:
        cfg = db.query(SisonConfig).first()
        valid_key = cfg.api_key if cfg else "kamera-secret-key"
        if credentials.credentials != valid_key:
            raise HTTPException(status_code=401, detail="API Key dari Sison tidak valid / Ditolak")
    finally:
        db.close()

class StartRequest(BaseModel):
    id_trans: str
    p_no: str
    lot: Optional[str] = "-"
    unique_no: Optional[str] = "-"
    p_name: Optional[str] = "-"
    qty: Optional[int] = 1

class OverrideRequest(BaseModel):
    pin: str

@router.post("/start")
def api_start(req: StartRequest, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    id_trans = (req.id_trans or "").strip()
    p_no = (req.p_no or "").strip()
    if not id_trans:
        raise HTTPException(status_code=400, detail="Field 'id_trans' wajib diisi (Tidak boleh kosong)!")
    if not p_no:
        raise HTTPException(status_code=400, detail="Field 'p_no' (Part Number) wajib diisi!")

    qty = max(1, int(req.qty or 1))
    lot = (req.lot or "-").strip() or "-"
    unique_no = (req.unique_no or "-").strip() or "-"
    p_name = (req.p_name or "-").strip() or "-"

    existing_trans = db.query(Transaction).filter(Transaction.id_trans == id_trans).first()
    if existing_trans:
        existing_trans.target_qty = qty
        existing_trans.qty_actual = 0
        existing_trans.status = 2  # 2 = PROSES / RUNNING
        existing_trans.start_time = func.now()
    else:
        new_trans = Transaction(
            id_trans=id_trans,
            part_no=p_no,
            part_name=p_name,
            lot_no=lot,
            unique_no=unique_no,
            target_qty=qty,
            qty_actual=0,
            status=2,
            start_time=func.now()
        )
        db.add(new_trans)
    db.commit()

    rules_rows = db.query(PartRule).filter(PartRule.p_no == req.p_no).all()
    aturan = []
    sisi_set = set()
    for r in rules_rows:
        aturan.append({
            "sisi": r.sisi, 
            "nama_komponen": r.nama_komponen.strip().lower(), 
            "qty": r.qty,
            "min_confidence": r.min_confidence if r.min_confidence is not None else 0.70,
            "avg_confidence": r.avg_confidence if r.avg_confidence is not None else 0.75,
            "min_coverage": getattr(r, 'min_coverage', 1.0) if getattr(r, 'min_coverage', None) is not None else 1.0
        })
        sisi_set.add(r.sisi)

    daftar_sisi = []
    if "Depan" in sisi_set: daftar_sisi.append("Depan")
    if "Belakang" in sisi_set: daftar_sisi.append("Belakang")
    for s in sisi_set:
        if s not in daftar_sisi: daftar_sisi.append(s)

    with state.lock:
        state.id_trans = req.id_trans
        state.p_no = req.p_no
        state.qty = req.qty
        state.target_qty = req.qty
        state.aturan_sisi = aturan
        state.daftar_sisi = daftar_sisi
        state.progress_sisi = 0
        state.status = "RUNNING"
    return {"success": True, "message": "Kamera menerima perintah mulai"}
