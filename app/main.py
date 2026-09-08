import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import ROOT_DIR, get_settings
from app.routes import admin, chat, pages
from app.services.health_service import health_status

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0")
app.mount("/static", StaticFiles(directory=str(ROOT_DIR / "app" / "static")), name="static")
app.include_router(pages.router)
app.include_router(chat.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    payload, status_code = health_status()
    return JSONResponse(payload, status_code=status_code)
