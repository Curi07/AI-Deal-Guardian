from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from app.api import deals
from app.db.init_db import init_db
from app.config import settings
import os
import logging
import sqlite3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Deal Guardian",
    description="AI-assisted decision-support tool for freelancers.",
    version="0.1.0",
)

@app.on_event("startup")
def startup_event():
    logger.info("Application starting up...")
    init_db()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."}
    )

app.include_router(deals.router, prefix="/api/deals", tags=["deals"])

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    return RedirectResponse(url="/static/index.html")

@app.get("/health")
def health_check():
    db_ok = True
    try:
        if not os.path.exists(settings.database_path):
            db_ok = False
        else:
            conn = sqlite3.connect(settings.database_path)
            conn.execute("SELECT 1 FROM deals LIMIT 1")
            conn.close()
    except Exception as e:
        logger.error(f"Health check DB error: {e}")
        db_ok = False

    if not db_ok:
        return JSONResponse(status_code=503, content={"status": "database_error"})
    return {"status": "ok"}
