"""
Unified training script for road and building segmentation.

Usage:
    python train.py --task road              # Train road segmentation (default)
    python train.py --task building          # Train building segmentation
    python train.py --task road --epochs 50  # Custom epochs
    python train.py --task road --decoder UnetPlusPlus  # Different decoder
    python train.py --task road --no-amp     # Disable mixed precision
"""

import os
os.environ["OPENCV_IO_MAX_IMAGE_PIXELS"] = str(pow(2, 40))
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"  # Suppress TIFF geotag warnings
import cv2
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import albumentations as album
import segmentation_models_pytorch as smp
import matplotlib.pyplot as plt
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm

from config import parse_args
from deepglobe_dataset import DeepGlobeDataset, load_deepglobe_samples


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

class SegmentationDataset(torch.utils.data.Dataset):
    """Dataset for binary segmentation (road or building).

    Masks are expected as RGB images where [255,255,255] = foreground.
    Returns single-channel binary mask for classes=1 output.
    """

    def __init__(self, images_dir, masks_dir, augmentation=None, preprocessing=None):
        self.image_paths = [os.path.join(images_dir, img) for img in sorted(os.listdir(images_dir))]
        self.mask_paths = [os.path.join(masks_dir, img) for img in sorted(os.listdir(masks_dir))]
        self.augmentation = augmentation
        self.preprocessing = preprocessing

    def __getitem__(self, i):
        image = cv2.cvtColor(cv2.imread(self.image_paths[i]), cv2.COLOR_BGR2RGB)
        mask = cv2.imread(self.mask_paths[i], cv2.IMREAD_GRAYSCALE)
        # Binarize: foreground pixels > 127 → 1.0
        mask = (mask > 127).astype(np.float32)
        # Add channel dim: (H, W) → (H, W, 1)
        mask = np.expand_dims(mask, axis=-1)

        if self.augmentation:
            sample = self.augmentation(image=image, mask=mask)
            image, mask = sample['image'], sample['mask']
        if self.preprocessing:
            sample = self.preprocessing(image=image, mask=mask)
            image, mask = sample['image'], sample['mask']

        return image, mask

    def __len__(self):
        return len(self.image_paths)


# ---------------------------------------------------------------------------
# Augmentations
# ---------------------------------------------------------------------------

def get_training_augmentation(cfg):
    """Rich augmentation pipeline for training."""
    transforms = [
        album.RandomCrop(height=cfg.data.crop_size, width=cfg.data.crop_size),
    ]

    # Geometric augmentations
    if cfg.augment.use_flip or cfg.augment.use_rotate:
        geo = []
        if cfg.augment.use_flip:
            geo.append(album.HorizontalFlip(p=1))
            geo.append(album.VerticalFlip(p=1))
        if cfg.augment.use_rotate:
            geo.append(album.RandomRotate90(p=1))
        transforms.append(album.OneOf(geo, p=0.75))

    # Color / photometric augmentations — critical for generalization
    if cfg.augment.use_brightness_contrast:
        transforms.append(album.RandomBrightnessContrast(
            brightness_limit=0.2, contrast_limit=0.2, p=0.5
        ))
    if cfg.augment.use_color_jitter:
        transforms.append(album.ColorJitter(
            brightness=0.1, contrast=0.1, saturation=0.15, hue=0.05, p=0.4
        ))
    if cfg.augment.use_clahe:
        transforms.append(album.CLAHE(clip_limit=4.0, p=0.3))
    if cfg.augment.use_gauss_noise:
        transforms.append(album.GaussNoise(p=0.3))
    if cfg.augment.use_blur:
        transforms.append(album.OneOf([
            album.GaussianBlur(blur_limit=(3, 5), p=1),
            album.MotionBlur(blur_limit=3, p=1),
        ], p=0.2))

    return album.Compose(transforms)


def get_validation_augmentation(cfg):
    """Pad to model-compatible size for full-image validation."""
    return album.Compose([
        album.PadIfNeeded(
            min_height=cfg.data.padded_size,
            min_width=cfg.data.padded_size,
            border_mode=0
        ),
    ])


def to_tensor(x, **kwargs):
    return x.transpose(2, 0, 1).astype('float32')


