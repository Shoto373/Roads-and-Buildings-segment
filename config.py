"""
Centralized configuration for the segmentation project.
Supports both road and building segmentation tasks via CLI arguments.
"""

import argparse
import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DataConfig:
    """Dataset paths and image parameters."""
    task: str = "road"  # "road" or "building"
    base_dir: str = "notebooks/input"
    image_size: int = 1500      # Original image size
    padded_size: int = 1536     # Padded to be divisible by 32
    crop_size: int = 256        # Training crop size

    @property
    def dataset_dir(self) -> str:
        if self.task == "road":
            return os.path.join(self.base_dir, "massachusetts-roads-dataset", "tiff")
        else:
            return os.path.join(self.base_dir, "massachusetts-buildings-dataset", "tiff")

    @property
    def train_images_dir(self) -> str:
        return os.path.join(self.dataset_dir, "train")

    @property
    def train_masks_dir(self) -> str:
        return os.path.join(self.dataset_dir, "train_labels")

    @property
    def val_images_dir(self) -> str:
        return os.path.join(self.dataset_dir, "val")

    @property
    def val_masks_dir(self) -> str:
        return os.path.join(self.dataset_dir, "val_labels")

    @property
    def test_images_dir(self) -> str:
        return os.path.join(self.dataset_dir, "test")

    @property
    def test_masks_dir(self) -> str:
        return os.path.join(self.dataset_dir, "test_labels")

    @property
    def class_names(self) -> List[str]:
        if self.task == "road":
            return ["background", "road"]
        else:
            return ["background", "building"]


@dataclass
class ModelConfig:
    """Model architecture parameters."""
    encoder: str = "efficientnet-b7"
    encoder_weights: str = "imagenet"
    decoder: str = "Unet"          # "Unet", "UnetPlusPlus", "DeepLabV3Plus"
    classes: int = 1               # Binary segmentation — single channel output
    activation: Optional[str] = None  # None for logits (BCEWithLogitsLoss), "sigmoid" for inference


@dataclass
class TrainConfig:
    """Training hyperparameters."""
    epochs: int = 30
    batch_size: int = 8
    val_batch_size: int = 1
    lr: float = 1e-4
    lr_min: float = 5e-5
    num_workers: int = 0         # 0 for Windows compatibility
    use_amp: bool = True         # Mixed precision training
    patience: int = 7            # Early stopping patience
    # Loss weights for Combo Loss (Dice + BCE)
    dice_weight: float = 0.5
    bce_weight: float = 0.5


@dataclass
class AugmentConfig:
    """Augmentation toggles."""
    use_flip: bool = True
    use_rotate: bool = True
    use_color_jitter: bool = True
    use_gauss_noise: bool = True
    use_blur: bool = True
    use_brightness_contrast: bool = True
    use_clahe: bool = True


@dataclass
class Config:
    """Top-level configuration container."""
    data: DataConfig = field(default_factory=DataConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    train: TrainConfig = field(default_factory=TrainConfig)
    augment: AugmentConfig = field(default_factory=AugmentConfig)

    @property
    def weights_dir(self) -> str:
        return "weights"

    @property
    def outputs_dir(self) -> str:
        return "outputs"

    @property
    def best_model_path(self) -> str:
        return os.path.join(self.weights_dir, f"best_{self.data.task}_model.pth")

    @property
    def tensorboard_dir(self) -> str:
        return os.path.join("runs", self.data.task)


def parse_args(description: str = "Segmentation") -> Config:
    """Parse CLI arguments and return a Config object."""
    parser = argparse.ArgumentParser(description=description)

    # Task
    parser.add_argument("--task", type=str, default="road",
                        choices=["road", "building"],
                        help="Segmentation task: road or building (default: road)")

    # Model
    parser.add_argument("--encoder", type=str, default="efficientnet-b7",
                        help="Encoder backbone (default: efficientnet-b7)")
    parser.add_argument("--decoder", type=str, default="Unet",
                        choices=["Unet", "UnetPlusPlus", "DeepLabV3Plus"],
                        help="Decoder architecture (default: Unet)")

    # Training
    parser.add_argument("--epochs", type=int, default=30,
                        help="Number of training epochs (default: 30)")
    parser.add_argument("--batch-size", type=int, default=8,
                        help="Training batch size (default: 8)")
    parser.add_argument("--lr", type=float, default=1e-4,
                        help="Learning rate (default: 0.0001)")
    parser.add_argument("--no-amp", action="store_true",
                        help="Disable mixed precision training")
    parser.add_argument("--patience", type=int, default=7,
                        help="Early stopping patience (default: 7)")

    # Inference
    parser.add_argument("--num-examples", type=int, default=10,
                        help="Number of inference examples to generate (default: 10)")
    parser.add_argument("--idx", type=int, default=0,
                        help="Index of single test image for demo (default: 0)")
    parser.add_argument("--tta", action="store_true",
                        help="Enable Test-Time Augmentation")
    parser.add_argument("--weights", type=str, default=None,
                        help="Path to model weights file (overrides default)")
    parser.add_argument("--input-image", type=str, default=None,
                        help="Path to a custom input image for single inference")

    args = parser.parse_args()

    config = Config()
    config.data.task = args.task
    config.model.encoder = args.encoder
    config.model.decoder = args.decoder
    config.train.epochs = args.epochs
    config.train.batch_size = args.batch_size
    config.train.lr = args.lr
    config.train.use_amp = not args.no_amp
    config.train.patience = args.patience

    # Store extra args for inference/evaluate scripts
    config._num_examples = args.num_examples
    config._idx = args.idx
    config._tta = args.tta
    config._weights_path = args.weights
    config._input_image = args.input_image

    return config
