"""
Centralized configuration for the segmentation project.
Supports both road and building segmentation tasks via CLI arguments.
"""

import argparse
import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DataConfig:
    """Dataset paths and image parameters."""
    task: str = "road"  # "road", "building", or "deepglobe"
    base_dir: str = "notebooks/input"
    image_size: int = 1500      # Original image size
    padded_size: int = 1536     # Padded to be divisible by 32
    crop_size: int = 256        # Training crop size

    @property
    def dataset_dir(self) -> str:
        if self.task == "deepglobe":
            candidates = [
                os.path.join(self.base_dir, "deepglobe-road-extraction-dataset"),
                os.path.join(self.base_dir, "deepglobe-road-dataset"),
                os.path.join(self.base_dir, "deepglobe"),
                "deepglobe-road-extraction-dataset",
            ]
            for c in candidates:
                if os.path.isdir(c):
                    return c
            return candidates[0]
        elif self.task == "road":
            return os.path.join(self.base_dir, "massachusetts-roads-dataset", "tiff")
        else:
            return os.path.join(self.base_dir, "massachusetts-buildings-dataset", "tiff")

    @property
    def train_images_dir(self) -> str:
        return os.path.join(self.dataset_dir, "train")

    @property
    def train_masks_dir(self) -> str:
        if self.task == "deepglobe":
            return os.path.join(self.dataset_dir, "train")
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
        if self.task in ["road", "deepglobe"]:
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


def parse_args(args=None, description: str = "Segmentation") -> Config:
    """Parse CLI arguments and return a Config object."""
    if isinstance(args, str):
        description = args
        args = None

    parser = argparse.ArgumentParser(description=description)

    # Task
    parser.add_argument("--task", type=str, default="road",
                        choices=["road", "building", "deepglobe"],
                        help="Segmentation task: road, building, or deepglobe (default: road)")

    # Model
    parser.add_argument("--encoder", type=str, default="efficientnet-b7",
                        help="Encoder backbone (default: efficientnet-b7, or resnet34 for deepglobe)")
    parser.add_argument("--decoder", type=str, default="Unet",
                        choices=["Unet", "UnetPlusPlus", "DeepLabV3Plus"],
                        help="Decoder architecture (default: Unet, or DeepLabV3Plus for deepglobe)")

    # Training
    parser.add_argument("--epochs", type=int, default=30,
                        help="Number of training epochs (default: 30)")
    parser.add_argument("--batch-size", type=int, default=8,
                        help="Training batch size (default: 8, or 4 for deepglobe)")
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
    parser.add_argument("--slacks", type=int, nargs="+", default=[2, 3, 5],
                        help="Slack distances in pixels for relaxed IoU evaluation (default: 2 3 5)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of test images to evaluate (default: all)")

    cli_str = " ".join(args) if args is not None else " ".join(sys.argv)
    parsed_args = parser.parse_args(args=args)

    config = Config()
    config.data.task = parsed_args.task

    if parsed_args.task == "deepglobe":
        # Satellite imagery configuration: 1024x1024 native resolution
        config.data.image_size = 1024
        config.data.padded_size = 1024
        config.data.crop_size = 512

        # Smart defaults for DeepGlobe if not overridden explicitly
        if "--decoder" not in cli_str:
            config.model.decoder = "DeepLabV3Plus"
        else:
            config.model.decoder = parsed_args.decoder

        if "--encoder" not in cli_str:
            config.model.encoder = "resnet34"
        else:
            config.model.encoder = parsed_args.encoder

        if "--batch-size" not in cli_str:
            config.train.batch_size = 4
        else:
            config.train.batch_size = parsed_args.batch_size
    else:
        config.model.encoder = parsed_args.encoder
        config.model.decoder = parsed_args.decoder
        config.train.batch_size = parsed_args.batch_size

    config.train.epochs = parsed_args.epochs
    config.train.lr = parsed_args.lr
    config.train.use_amp = not parsed_args.no_amp
    config.train.patience = parsed_args.patience

    # Store extra args for inference/evaluate scripts
    config._num_examples = parsed_args.num_examples
    config._idx = parsed_args.idx
    config._tta = parsed_args.tta
    config._weights_path = parsed_args.weights
    config._input_image = parsed_args.input_image
    config._slacks = tuple(parsed_args.slacks)
    config._limit = parsed_args.limit

    return config
