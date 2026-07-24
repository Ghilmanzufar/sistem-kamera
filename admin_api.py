from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database_config import get_db, PartRule, User, InspectionLog, Transaction
from collections import defaultdict

router = APIRouter()

# --- SCHEMAS ---
class ComponentSchema(BaseModel):
    sisi: str
    nama_komponen: str
    qty: int

class PartRuleSchema(BaseModel):
    p_no: str
    komponen: list[ComponentSchema]

# --- MONITORING API ---
@router.get("/transactions")
def get_transactions(db: Session = Depends(get_db)):
    # Mengambil 50 transaksi terbaru
    trans = db.query(Transaction).order_by(Transaction.start_time.desc()).limit(50).all()
    return trans

# --- PART RULES API ---
@router.get("/rules")
def get_all_rules(db: Session = Depends(get_db)):
    rules_raw = db.query(PartRule).all()
    
    # Group by p_no
    grouped = defaultdict(list)
    for r in rules_raw:
        grouped[r.p_no].append({
            "sisi": r.sisi,
            "nama_komponen": r.nama_komponen,
            "qty": r.qty
        })
        
    result = []
    for p_no, comps in grouped.items():
        result.append({
            "p_no": p_no,
            "komponen": comps
        })
    return result

@router.post("/rules")
def save_rule(rule_data: PartRuleSchema, db: Session = Depends(get_db)):
    try:
        # Hapus semua komponen lama untuk p_no ini
        db.query(PartRule).filter(PartRule.p_no == rule_data.p_no).delete()
        db.flush()

        # Bulk insert komponen baru
        for c in rule_data.komponen:
            new_comp = PartRule(
                p_no=rule_data.p_no,
                sisi=c.sisi,
                nama_komponen=c.nama_komponen,
                qty=c.qty
            )
            db.add(new_comp)

        db.commit()
        return {"success": True, "message": "Rule saved successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/rules/{p_no}")
def delete_rule(p_no: str, db: Session = Depends(get_db)):
    deleted_count = db.query(PartRule).filter(PartRule.p_no == p_no).delete()
    if deleted_count > 0:
        db.commit()
        return {"success": True, "message": "Rule deleted"}
    raise HTTPException(status_code=404, detail="Rule not found")
