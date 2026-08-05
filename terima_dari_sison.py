import time
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Import state dan database
from proses_kamera import state
from database_config import get_db, PartRule, Transaction, SessionLocal, SisonConfig
from sqlalchemy.sql import func

router = APIRouter()
security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """👱 Ponytail: Validasi Bearer token dari Sison terhadap api_key di tabel SisonConfig."""
    db = SessionLocal()
    try:
        cfg = db.query(SisonConfig).first()
        valid_key = cfg.api_key if cfg else "kamera-secret-key"
        if credentials.credentials != valid_key:
            raise HTTPException(status_code=401, detail="API Key dari Sison tidak valid / Ditolak")
    finally:
        db.close()


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
def api_start(req: StartRequest, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    # --- CATAT TRANSAKSI KE DATABASE ---
    existing_trans = db.query(Transaction).filter(Transaction.id_trans == req.id_trans).first()
    if existing_trans:
        existing_trans.target_qty = req.qty
        existing_trans.qty_actual = 0
        existing_trans.status = 2  # 👱 Ponytail: 2 = PROSES / RUNNING (sesuai spesifikasi workflow.md)
        existing_trans.start_time = func.now()
    else:
        new_trans = Transaction(
            id_trans=req.id_trans,
            part_no=req.p_no,
            part_name=req.p_name,
            lot_no=req.lot,
            unique_no=req.unique_no,
            target_qty=req.qty,
            qty_actual=0,
            status=2,  # 👱 Ponytail: 2 = PROSES / RUNNING
            start_time=func.now()
        )
        db.add(new_trans)
    db.commit()

    # Query nyata ke database PostgreSQL (Satu tabel murni)
    rules_rows = db.query(PartRule).filter(PartRule.p_no == req.p_no).all()
    aturan = []
    sisi_set = set()
    for r in rules_rows:
        # Normalize nama_komponen: lowercase+strip, konsisten dengan label model (model.names[cls].lower())
        aturan.append({
            "sisi": r.sisi, 
            "nama_komponen": r.nama_komponen.strip().lower(), 
            "qty": r.qty,
            "min_confidence": r.min_confidence,
            "avg_confidence": r.avg_confidence,
            "min_coverage": getattr(r, 'min_coverage', 1.0)
        })
        sisi_set.add(r.sisi)

    # Urutkan daftar sisi (Depan selalu dicek pertama jika ada)
    daftar_sisi = []
    if "Depan" in sisi_set: daftar_sisi.append("Depan")
    if "Belakang" in sisi_set: daftar_sisi.append("Belakang")
    # Tambahkan sisi lain jika ada (untuk masa depan)
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

