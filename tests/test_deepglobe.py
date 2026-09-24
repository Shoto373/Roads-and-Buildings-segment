"""Unit tests for DeepGlobe dataset integration and pipeline configuration."""

import os
import tempfile
import cv2
import numpy as np
import pytest
import torch

from config import Config, parse_args
from deepglobe_dataset import DeepGlobeDataset, load_deepglobe_samples


def test_deepglobe_config():
    """Verify default parameters for DeepGlobe task."""
    cfg = parse_args(["--task", "deepglobe"])
    assert cfg.data.task == "deepglobe"
    assert cfg.data.image_size == 1024
    assert cfg.data.padded_size == 1024
    assert cfg.data.crop_size == 512
    assert cfg.model.decoder == "DeepLabV3Plus"
    assert cfg.model.encoder == "resnet34"
    assert cfg.train.batch_size == 4


def test_deepglobe_dataset_loading():
    """Verify DeepGlobeDataset and load_deepglobe_samples with temporary synthetic files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        train_dir = os.path.join(tmpdir, "train")
        os.makedirs(train_dir, exist_ok=True)

        # Create 10 dummy image-mask pairs
        for i in range(10):
            img = np.random.randint(0, 255, (1024, 1024, 3), dtype=np.uint8)
            mask = np.zeros((1024, 1024), dtype=np.uint8)
            mask[400:600, :] = 255  # Horizontal road

            cv2.imwrite(os.path.join(train_dir, f"{100000 + i}_sat.jpg"), img)
            cv2.imwrite(os.path.join(train_dir, f"{100000 + i}_mask.png"), mask)

        train_samples, val_samples, _ = load_deepglobe_samples(tmpdir, val_ratio=0.2, seed=42)

        assert len(train_samples) == 8
        assert len(val_samples) == 2

        dataset = DeepGlobeDataset(train_samples)
        assert len(dataset) == 8

        image, mask = dataset[0]
        assert image.shape == (1024, 1024, 3)
        assert mask.shape == (1024, 1024, 1)
        assert mask.max() == 1.0
        assert mask.min() == 0.0
