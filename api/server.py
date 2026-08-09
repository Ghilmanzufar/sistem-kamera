import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import FileResponse
import uvicorn

from .routes import sison_inbound_router, public_router, admin_protected_router

class SPAStaticFiles(StaticFiles):
    """Custom StaticFiles yang mengalihkan 404 Not Found ke index.html (SPA Fallback)."""
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as ex:
            if ex.status_code == 404 and self.html:
                index_path = os.path.join(self.directory, "index.html")
                if os.path.exists(index_path):
                    return FileResponse(index_path)
            raise ex

def create_app() -> FastAPI:
    """FastAPI Application Factory."""
    app = FastAPI(title="Sistem Kamera Inspeksi AI", version="2.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 1. Rute Inbound SISON (/api/start)
    app.include_router(sison_inbound_router, prefix="/api")

    # 2. Rute Publik (/api/health, /api/admin-login)
    app.include_router(public_router, prefix="/api")

    # 3. Rute Admin Terproteksi (/api/admin/*)
    app.include_router(admin_protected_router, prefix="/api/admin")

    # 4. Mount Static Files
    os.makedirs("web_admin/dist", exist_ok=True)
    os.makedirs("ng_records", exist_ok=True)
    
    app.mount("/admin", SPAStaticFiles(directory="web_admin/dist", html=True), name="admin")
    app.mount("/ng_records", StaticFiles(directory="ng_records"), name="ng_records")

    return app

app_fastapi = create_app()

def run_fastapi(host: str = "0.0.0.0", port: int = 8000):
    """Jalankan uvicorn server di background thread."""
    uvicorn.run(app_fastapi, host=host, port=port, log_level="error")
