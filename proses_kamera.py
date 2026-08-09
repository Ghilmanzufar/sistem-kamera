"""
Backward-compatibility bridge for proses_kamera.
Fungsionalitas telah dimodularisasi ke dalam package `core/`.
"""
from core import *
from core.state import state, SystemState
from core.detector import KameraProses, model_cache, log_inspeksi_db, log_ng_db
from core.rules import get_rules_for_side as _get_rules_for_side

__all__ = [
    "state",
    "SystemState",
    "KameraProses",
    "model_cache",
    "log_inspeksi_db",
    "log_ng_db",
    "_get_rules_for_side"
]
