import time
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Import state dan database
import importlib
state = importlib.import_module("2_proses_kamera").state
from database_config import get_db, PartRule, Transaction
from sqlalchemy.sql import func

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
    # --- CATAT TRANSAKSI KE DATABASE ---
    existing_trans = db.query(Transaction).filter(Transaction.id_trans == req.id_trans).first()
    if existing_trans:
        existing_trans.target_qty = req.qty
        existing_trans.qty_actual = 0
        existing_trans.status = 1
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
            status=1,
            start_time=func.now()
        )
        db.add(new_trans)
    db.commit()

    # Query nyata ke database PostgreSQL (Satu tabel murni)
    rules_rows = db.query(PartRule).filter(PartRule.p_no == req.p_no).all()
    aturan = []
    sisi_set = set()
    for r in rules_rows:
        aturan.append({"sisi": r.sisi, "nama_komponen": r.nama_komponen, "qty": r.qty})
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

@router.post("/override")
def api_override(req: OverrideRequest):
    if req.pin == "1234":
        with state.lock:
            if state.status == "NG":
                state.status = "RUNNING"
                state.cooldown_until = time.time() + 2.0
        return {"success": True, "message": "Override berhasil"}
    return {"success": False, "message": "PIN Salah!"}
