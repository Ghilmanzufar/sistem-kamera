import os
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db, Transaction, InspectionLog, AuditLog, PartRule
from sqlalchemy.sql import func
from integrations import get_buffered_count

router = APIRouter()

@router.get("/dashboard-stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Mengambil metrik statistik harian dan bulanan untuk Live Dashboard."""
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # 1. Total Transaksi
    total_trans_today = db.query(Transaction).filter(Transaction.start_time >= today_start).count()
    total_trans_month = db.query(Transaction).filter(Transaction.start_time >= month_start).count()
    
    # 2. Total Inspeksi OK vs NG
    total_ok_today = db.query(InspectionLog).filter(InspectionLog.created_at >= today_start, InspectionLog.detection_status == "OK").count()
    total_ng_today = db.query(InspectionLog).filter(InspectionLog.created_at >= today_start, InspectionLog.detection_status == "NG").count()
    
    total_ok_month = db.query(InspectionLog).filter(InspectionLog.created_at >= month_start, InspectionLog.detection_status == "OK").count()
    total_ng_month = db.query(InspectionLog).filter(InspectionLog.created_at >= month_start, InspectionLog.detection_status == "NG").count()

    total_insp_today = total_ok_today + total_ng_today
    yield_rate_today = round((total_ok_today / total_insp_today * 100), 1) if total_insp_today > 0 else 100.0

    # 3. Transaksi Terbaru (5 item)
    recent_transactions = db.query(Transaction).order_by(Transaction.start_time.desc()).limit(5).all()
    
    # 4. Total Rules & Offline Buffer Count
    total_rules = db.query(func.count(func.distinct(PartRule.p_no))).scalar() or 0
    buffered_count = get_buffered_count()

    return {
        "today": {
            "total_transactions": total_trans_today,
            "total_inspections": total_insp_today,
            "total_ok": total_ok_today,
            "total_ng": total_ng_today,
            "yield_rate": yield_rate_today
        },
        "month": {
            "total_transactions": total_trans_month,
            "total_ok": total_ok_month,
            "total_ng": total_ng_month
        },
        "total_rules": total_rules,
        "buffered_offline_count": buffered_count,
        "recent_transactions": [
            {
                "id_trans": t.id_trans,
                "part_no": t.part_no,
                "part_name": t.part_name,
                "qty_actual": t.qty_actual,
                "target_qty": t.target_qty,
                "status": t.status,
                "start_time": t.start_time
            }
            for t in recent_transactions
        ]
    }

@router.get("/logs")
def get_audit_logs(db: Session = Depends(get_db)):
    """Mengambil rekam jejak audit log aktivitas user."""
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(200).all()
