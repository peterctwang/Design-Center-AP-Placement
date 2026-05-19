"""FastAPI app — single entry point.

Serves:
  /api/*       REST endpoints
  /ws/*        WebSocket streams
  /uploads/*   Uploaded floor plan images (static)
  /            React SPA built into ./static
"""
import sys
from pathlib import Path

# Make `algorithms/` importable as a top-level package
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

from .config import settings
from .db import init_db
from .api import projects, walls, optimize, heatmap, report
from .ws import task_stream


app = FastAPI(title=settings.app_name, debug=settings.debug)

# CORS (open for local demo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(projects.router)
app.include_router(walls.router)
app.include_router(optimize.router)
app.include_router(heatmap.router)
app.include_router(report.router)
app.include_router(task_stream.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}


@app.on_event("startup")
def on_startup():
    logger.info(f"Starting {settings.app_name}")
    init_db()
    logger.info(f"DB ready: {settings.database_url}")


# Serve uploaded images so the React frontend can <img src> them directly.
app.mount("/uploads", StaticFiles(directory=settings.upload_dir),
          name="uploads")


# --- React SPA static files (catch-all, MUST be last) ---
# After `cd frontend && npm run build`, files live in backend/static/.
# If the build hasn't been run yet, we serve a minimal landing page.
if (settings.static_dir / "index.html").exists():
    app.mount("/", StaticFiles(directory=settings.static_dir,
                               html=True), name="static")
else:
    @app.get("/")
    def landing():
        return {
            "message": (
                "Frontend not built yet. Run "
                "`cd frontend && npm install && npm run build`."
            ),
            "api_docs": "/docs",
        }
