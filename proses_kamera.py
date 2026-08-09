"""
Backward-compatibility bridge for proses_kamera.
Fungsionalitas telah dimodularisasi ke dalam package `core/`.
"""
from core import *

# Re-export state instance explicitly
from core.state import state, SystemState
from core.detector import KameraProses, model_cache, log_inspeksi_db, log_ng_db
