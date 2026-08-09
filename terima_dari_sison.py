"""
Backward-compatibility bridge for terima_dari_sison.
Fungsionalitas telah dimodularisasi ke dalam package `api.routes.sison_inbound`.
"""
from api.routes.sison_inbound import router as camera_router, StartRequest