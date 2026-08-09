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

@router.get("/rules")
def get_all_rules(db: Session = Depends(get_db)):
    rules = db.query(PartRule).all()
    grouped = defaultdict(lambda: {"avg_confidence": 0.75, "min_coverage": 1.0, "komponen": []})
    for r in rules:
        grouped[r.p_no]["avg_confidence"] = r.avg_confidence if r.avg_confidence is not None else 0.75
        grouped[r.p_no]["min_coverage"] = r.min_coverage if r.min_coverage is not None else 1.0
        grouped[r.p_no]["komponen"].append({
            "id": r.id,
            "sisi": r.sisi or "-",
            "nama_komponen": r.nama_komponen,
            "qty": r.qty,
            "min_confidence": r.min_confidence if r.min_confidence is not None else 0.70
        })
    return [{"p_no": k, "avg_confidence": v["avg_confidence"], "min_coverage": v["min_coverage"], "komponen": v["komponen"]} for k, v in grouped.items()]

@router.post("/rules")
def save_part_rule(rule_data: PartRuleSchema, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    db.query(PartRule).filter(PartRule.p_no == rule_data.p_no).delete()
    for comp in rule_data.komponen:
        new_comp = PartRule(
            p_no=rule_data.p_no,
            sisi=comp.sisi or "-",
            nama_komponen=comp.nama_komponen,
            qty=comp.qty,
            min_confidence=comp.min_confidence if comp.min_confidence is not None else 0.70,
            avg_confidence=rule_data.avg_confidence if rule_data.avg_confidence is not None else 0.75,
            min_coverage=rule_data.min_coverage if rule_data.min_coverage is not None else 1.0
        )
        db.add(new_comp)
    db.commit()
    log_audit_event(db, uname, "SAVE_RULE", f"Menyimpan aturan part {rule_data.p_no} ({len(rule_data.komponen)} komponen)")
    return {"message": "Rule saved successfully"}

@router.delete("/rules/{p_no}")
def delete_part_rule(p_no: str, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    deleted = db.query(PartRule).filter(PartRule.p_no == p_no).delete()
    db.commit()
    log_audit_event(db, uname, "DELETE_RULE", f"Menghapus seluruh aturan part: {p_no}")
    return {"message": f"Rule {p_no} deleted successfully", "deleted_components": deleted}

@router.get("/rules/global")
def get_global_settings(db: Session = Depends(get_db)):
    setting = db.query(GlobalSettings).first()
    if not setting:
        return {"default_avg_conf": 0.75, "default_min_conf": 0.70, "default_min_coverage": 1.0}
    return {
        "default_avg_conf": setting.default_avg_conf,
        "default_min_conf": setting.default_min_conf,
        "default_min_coverage": setting.default_min_coverage
    }

@router.post("/rules/global")
def save_global_settings(data: GlobalRuleSchema, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    setting = db.query(GlobalSettings).first()
    if not setting:
        setting = GlobalSettings()
        db.add(setting)
    setting.default_avg_conf = data.default_avg_conf
    setting.default_min_conf = data.default_min_conf
    setting.default_min_coverage = data.default_min_coverage
    db.commit()
    log_audit_event(db, uname, "SAVE_GLOBAL_RULES", f"Mengubah aturan global: Avg={data.default_avg_conf}, Min={data.default_min_conf}")
    return {"message": "Pengaturan aturan global berhasil disimpan"}
