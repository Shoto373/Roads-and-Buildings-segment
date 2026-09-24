"""
DeepGlobe Road Extraction Dataset Loader.

Dataset specification:
- Source: Kaggle 'balraj98/deepglobe-road-extraction-dataset' (DigitalGlobe satellites, 0.5m/px)
- Image dimensions: 1024x1024 RGB (*_sat.jpg)
- Mask dimensions: 1024x1024 binary (*_mask.png), where road pixels are 255 (white)
- Structure:
    deepglobe/
    ├── metadata.csv (optional)
    ├── train/
    │   ├── 100034_sat.jpg
    │   ├── 100034_mask.png
    │   └── ...
    ├── valid/
    │   └── *_sat.jpg
    └── test/
        └── *_sat.jpg
"""

import os
import cv2
import numpy as np
import pandas as pd
import torch
from typing import List, Tuple, Optional
from torch.utils.data import Dataset


class DeepGlobeDataset(Dataset):
    """PyTorch Dataset for DeepGlobe Road Extraction."""

    def __init__(
        self,
        samples: List[Tuple[str, Optional[str]]],
        augmentation=None,
        preprocessing=None,
    ):
        """
        Args:
            samples: List of (image_path, mask_path). mask_path can be None for test images.
            augmentation: Albumentations compose transforms for data augmentation.
            preprocessing: Albumentations compose transforms for normalization/to_tensor.
        """
        self.samples = samples
        self.augmentation = augmentation
        self.preprocessing = preprocessing

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        img_path, mask_path = self.samples[idx]

        # Read satellite image (BGR -> RGB)
        image = cv2.imread(img_path)
        if image is None:
            raise FileNotFoundError(f"Failed to read image at: {img_path}")
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Read mask if available
        if mask_path is not None and os.path.exists(mask_path):
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            if mask is None:
                raise FileNotFoundError(f"Failed to read mask at: {mask_path}")
            # Binarize: road is white (255) -> 1.0, background is 0.0
            mask = (mask > 127).astype(np.float32)
            mask = np.expand_dims(mask, axis=-1)
        else:
            # Dummy mask for unlabeled evaluation / inference
            mask = np.zeros((image.shape[0], image.shape[1], 1), dtype=np.float32)

        # Apply spatial & color augmentations
        if self.augmentation:
            augmented = self.augmentation(image=image, mask=mask)
            image, mask = augmented["image"], augmented["mask"]

        # Apply model-specific preprocessing and to_tensor
        if self.preprocessing:
            preprocessed = self.preprocessing(image=image, mask=mask)
            image, mask = preprocessed["image"], preprocessed["mask"]

        return image, mask


def find_deepglobe_root(base_dir: str = "notebooks/input") -> str:
    """Find the root directory where DeepGlobe dataset is located."""
    possible_names = [
        "deepglobe-road-extraction-dataset",
        "deepglobe-road-dataset",
        "deepglobe",
        "deepglobe_roads",
    ]
    for name in possible_names:
        full_path = os.path.join(base_dir, name)
        if os.path.isdir(full_path):
            return full_path
        # Check current directory as well
        if os.path.isdir(name):
            return os.path.abspath(name)

    return os.path.join(base_dir, "deepglobe-road-extraction-dataset")


def load_deepglobe_samples(
    dataset_dir: str,
    val_ratio: float = 0.15,
    seed: int = 42,
) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]], List[Tuple[str, Optional[str]]]]:
    """Scan and split DeepGlobe images into train, validation, and test sets.

    Since official valid/test splits on Kaggle do not include ground-truth masks,
    the train folder (6226 pairs) is split into train and validation sets.

    Returns:
        (train_samples, val_samples, test_samples)
    """
    train_dir = os.path.join(dataset_dir, "train")
    if not os.path.isdir(train_dir):
        # Maybe dataset_dir itself is the folder containing images
        if any(f.endswith("_sat.jpg") for f in os.listdir(dataset_dir) if os.path.isfile(os.path.join(dataset_dir, f))):
            train_dir = dataset_dir

    metadata_path = os.path.join(dataset_dir, "metadata.csv")
    labeled_pairs: List[Tuple[str, str]] = []

    if os.path.isfile(metadata_path):
        try:
            df = pd.read_csv(metadata_path)
            # Filter rows with masks
            if "split" in df.columns:
                train_df = df[df["split"] == "train"]
            else:
                train_df = df.dropna(subset=["mask_path"])

            for _, row in train_df.iterrows():
                sat_p = str(row["sat_image_path"])
                mask_p = str(row["mask_path"])
                # Handle relative paths from metadata
                full_sat = os.path.join(dataset_dir, sat_p) if not os.path.isabs(sat_p) else sat_p
                full_mask = os.path.join(dataset_dir, mask_p) if not os.path.isabs(mask_p) else mask_p
                if os.path.exists(full_sat) and os.path.exists(full_mask):
                    labeled_pairs.append((full_sat, full_mask))
        except Exception as e:
            print(f"Warning: Failed to parse metadata.csv ({e}). Falling back to directory scan.")

    # Fallback to direct directory scan if metadata.csv not found or empty
    if not labeled_pairs and os.path.isdir(train_dir):
        all_files = os.listdir(train_dir)
        sat_files = sorted([f for f in all_files if f.endswith("_sat.jpg") or f.endswith(".jpg") and "_mask" not in f])

        for sat_file in sat_files:
            prefix = sat_file.replace("_sat.jpg", "").replace(".jpg", "")
            # Possible mask file names
            mask_candidates = [
                f"{prefix}_mask.png",
                f"{prefix}_mask.tif",
                f"{prefix}_mask.jpg",
                f"{prefix}.png",
            ]
            found_mask = None
            for mc in mask_candidates:
                candidate_path = os.path.join(train_dir, mc)
                if os.path.isfile(candidate_path):
                    found_mask = candidate_path
                    break

            if found_mask:
                labeled_pairs.append((os.path.join(train_dir, sat_file), found_mask))

    # Deterministic train/val split
    rng = np.random.RandomState(seed)
    indices = np.arange(len(labeled_pairs))
    rng.shuffle(indices)

    n_val = int(len(labeled_pairs) * val_ratio)
    val_indices = set(indices[:n_val])

    train_samples = [labeled_pairs[i] for i in range(len(labeled_pairs)) if i not in val_indices]
    val_samples = [labeled_pairs[i] for i in range(len(labeled_pairs)) if i in val_indices]

    # Collect unmasked test samples if test directory exists
    test_samples: List[Tuple[str, Optional[str]]] = []
    test_dir = os.path.join(dataset_dir, "test")
    if os.path.isdir(test_dir):
        for f in sorted(os.listdir(test_dir)):
            if f.endswith(".jpg") or f.endswith(".png"):
                test_samples.append((os.path.join(test_dir, f), None))

    return train_samples, val_samples, test_samples
