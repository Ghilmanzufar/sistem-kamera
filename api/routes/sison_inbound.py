from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, SisonConfig, PartRule, Transaction
from core.state import state
from api.auth import admin_security
from fastapi.security import HTTPAuthorizationCredentials

router = APIRouter()

class StartRequest(BaseModel):
    id_trans: str
    lot: str
    p_no: str
    unique_no: str
    p_name: str
    qty: int

def verify_sison_key(credentials: HTTPAuthorizationCredentials = Depends(admin_security), db: Session = Depends(get_db)):
    """Verifikasi Bearer API Key yang dikirim oleh sistem SISON."""
    token = credentials.credentials
    cfg = db.query(SisonConfig).first()
    expected_key = cfg.api_key if cfg and cfg.api_key else "kamera-secret-key"
    if token != expected_key:
        raise HTTPException(status_code=401, detail="API Key Sison Tidak Valid!")
    return token

@router.post("/start")
def start_inspection(req: StartRequest, db: Session = Depends(get_db), auth: str = Depends(verify_sison_key)):
    """Endpoint yang dipanggil oleh SISON untuk memulai proses inspeksi part."""
    # Catat transaksi ke PostgreSQL
    trx = db.query(Transaction).filter(Transaction.id_trans == req.id_trans).first()
    if not trx:
        trx = Transaction(
            id_trans=req.id_trans,
            part_no=req.p_no,
            part_name=req.p_name,
            lot_no=req.lot,
            unique_no=req.unique_no,
            target_qty=req.qty,
            qty_actual=0,
            status=0
        )
        db.add(trx)
        db.commit()

    # Ambil aturan dari DB
    rules_db = db.query(PartRule).filter(PartRule.p_no == req.p_no).all()
    aturan = []
    sisi_set = []
    for r in rules_db:
        aturan.append({
            "sisi": r.sisi,
            "nama_komponen": r.nama_komponen,
            "qty": r.qty,
            "min_confidence": r.min_confidence if r.min_confidence is not None else 0.70,
            "avg_confidence": r.avg_confidence if r.avg_confidence is not None else 0.75,
            "min_coverage": r.min_coverage if r.min_coverage is not None else 1.0
        })
        if r.sisi and r.sisi != "-" and r.sisi not in sisi_set:
            sisi_set.append(r.sisi)

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
