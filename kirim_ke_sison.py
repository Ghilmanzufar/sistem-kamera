"""
Backward-compatibility bridge for kirim_ke_sison.
Fungsionalitas telah dimodularisasi ke dalam package `integrations.sison_client`.
"""
from integrations.sison_client import SisonSender, get_callback_url

__all__ = ["SisonSender", "get_callback_url"]
