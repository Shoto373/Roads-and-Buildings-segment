"""Segmentation service handling image transformation, inference, and visualization."""

import io
import time
import base64
import cv2
import numpy as np
import torch
from PIL import Image
from typing import Dict, Any, Optional, Tuple

from backend.app.config import settings
from backend.app.services.model_manager import model_manager
from inference import predict_single


class SegmentationService:
    """Orchestrates image decoding, neural inference, and overlay rendering."""

    DEFAULT_COLORS = {
        "road": (0, 229, 255),            # Cyan / Electric Blue (Aerial Roads)
        "building": (16, 185, 129),        # Emerald Green (Aerial Buildings)
        "satellite_road": (245, 158, 11),  # Amber Gold / Solar Orange (Satellite Roads)
        "satellite": (245, 158, 11),
    }

    @staticmethod
    def decode_image(image_bytes: bytes) -> np.ndarray:
        """Decode image bytes into RGB numpy array."""
        try:
            # First try PIL for comprehensive format support (TIFF, PNG, JPG)
            pil_img = Image.open(io.BytesIO(image_bytes))
            if pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")
            return np.array(pil_img)
        except Exception:
            # Fallback to OpenCV
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode image. Supported formats: PNG, JPG, JPEG, TIFF.")
            return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    @staticmethod
    def encode_base64_png(image_rgb_or_gray: np.ndarray) -> str:
        """Encode numpy array (RGB or Grayscale) to Base64 PNG data URI."""
        if len(image_rgb_or_gray.shape) == 3:
            # Convert RGB to BGR for cv2.imencode
            bgr = cv2.cvtColor(image_rgb_or_gray, cv2.COLOR_RGB2BGR)
            success, buffer = cv2.imencode(".png", bgr)
        else:
            success, buffer = cv2.imencode(".png", image_rgb_or_gray)

        if not success:
            raise RuntimeError("Failed to encode image to PNG.")
        b64_str = base64.b64encode(buffer).decode("utf-8")
        return f"data:image/png;base64,{b64_str}"

    @classmethod
    def run_segmentation(
        cls,
        image_bytes: bytes,
        task: str = "road",
        use_tta: bool = False,
        opacity: float = 0.55,
        custom_color: Optional[Tuple[int, int, int]] = None,
    ) -> Dict[str, Any]:
        """Perform end-to-end segmentation on input image bytes."""
        t_start = time.perf_counter()

        # 1. Decode & validate image
        image = cls.decode_image(image_bytes)
        orig_h, orig_w = image.shape[:2]

        if orig_h < 64 or orig_w < 64:
            raise ValueError(f"Image resolution too low ({orig_w}x{orig_h}). Minimum is 64x64 pixels.")
        if orig_h > 6000 or orig_w > 6000:
            raise ValueError(f"Image resolution too large ({orig_w}x{orig_h}). Maximum supported is 6000x6000.")

        # 2. Get model & preprocessing
        model, is_logits, preprocessing_fn = model_manager.get_model(task)

        # 3. Calculate pad size (multiple of 32)
        # Satellite images are natively 1024x1024; aerial images are 1500x1500 padded to 1536
        if task in ("satellite_road", "satellite", "deepglobe"):
            padded_h = max(1024, int(np.ceil(orig_h / 32.0) * 32))
            padded_w = max(1024, int(np.ceil(orig_w / 32.0) * 32))
        else:
            padded_h = max(1536, int(np.ceil(orig_h / 32.0) * 32))
            padded_w = max(1536, int(np.ceil(orig_w / 32.0) * 32))
        pad_size = max(padded_h, padded_w)

        # 4. Neural inference
        t_infer_start = time.perf_counter()
        pred_mask_padded = predict_single(
            model=model,
            image=image,
            preprocessing_fn=preprocessing_fn,
            padded_size=pad_size,
            device=model_manager.device,
            use_tta=use_tta,
            is_logits=is_logits,
        )
        t_infer_end = time.perf_counter()

        # 5. Crop back to original dimensions
        pred_mask = pred_mask_padded[:orig_h, :orig_w].astype(np.uint8)

        # 6. Calculate statistics
        total_pixels = int(orig_h * orig_w)
        positive_pixels = int(np.sum(pred_mask > 0))
        coverage_percent = round((positive_pixels / total_pixels) * 100, 2)

        # 7. Generate color mask & blended overlay
        color_rgb = custom_color or cls.DEFAULT_COLORS.get(task, (0, 229, 255))
        mask_3ch = np.zeros_like(image, dtype=np.uint8)
        mask_3ch[pred_mask > 0] = color_rgb

        # Alpha blend overlay
        overlay = image.copy().astype(np.float32)
        fg_mask = (pred_mask > 0)[:, :, None]
        color_arr = np.array(color_rgb, dtype=np.float32)

        overlay = np.where(
            fg_mask,
            (1.0 - opacity) * overlay + opacity * color_arr,
            overlay,
        ).clip(0, 255).astype(np.uint8)

        # 8. Encode outputs as Base64
        binary_mask_255 = (pred_mask * 255).astype(np.uint8)
        b64_mask = cls.encode_base64_png(binary_mask_255)
        b64_overlay = cls.encode_base64_png(overlay)
        b64_original = cls.encode_base64_png(image)

        t_end = time.perf_counter()

        return {
            "task": task,
            "tta": use_tta,
            "dimensions": {
                "width": orig_w,
                "height": orig_h,
            },
            "statistics": {
                "total_pixels": total_pixels,
                "detected_pixels": positive_pixels,
                "coverage_percent": coverage_percent,
            },
            "telemetry": {
                "inference_time_ms": round((t_infer_end - t_infer_start) * 1000, 1),
                "total_time_ms": round((t_end - t_start) * 1000, 1),
                "device": str(model_manager.device),
            },
            "images": {
                "original": b64_original,
                "mask": b64_mask,
                "overlay": b64_overlay,
            },
        }


segmentation_service = SegmentationService()