def get_preprocessing(preprocessing_fn=None):
    """Apply encoder-specific preprocessing + convert to tensor."""
    _transform = []
    if preprocessing_fn:
        _transform.append(album.Lambda(image=preprocessing_fn))
    _transform.append(album.Lambda(image=to_tensor, mask=to_tensor))
    return album.Compose(_transform)


# ---------------------------------------------------------------------------
# Losses
# ---------------------------------------------------------------------------

class DiceLoss(nn.Module):
    """Soft Dice Loss for binary segmentation."""

    def forward(self, logits, targets, eps=1e-7):
        probs = torch.sigmoid(logits)
        probs = probs.view(probs.size(0), -1)
        targets = targets.view(targets.size(0), -1)
        intersection = torch.sum(probs * targets, dim=1)
        union = torch.sum(probs, dim=1) + torch.sum(targets, dim=1)
        dice = (2.0 * intersection + eps) / (union + eps)
        return torch.mean(1.0 - dice)


class ComboLoss(nn.Module):
    """Combo Loss = α * Dice Loss + β * BCE with Logits Loss.

    Dice Loss handles class imbalance well.
    BCE Loss provides stable per-pixel gradients, especially for thin structures (roads).
    """

    def __init__(self, dice_weight=0.5, bce_weight=0.5):
        super().__init__()
        self.dice_loss = DiceLoss()
        self.bce_loss = nn.BCEWithLogitsLoss()
        self.dice_weight = dice_weight
        self.bce_weight = bce_weight

    def forward(self, logits, targets):
        return (self.dice_weight * self.dice_loss(logits, targets) +
                self.bce_weight * self.bce_loss(logits, targets))


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@torch.no_grad()
def calculate_iou(logits, targets, threshold=0.5):
    """Calculate IoU (Jaccard Index) for binary segmentation."""
    preds = (torch.sigmoid(logits) > threshold).float()
    intersection = (preds * targets).sum((1, 2, 3))
    union = (preds + targets).sum((1, 2, 3)) - intersection
    iou = (intersection / (union + 1e-7)).mean().item()
    return iou


@torch.no_grad()
def calculate_dice(logits, targets, threshold=0.5):
    """Calculate Dice coefficient for binary segmentation."""
    preds = (torch.sigmoid(logits) > threshold).float()
    intersection = (preds * targets).sum((1, 2, 3))
    dice = (2.0 * intersection / (preds.sum((1, 2, 3)) + targets.sum((1, 2, 3)) + 1e-7)).mean().item()
    return dice


# ---------------------------------------------------------------------------
# Model factory
# ---------------------------------------------------------------------------

