"""
Backward-compatibility bridge for admin_router.
Fungsionalitas telah dimodularisasi ke dalam package `api/`.
"""
from api.auth import (
    create_admin_token,
    decode_and_verify_token,
    verify_admin_auth,
    get_current_user_name,
    get_secret_key as _get_secret_key
)
from api.routes import public_router, admin_protected_router as router

__all__ = [
    "create_admin_token",
    "decode_and_verify_token",
    "verify_admin_auth",
    "get_current_user_name",
    "_get_secret_key",
    "public_router",
    "router"
]
