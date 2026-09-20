"""FastAPI entry point for Aerial Road and Building Segmentation API."""

import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from backend.app.config import settings
from backend.app.services.model_manager import model_manager
from backend.app.api.endpoints import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: Pre-loads PyTorch models into GPU/CPU memory on server startup."""
    print("=" * 60)
    print("[SERVER] Starting Aerial Road & Building Segmentation Backend API")
    print(f"[SERVER] Device configured: {settings.DEVICE}")
    print("=" * 60)

    # Preload models
    model_manager.load_all_models()

    yield

    print("[SERVER] Shutting down segmentation server...")


app = FastAPI(
    title="Aerial Road & Building Segmentation API",
    description="REST API for deep semantic segmentation of aerial imagery using EfficientNet-B7 + UNet.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Enable CORS for frontend applications (local, docker, production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directories exist and mount
os.makedirs(settings.SAMPLES_DIR, exist_ok=True)
static_root = os.path.join(settings.PROJECT_ROOT, "backend", "static")
os.makedirs(static_root, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_root), name="static")

# Mount API routes
app.include_router(api_router)


@app.get("/", include_in_schema=False)
def root_redirect():
    """Redirect root path to interactive Swagger documentation."""
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
