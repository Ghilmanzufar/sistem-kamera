from fastapi import APIRouter, Depends
from api.auth import verify_admin_auth

from .sison_inbound import router as sison_inbound_router
from .auth_routes import router as auth_router
from .inspection_routes import router as inspection_router
from .camera_routes import router as camera_router
from .model_routes import router as model_router
from .rule_routes import router as rule_router
from .user_routes import router as user_router
from .sison_config_routes import router as sison_config_router
from .system_routes import router as system_router

# Router publik (tanpa token)
public_router = APIRouter()
public_router.include_router(auth_router)

# Router terproteksi admin (dengan dependency verify_admin_auth)
admin_protected_router = APIRouter(dependencies=[Depends(verify_admin_auth)])
admin_protected_router.include_router(auth_router) # Support POST /api/admin/logout
admin_protected_router.include_router(system_router) # /transactions, /audit-logs
admin_protected_router.include_router(inspection_router) # /inspection-logs
admin_protected_router.include_router(rule_router) # /rules, /global-rule
admin_protected_router.include_router(model_router) # /models, /models/{part_no}/*
admin_protected_router.include_router(user_router) # /users
admin_protected_router.include_router(camera_router) # /cameras, /cameras/scan, /cameras/{id}/*
admin_protected_router.include_router(sison_config_router) # /sison-config, /sison-test-ping

__all__ = [
    "sison_inbound_router",
    "public_router",
    "admin_protected_router"
]
