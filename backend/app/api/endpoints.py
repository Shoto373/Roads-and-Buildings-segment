"""FastAPI endpoints for inference, metrics, health, and sample datasets."""

import os
import io
import json
import zipfile
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse, Response

from backend.app.config import settings
from backend.app.services.model_manager import model_manager
from backend.app.services.segmentation_service import segmentation_service

router = APIRouter(prefix="/api", tags=["Segmentation API"])


@router.get("/health")
def health_check():
    """System health check and model loading status."""
    return model_manager.get_status()


@router.get("/metrics/{task}")
def get_metrics(task: str):
    """Retrieve benchmark metrics on official test set."""
    task = task.lower()
    if task not in ("road", "building"):
        raise HTTPException(status_code=400, detail=f"Invalid task '{task}'. Expected 'road' or 'building'.")

    metrics_filename = f"{task}_test_metrics.json"
    metrics_path = os.path.join(settings.OUTPUTS_DIR, metrics_filename)

    if not os.path.exists(metrics_path):
        # Fallback metrics from benchmarks if json not yet generated
        fallback_data = {
            "road": {
                "task": "road",
                "n_test": 49,
                "metrics": {
                    "iou": 0.4872, "iou_std": 0.0603,
                    "dice": 0.6528, "dice_std": 0.0582,
                    "precision": 0.5704, "precision_std": 0.0492,
                    "recall": 0.7730, "recall_std": 0.0991,
                    "accuracy": 0.9626, "accuracy_std": 0.0209
                }
            },
            "building": {
                "task": "building",
                "n_test": 10,
                "metrics": {
                    "iou": 0.6039, "iou_std": 0.0351,
                    "dice": 0.7524, "dice_std": 0.0273,
                    "precision": 0.7908, "precision_std": 0.0268,
                    "recall": 0.7187, "recall_std": 0.0385,
                    "accuracy": 0.9143, "accuracy_std": 0.0340
                }
            }
        }
        return fallback_data[task]

    try:
        with open(metrics_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Filter per_image array to keep response compact unless explicitly requested
            summary = {
                "task": data.get("task", task),
                "weights": data.get("weights", "weights/default.pth"),
                "tta": data.get("tta", False),
                "n_test": data.get("n_test", 0),
                "metrics": data.get("metrics", {}),
            }
            return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read metrics: {str(e)}")


@router.post("/segment")
async def segment_image(
    file: UploadFile = File(..., description="Aerial image file (.png, .jpg, .tif)"),
    task: str = Form("road", description="Task type: 'road' or 'building'"),
    tta: bool = Form(False, description="Enable Test-Time Augmentation"),
    opacity: float = Form(0.55, description="Overlay opacity (0.0 to 1.0)"),
):
    """Run neural segmentation on an uploaded aerial photograph."""
    # 1. Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Allowed formats: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # 2. Read file content with size limit
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB} MB."
        )

    # 3. Validate task
    task = task.lower().strip()
    if task not in ("road", "building"):
        raise HTTPException(status_code=400, detail="Task must be either 'road' or 'building'.")

    # 4. Perform segmentation
    try:
        result = segmentation_service.run_segmentation(
            image_bytes=content,
            task=task,
            use_tta=tta,
            opacity=max(0.1, min(1.0, opacity)),
        )
        result["filename"] = file.filename
        return JSONResponse(content=result)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")


@router.get("/samples")
def get_sample_images():
    """List preset sample aerial images available for 1-click testing."""
    samples = [
        {
            "id": "sample-highway",
            "title": "Шоссе и развязка",
            "description": "Скоростная многополосная трасса и эстакада",
            "recommended_task": "road",
            "url": "/static/samples/sample_highway.jpg",
            "thumbnail": "/static/samples/sample_highway_thumb.jpg",
        },
        {
            "id": "sample-urban",
            "title": "Городской центр",
            "description": "Плотная ортогональная сеть улиц и кварталы",
            "recommended_task": "road",
            "url": "/static/samples/sample_urban.jpg",
            "thumbnail": "/static/samples/sample_urban_thumb.jpg",
        },
        {
            "id": "sample-suburb",
            "title": "Пригородный массив",
            "description": "Коттеджный поселок и малоэтажная застройка",
            "recommended_task": "building",
            "url": "/static/samples/sample_suburb.jpg",
            "thumbnail": "/static/samples/sample_suburb_thumb.jpg",
        },
        {
            "id": "sample-rural",
            "title": "Загородные трассы",
            "description": "Извилистая дорога через лесной и открытый массив",
            "recommended_task": "road",
            "url": "/static/samples/sample_rural.jpg",
            "thumbnail": "/static/samples/sample_rural_thumb.jpg",
        },
    ]
    return samples


@router.post("/segment/batch")
async def segment_batch(
    files: List[UploadFile] = File(..., description="Multiple aerial images"),
    task: str = Form("road"),
    tta: bool = Form(False),
):
    """Batch process multiple images and return a ZIP archive with masks and overlays."""
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 images allowed per batch.")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file in files:
            content = await file.read()
            try:
                result = segmentation_service.run_segmentation(
                    image_bytes=content,
                    task=task,
                    use_tta=tta,
                )
                base_name = os.path.splitext(file.filename)[0]

                # Extract raw png bytes from base64
                import base64
                mask_bytes = base64.b64decode(result["images"]["mask"].split(",")[1])
                overlay_bytes = base64.b64decode(result["images"]["overlay"].split(",")[1])

                zip_file.writestr(f"{base_name}_mask.png", mask_bytes)
                zip_file.writestr(f"{base_name}_overlay.png", overlay_bytes)
            except Exception as e:
                print(f"Error processing {file.filename}: {e}")

    zip_buffer.seek(0)
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={task}_segmentation_batch.zip"}
    )
