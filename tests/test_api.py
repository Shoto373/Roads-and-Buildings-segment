"""Smoke and integration tests for Aerial Road and Building Segmentation API."""

import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    """Verify health check returns service and model status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ("ready", "degraded")
    assert "road_model_loaded" in data
    assert "building_model_loaded" in data


def test_metrics_road_endpoint(client):
    """Verify road metrics schema, reasonable bounds, and presence of relaxed metrics."""
    response = client.get("/api/metrics/road")
    assert response.status_code == 200
    data = response.json()
    assert data["task"] == "road"
    assert "metrics" in data
    metrics = data["metrics"]
    assert 0.0 <= metrics["iou"] <= 1.0
    assert 0.0 <= metrics["dice"] <= 1.0
    assert 0.0 <= metrics["accuracy"] <= 1.0
    # Verify relaxed metrics if present
    if "relaxed_3px_iou" in metrics:
        assert 0.0 <= metrics["relaxed_3px_iou"] <= 1.0
        assert metrics["relaxed_3px_iou"] >= metrics["iou"]  # Relaxed IoU must be >= Strict IoU


def test_metrics_building_endpoint(client):
    """Verify building metrics schema and reasonable bounds."""
    response = client.get("/api/metrics/building")
    assert response.status_code == 200
    data = response.json()
    assert data["task"] == "building"
    assert "metrics" in data
    metrics = data["metrics"]
    assert 0.0 <= metrics["iou"] <= 1.0


def test_samples_endpoint(client):
    """Verify sample preset images exist and contain required keys."""
    response = client.get("/api/samples")
    assert response.status_code == 200
    samples = response.json()
    assert len(samples) >= 1
    for s in samples:
        assert "id" in s
        assert "title" in s
        assert "url" in s
        assert "recommended_task" in s


def test_segment_endpoint_success(client):
    """Verify inference on a synthesized small RGB test image."""
    # Create a small 128x128 test image
    img = Image.new("RGB", (128, 128), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    response = client.post(
        "/api/segment",
        files={"file": ("test.png", buf, "image/png")},
        data={"task": "road", "tta": "false", "opacity": "0.6"},
    )
    assert response.status_code == 200
    result = response.json()

    assert result["task"] == "road"
    assert result["dimensions"]["width"] == 128
    assert result["dimensions"]["height"] == 128
    assert "telemetry" in result
    assert "images" in result
    assert result["images"]["mask"].startswith("data:image/png;base64,")
    assert result["images"]["overlay"].startswith("data:image/png;base64,")


def test_segment_invalid_extension(client):
    """Verify 400 Bad Request when uploading non-image files."""
    response = client.post(
        "/api/segment",
        files={"file": ("test.txt", io.BytesIO(b"hello world"), "text/plain")},
        data={"task": "road"},
    )
    assert response.status_code == 400
    assert "Unsupported format" in response.json()["detail"]


def test_segment_invalid_task(client):
    """Verify 400 Bad Request when requesting unknown task."""
    img = Image.new("RGB", (64, 64), color=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    response = client.post(
        "/api/segment",
        files={"file": ("test.png", buf, "image/png")},
        data={"task": "unknown_task"},
    )
    assert response.status_code == 400


def test_segment_satellite_endpoint_success(client):
    """Verify inference on satellite mode with satellite_road task."""
    img = Image.new("RGB", (128, 128), color=(80, 110, 70))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    response = client.post(
        "/api/segment",
        files={"file": ("sat_test.png", buf, "image/png")},
        data={"task": "satellite_road", "tta": "false", "opacity": "0.6"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["task"] == "satellite_road"
    assert result["dimensions"]["width"] == 128
    assert "telemetry" in result
