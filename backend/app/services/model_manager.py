"""In-memory model manager for caching segmentation neural networks."""

import os
import sys
import torch
import segmentation_models_pytorch as smp
from typing import Tuple, Dict, Any, Optional

# Ensure project root is in sys.path to import inference functions
from backend.app.config import settings

if settings.PROJECT_ROOT not in sys.path:
    sys.path.insert(0, settings.PROJECT_ROOT)

from inference import load_model


class ModelManager:
    """Singleton model cache to avoid reloading PyTorch weights per HTTP request."""

    _instance: Optional['ModelManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.device = torch.device(settings.DEVICE)
        self.road_model = None
        self.road_is_logits = True
        self.road_weights_path = None
        self.building_model = None
        self.building_is_logits = False
        self.building_weights_path = None
        self.preprocessing_fn = smp.encoders.get_preprocessing_fn("efficientnet-b7", "imagenet")
        self.error_log = []
        self._initialized = True

    def load_all_models(self):
        """Preload both road and building models into memory."""
        print(f"[ModelManager] Initializing models on device: {self.device}...")

        # 1. Road model
        road_path = settings.ROAD_WEIGHTS_PATH
        if not os.path.exists(road_path) and os.path.exists(settings.FALLBACK_ROAD_WEIGHTS):
            road_path = settings.FALLBACK_ROAD_WEIGHTS

        if os.path.exists(road_path):
            try:
                print(f"[ModelManager] Loading Road model from {road_path}")
                self.road_model, self.road_is_logits = load_model(road_path, self.device)
                self.road_weights_path = road_path
                print(f"[ModelManager] Road model loaded successfully.")
            except Exception as e:
                err = f"Failed loading road model: {str(e)}"
                print(f"[ModelManager] ERROR: {err}")
                self.error_log.append(err)
        else:
            self.error_log.append(f"Road weights not found at {road_path}")

        # 2. Building model
        building_path = settings.BUILDING_WEIGHTS_PATH
        if os.path.exists(building_path):
            try:
                print(f"[ModelManager] Loading Building model from {building_path}")
                self.building_model, self.building_is_logits = load_model(building_path, self.device)
                self.building_weights_path = building_path
                print(f"[ModelManager] Building model loaded successfully.")
            except Exception as e:
                err = f"Failed loading building model: {str(e)}"
                print(f"[ModelManager] ERROR: {err}")
                self.error_log.append(err)
        else:
            self.error_log.append(f"Building weights not found at {building_path}")

    def get_model(self, task: str) -> Tuple[Any, bool, Any]:
        """Get model, is_logits flag, and preprocessing function for given task."""
        task = task.lower()
        if task == "road":
            if self.road_model is None:
                raise RuntimeError("Road model is not loaded. Check server logs.")
            return self.road_model, self.road_is_logits, self.preprocessing_fn
        elif task == "building":
            if self.building_model is None:
                raise RuntimeError("Building model is not loaded. Check server logs.")
            return self.building_model, self.building_is_logits, self.preprocessing_fn
        else:
            raise ValueError(f"Unknown task '{task}'. Expected 'road' or 'building'.")

    def get_status(self) -> Dict[str, Any]:
        """Return readiness and memory status."""
        cuda_info = {}
        if torch.cuda.is_available():
            cuda_info = {
                "cuda_device_name": torch.cuda.get_device_name(0),
                "allocated_memory_mb": round(torch.cuda.memory_allocated(0) / (1024 * 1024), 1),
                "reserved_memory_mb": round(torch.cuda.memory_reserved(0) / (1024 * 1024), 1),
            }

        return {
            "status": "ready" if (self.road_model or self.building_model) else "degraded",
            "device": str(self.device),
            "road_model_loaded": self.road_model is not None,
            "road_weights": self.road_weights_path,
            "building_model_loaded": self.building_model is not None,
            "building_weights": self.building_weights_path,
            "cuda": cuda_info,
            "errors": self.error_log,
        }


model_manager = ModelManager()
