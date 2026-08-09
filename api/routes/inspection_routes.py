from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db, InspectionLog, Transaction, log_audit_event
from api.auth import verify_admin_auth

router = APIRouter()

@router.get("/inspection-logs")
def get_inspection_logs(
    date_filter: Optional[str] = None, 
    month_filter: Optional[str] = None,
    part_filter: Optional[str] = None, 
    status_filter: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    """Ambil riwayat log inspeksi kamera (OK & NG) dengan filter tanggal/bulan, part_no, dan status."""
    query = db.query(
        InspectionLog,
        Transaction.lot_no,
        Transaction.unique_no,
        Transaction.part_name,
        Transaction.target_qty,
        Transaction.qty_actual
    ).outerjoin(Transaction, InspectionLog.id_trans == Transaction.id_trans)
    
    if month_filter:
        try:
            f_month = datetime.strptime(month_filter, "%Y-%m").date()
            start_date = datetime(f_month.year, f_month.month, 1, 0, 0, 0)
            if f_month.month == 12:
                end_date = datetime(f_month.year + 1, 1, 1, 0, 0, 0) - timedelta(seconds=1)
            else:
                end_date = datetime(f_month.year, f_month.month + 1, 1, 0, 0, 0) - timedelta(seconds=1)
            query = query.filter(InspectionLog.created_at >= start_date, InspectionLog.created_at <= end_date)
        except ValueError:
            pass
    elif date_filter:
        try:
            f_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            start_date = datetime(f_date.year, f_date.month, f_date.day, 0, 0, 0)
            end_date = datetime(f_date.year, f_date.month, f_date.day, 23, 59, 59)
            query = query.filter(InspectionLog.created_at >= start_date, InspectionLog.created_at <= end_date)
        except ValueError:
            pass

    if part_filter and part_filter.strip():
        query = query.filter(InspectionLog.part_no.ilike(f"%{part_filter.strip()}%"))

    if status_filter and status_filter.strip() and status_filter != "ALL":
        query = query.filter(InspectionLog.detection_status == status_filter.strip())
            
    logs_raw = query.order_by(InspectionLog.created_at.desc()).limit(500).all()
    
    result = []
    for log, lot_no, unique_no, part_name, target_qty, qty_actual in logs_raw:
        result.append({
            "id": log.id,
            "created_at": log.created_at,
            "id_trans": log.id_trans,
            "part_no": log.part_no,
            "part_name": part_name or "-",
            "lot_no": lot_no or "-",
            "unique_no": unique_no or "-",
            "detection_status": log.detection_status,
            "confidence_score": log.confidence_score,
            "method": getattr(log, 'method', 'AI') or 'AI',
            "operator_name": getattr(log, 'operator_name', None) or "-",
            "target_qty": target_qty if target_qty is not None else "-",
            "qty_actual": qty_actual if qty_actual is not None else "-"
        })
    return result

@router.delete("/inspection-logs")
def clear_all_inspection_logs(db: Session = Depends(get_db), auth: dict = Depends(verify_admin_auth)):
    """Hapus seluruh riwayat log inspeksi dan catat di audit logs."""
    username = auth.get("u", "ADMIN")
    deleted_count = db.query(InspectionLog).delete()
    log_audit_event(db, username, "DELETE_ALL_INSPECTION_LOGS", f"Menghapus seluruh {deleted_count} data riwayat inspeksi")
    db.commit()
    return {"message": "Semua riwayat inspeksi berhasil dibersihkan", "deleted_count": deleted_count}
