from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db, Transaction, AuditLog, log_audit_event
from api.auth import get_current_user_name

router = APIRouter()

@router.get("/transactions")
def get_transactions(date_filter: Optional[str] = None, db: Session = Depends(get_db)):
    """Mengambil 50 transaksi terbaru untuk Dashboard monitoring."""
    query = db.query(Transaction)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            start_date = datetime(filter_date.year, filter_date.month, filter_date.day, 0, 0, 0)
            end_date = datetime(filter_date.year, filter_date.month, filter_date.day, 23, 59, 59)
            query = query.filter(Transaction.start_time >= start_date, Transaction.start_time <= end_date)
            return query.order_by(Transaction.start_time.desc()).all()
        except ValueError:
            pass
            
    trans = query.order_by(Transaction.start_time.desc()).limit(50).all()
    return trans

@router.delete("/transactions/running")
def clear_running_transactions(db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    """Hapus seluruh transaksi berstatus RUNNING (status=2) dari database."""
    deleted_count = db.query(Transaction).filter(Transaction.status == 2).delete()
    db.commit()
    log_audit_event(db, uname, "DELETE_RUNNING_TRANS", f"Menghapus {deleted_count} transaksi ber-status RUNNING")
    return {"success": True, "count": deleted_count, "message": f"Berhasil menghapus {deleted_count} transaksi RUNNING."}

@router.get("/audit-logs")
def get_audit_logs(date_filter: Optional[str] = None, db: Session = Depends(get_db)):
    """Mengambil riwayat audit aktivitas user dan sistem."""
    query = db.query(AuditLog)
    if date_filter:
        try:
            f_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            start_date = datetime(f_date.year, f_date.month, f_date.day, 0, 0, 0)
            end_date = datetime(f_date.year, f_date.month, f_date.day, 23, 59, 59)
            query = query.filter(AuditLog.timestamp >= start_date, AuditLog.timestamp <= end_date)
        except ValueError:
            pass
    raw_logs = query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    result = []
    for log in raw_logs:
        ts_str = log.timestamp.isoformat() if log.timestamp else datetime.now().isoformat()
        result.append({
            "id": log.id,
            "timestamp": ts_str,
            "created_at": ts_str,
            "username": log.username or "SYSTEM",
            "action": log.action,
            "details": log.details or ""
        })
    return result