def create_model(cfg):
    """Create segmentation model based on config."""
    decoder_map = {
        "Unet": smp.Unet,
        "UnetPlusPlus": smp.UnetPlusPlus,
        "DeepLabV3Plus": smp.DeepLabV3Plus,
    }

    decoder_cls = decoder_map.get(cfg.model.decoder)
    if decoder_cls is None:
        raise ValueError(f"Unknown decoder: {cfg.model.decoder}. "
                         f"Choose from: {list(decoder_map.keys())}")

    model = decoder_cls(
        encoder_name=cfg.model.encoder,
        encoder_weights=cfg.model.encoder_weights,
        classes=cfg.model.classes,       # 1 channel for binary segmentation
        activation=cfg.model.activation, # None → raw logits for BCEWithLogitsLoss
    )
    return model


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def main():
    cfg = parse_args(description="Train segmentation model")

    os.makedirs(cfg.weights_dir, exist_ok=True)
    os.makedirs(cfg.outputs_dir, exist_ok=True)

    print(f"{'='*60}")
    print(f"  Task:     {cfg.data.task}")
    print(f"  Encoder:  {cfg.model.encoder}")
    print(f"  Decoder:  {cfg.model.decoder}")
    print(f"  Epochs:   {cfg.train.epochs}")
    print(f"  Batch:    {cfg.train.batch_size}")
    print(f"  LR:       {cfg.train.lr}")
    print(f"  AMP:      {cfg.train.use_amp}")
    print(f"  Patience: {cfg.train.patience}")
    print(f"{'='*60}")

    # Preprocessing
    preprocessing_fn = smp.encoders.get_preprocessing_fn(
        cfg.model.encoder, cfg.model.encoder_weights
    )

    # Datasets
    limit = getattr(cfg, '_limit', None)
    if cfg.data.task == "deepglobe":
        print(f"Loading DeepGlobe dataset from: {cfg.data.dataset_dir}")
        train_samples, val_samples, _ = load_deepglobe_samples(cfg.data.dataset_dir)
        if len(train_samples) == 0:
            raise FileNotFoundError(
                f"No DeepGlobe training images found in: {cfg.data.dataset_dir}\n"
                f"Please download the dataset from https://www.kaggle.com/datasets/balraj98/deepglobe-road-extraction-dataset "
                f"and extract it into: {cfg.data.dataset_dir}"
            )
        if limit:
            val_lim = max(2, limit // 5)
            print(f"Trial mode: limiting to {limit} train and {val_lim} val samples.")
            train_samples = train_samples[:limit]
            val_samples = val_samples[:val_lim]

        train_dataset = DeepGlobeDataset(
            train_samples,
            augmentation=get_training_augmentation(cfg),
            preprocessing=get_preprocessing(preprocessing_fn),
        )
        valid_dataset = DeepGlobeDataset(
            val_samples,
            augmentation=get_validation_augmentation(cfg),
            preprocessing=get_preprocessing(preprocessing_fn),
        )
    else:
        train_dataset = SegmentationDataset(
            cfg.data.train_images_dir,
            cfg.data.train_masks_dir,
            augmentation=get_training_augmentation(cfg),
            preprocessing=get_preprocessing(preprocessing_fn),
        )
        valid_dataset = SegmentationDataset(
            cfg.data.val_images_dir,
            cfg.data.val_masks_dir,
            augmentation=get_validation_augmentation(cfg),
            preprocessing=get_preprocessing(preprocessing_fn),
        )
        if limit:
            val_lim = max(2, limit // 5)
            print(f"Trial mode: limiting to {limit} train and {val_lim} val samples.")
            train_dataset.image_paths = train_dataset.image_paths[:limit]
            train_dataset.mask_paths = train_dataset.mask_paths[:limit]
            valid_dataset.image_paths = valid_dataset.image_paths[:val_lim]
            valid_dataset.mask_paths = valid_dataset.mask_paths[:val_lim]

    train_loader = DataLoader(
        train_dataset,
        batch_size=cfg.train.batch_size,
        shuffle=True,
        num_workers=cfg.train.num_workers,
    )
    valid_loader = DataLoader(
        valid_dataset,
        batch_size=cfg.train.val_batch_size,
        shuffle=False,
        num_workers=cfg.train.num_workers,
    )

    print(f"Train samples: {len(train_dataset)} | Val samples: {len(valid_dataset)}")

    # Model
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {DEVICE}")

    model = create_model(cfg).to(DEVICE)

    # Loss, optimizer, scheduler
    criterion = ComboLoss(
        dice_weight=cfg.train.dice_weight,
        bce_weight=cfg.train.bce_weight,
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg.train.lr)
    lr_scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
        optimizer, T_0=1, T_mult=2, eta_min=cfg.train.lr_min,
    )

    # Mixed precision
    scaler = torch.amp.GradScaler("cuda", enabled=cfg.train.use_amp and DEVICE.type == "cuda")

    # TensorBoard
    writer = SummaryWriter(log_dir=cfg.tensorboard_dir)

    # Training state
    best_iou_score = 0.0
    epochs_no_improve = 0
    train_logs_list, valid_logs_list = [], []

    print(f"\nStarting training for {cfg.train.epochs} epochs...\n")

    for epoch in range(cfg.train.epochs):
        # ---- Train ----
        model.train()
        train_loss = 0.0
        train_iou = 0.0

        pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{cfg.train.epochs} [Train]",
                     leave=False)
        for images, masks in pbar:
            images, masks = images.to(DEVICE), masks.to(DEVICE)

            optimizer.zero_grad()

            with torch.amp.autocast("cuda", enabled=cfg.train.use_amp and DEVICE.type == "cuda"):
                outputs = model(images)
                loss = criterion(outputs, masks)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            train_loss += loss.item()
            train_iou += calculate_iou(outputs.detach(), masks)

            pbar.set_postfix(loss=f"{loss.item():.4f}")

        train_loss /= len(train_loader)
        train_iou /= len(train_loader)

        # ---- Validate ----
        model.eval()
        valid_loss = 0.0
        valid_iou = 0.0

        with torch.no_grad():
            for images, masks in tqdm(valid_loader,
                                       desc=f"Epoch {epoch+1}/{cfg.train.epochs} [Val]",
                                       leave=False):
                images, masks = images.to(DEVICE), masks.to(DEVICE)

                with torch.amp.autocast("cuda", enabled=cfg.train.use_amp and DEVICE.type == "cuda"):
                    outputs = model(images)
                    loss = criterion(outputs, masks)

                valid_loss += loss.item()
                valid_iou += calculate_iou(outputs, masks)

        valid_loss /= len(valid_loader)
        valid_iou /= len(valid_loader)

        # ---- Logging ----
        print(f"Epoch {epoch+1:3d}/{cfg.train.epochs} | "
              f"Train Loss: {train_loss:.4f}  IoU: {train_iou:.4f} | "
              f"Val Loss: {valid_loss:.4f}  IoU: {valid_iou:.4f} | "
              f"LR: {optimizer.param_groups[0]['lr']:.6f}")

        train_logs_list.append({'dice_loss': train_loss, 'iou_score': train_iou})
        valid_logs_list.append({'dice_loss': valid_loss, 'iou_score': valid_iou})

        writer.add_scalars('Loss', {'train': train_loss, 'val': valid_loss}, epoch)
        writer.add_scalars('IoU', {'train': train_iou, 'val': valid_iou}, epoch)
        writer.add_scalar('LR', optimizer.param_groups[0]['lr'], epoch)

        lr_scheduler.step()

        # ---- Checkpointing ----
        if valid_iou > best_iou_score or epoch == 0:
            if valid_iou > best_iou_score:
                best_iou_score = valid_iou
            epochs_no_improve = 0
            checkpoint = {
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'best_iou': best_iou_score,
                'config': {
                    'encoder': cfg.model.encoder,
                    'decoder': cfg.model.decoder,
                    'classes': cfg.model.classes,
                    'task': cfg.data.task,
                },
            }
            torch.save(checkpoint, cfg.best_model_path)
            print(f"  [+] Model saved! Best IoU: {best_iou_score:.4f}")
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= cfg.train.patience:
                print(f"\n[!] Early stopping triggered after {cfg.train.patience} epochs without improvement.")
                break

    writer.close()
    print(f"\nTraining complete! Best IoU: {best_iou_score:.4f}")
    print(f"Weights saved to: {cfg.best_model_path}")

    # ---- Plots ----
    train_logs_df = pd.DataFrame(train_logs_list)
    valid_logs_df = pd.DataFrame(valid_logs_list)

    task_prefix = cfg.data.task

    # IoU plot
    plt.figure(figsize=(20, 8))
    plt.plot(train_logs_df.index.tolist(), train_logs_df.iou_score.tolist(), lw=3, label='Train')
    plt.plot(valid_logs_df.index.tolist(), valid_logs_df.iou_score.tolist(), lw=3, label='Valid')
    plt.xlabel('Epochs', fontsize=20)
    plt.ylabel('IoU Score', fontsize=20)
    plt.title(f'{task_prefix.capitalize()} — IoU Score', fontsize=20)
    plt.legend(loc='best', fontsize=16)
    plt.grid()
    plt.savefig(os.path.join(cfg.outputs_dir, f'{task_prefix}_iou_score_plot.png'))
    plt.close()

    # Loss plot
    plt.figure(figsize=(20, 8))
    plt.plot(train_logs_df.index.tolist(), train_logs_df.dice_loss.tolist(), lw=3, label='Train')
    plt.plot(valid_logs_df.index.tolist(), valid_logs_df.dice_loss.tolist(), lw=3, label='Valid')
    plt.xlabel('Epochs', fontsize=20)
    plt.ylabel('Combo Loss', fontsize=20)
    plt.title(f'{task_prefix.capitalize()} — Combo Loss (Dice + BCE)', fontsize=20)
    plt.legend(loc='best', fontsize=16)
    plt.grid()
    plt.savefig(os.path.join(cfg.outputs_dir, f'{task_prefix}_loss_plot.png'))
    plt.close()

    print(f"Plots saved to {cfg.outputs_dir}/")
    print(f"TensorBoard logs: tensorboard --logdir=runs")


if __name__ == '__main__':
    main()
