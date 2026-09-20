"""Configuration for the FastAPI Aerial Segmentation backend."""

import os
import torch
from dataclasses import dataclass
from typing import List


@dataclass
class Settings:
    PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

    # Hardware device
    DEVICE: str = "cuda" if torch.cuda.is_available() else "cpu"

    # Input constraints
    MAX_FILE_SIZE_MB: int = 30
    MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024
    ALLOWED_EXTENSIONS: List[str] = (".png", ".jpg", ".jpeg", ".tif", ".tiff")

    # Weights paths
    ROAD_WEIGHTS_PATH: str = os.path.join(PROJECT_ROOT, "weights", "road_model_30_epochs.pth")
    FALLBACK_ROAD_WEIGHTS: str = os.path.join(PROJECT_ROOT, "weights", "best_road_model.pth")
    BUILDING_WEIGHTS_PATH: str = os.path.join(PROJECT_ROOT, "weights", "best_model.pth")

    # Directories
    OUTPUTS_DIR: str = os.path.join(PROJECT_ROOT, "outputs")
    SAMPLES_DIR: str = os.path.join(PROJECT_ROOT, "backend", "static", "samples")


settings = Settings()
