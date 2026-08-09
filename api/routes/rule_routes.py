from typing import Optional
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, PartRule, GlobalSettings, log_audit_event
from api.auth import get_current_user_name

router = APIRouter()

class ComponentSchema(BaseModel):
    sisi: Optional[str] = "-"
    nama_komponen: str
    qty: Optional[int] = 1
    min_confidence: Optional[float] = 0.70

class PartRuleSchema(BaseModel):
    p_no: str
    avg_confidence: Optional[float] = 0.75
    min_coverage: Optional[float] = 1.0
    komponen: list[ComponentSchema]

class GlobalRuleSchema(BaseModel):
    default_avg_conf: float
    default_min_conf: float
    default_min_coverage: float

def get_or_create_global_settings(db: Session) -> GlobalSettings:
    gs = db.query(GlobalSettings).first()
    if not gs:
        gs = GlobalSettings()
        db.add(gs)
        db.commit()
        db.refresh(gs)
    return gs

@router.get("/rules")
def get_all_rules(db: Session = Depends(get_db)):
    rules_raw = db.query(PartRule).all()
    grouped = defaultdict(list)
    avg_conf_map = {}
    for r in rules_raw:
        min_c = getattr(r, 'min_confidence', 0.70)
        if min_c is None: min_c = 0.70
        avg_c = getattr(r, 'avg_confidence', 0.75)
        if avg_c is None: avg_c = 0.75
        min_cov = getattr(r, 'min_coverage', 1.0)
        if min_cov is None: min_cov = 1.0

        grouped[r.p_no].append({
            "sisi": r.sisi or "-",
            "nama_komponen": r.nama_komponen,
            "qty": r.qty or 1,
            "min_confidence": min_c
        })
        avg_conf_map[r.p_no] = avg_c
        
    result = []
    for p_no, comps in grouped.items():
        min_cov = 1.0
        if rules_raw:
            first_rule = next((x for x in rules_raw if x.p_no == p_no), None)
            if first_rule and getattr(first_rule, 'min_coverage', None) is not None:
                min_cov = first_rule.min_coverage

        result.append({
            "p_no": p_no,
            "avg_confidence": avg_conf_map.get(p_no, 0.75),
            "min_coverage": min_cov,
            "komponen": comps
        })
    return result

@router.post("/rules")
def save_rule(rule_data: PartRuleSchema, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    try:
        db.query(PartRule).filter(PartRule.p_no == rule_data.p_no).delete()
        db.flush()

        avg_c = rule_data.avg_confidence if rule_data.avg_confidence is not None else 0.75
        min_cov = rule_data.min_coverage if rule_data.min_coverage is not None else 1.0

        for c in rule_data.komponen:
            min_c = c.min_confidence if c.min_confidence is not None else 0.70
            new_comp = PartRule(
                p_no=rule_data.p_no,
                sisi=c.sisi or "-",
                nama_komponen=c.nama_komponen,
                qty=c.qty or 1,
                min_confidence=min_c,
                avg_confidence=avg_c,
                min_coverage=min_cov
            )
            db.add(new_comp)

        db.commit()
        log_audit_event(db, uname, "SAVE_RULE", f"Menyimpan rule part {rule_data.p_no} ({len(rule_data.komponen)} komponen)")
        return {"success": True, "message": "Rule saved successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/rules/{p_no}")
def delete_rule(p_no: str, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    deleted_count = db.query(PartRule).filter(PartRule.p_no == p_no).delete()
    if deleted_count > 0:
        db.commit()
        log_audit_event(db, uname, "DELETE_RULE", f"Menghapus rule part {p_no}")
        return {"success": True, "message": "Rule deleted"}
    raise HTTPException(status_code=404, detail="Rule not found")

@router.get("/global-rule")
def get_global_rule(db: Session = Depends(get_db)):
    gs = get_or_create_global_settings(db)
    total_parts = db.query(PartRule.p_no).distinct().count()
    return {
        "default_avg_conf": gs.default_avg_conf,
        "default_min_conf": gs.default_min_conf,
        "default_min_coverage": gs.default_min_coverage,
        "total_parts": total_parts
    }

@router.post("/global-rule")
def update_global_rule(data: GlobalRuleSchema, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    gs = get_or_create_global_settings(db)
    gs.default_avg_conf = data.default_avg_conf
    gs.default_min_conf = data.default_min_conf
    gs.default_min_coverage = data.default_min_coverage
    
    db.query(PartRule).update({
        PartRule.avg_confidence: data.default_avg_conf,
        PartRule.min_confidence: data.default_min_conf,
        PartRule.min_coverage: data.default_min_coverage
    })
    db.commit()
    log_audit_event(db, uname, "UPDATE_GLOBAL_RULE", f"Bulk update rule global (Avg: {data.default_avg_conf*100:.0f}%, MinConf: {data.default_min_conf*100:.0f}%, Coverage: {data.default_min_coverage*100:.0f}%)")
    return {"success": True, "message": "Global rule disimpan dan diaplikasikan ke semua part."}
