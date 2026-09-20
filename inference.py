"""
Unified inference script for road and building segmentation.

Usage:
    python inference.py --task road                        # Single demo (index 0)
    python inference.py --task road --idx 3                # Demo on test image #3
    python inference.py --task road --num-examples 10      # Generate 10 examples
    python inference.py --task building --tta              # With Test-Time Augmentation
    python inference.py --task road --weights weights/road_model_30_epochs.pth  # Custom weights
"""

import os
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"
import cv2
import json
import numpy as np
import torch
import albumentations as album
import segmentation_models_pytorch as smp
import matplotlib.pyplot as plt
from tqdm import tqdm

from config import parse_args


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def to_tensor(x, **kwargs):
    return x.transpose(2, 0, 1).astype('float32')


def crop_image(img, target_size=1500):
    """Crop padded image back to original size."""
    padding = (img.shape[0] - target_size) // 2
    if padding <= 0:
        return img
    return img[padding:-padding, padding:-padding]


def colour_code_segmentation(mask, class_rgb_values):
    """Convert class index mask to RGB."""
    colour_codes = np.array(class_rgb_values)
    return colour_codes[mask.astype(int)]


# ---------------------------------------------------------------------------
# Model loading (supports both new state_dict and legacy pickle formats)
# ---------------------------------------------------------------------------

def load_model(weights_path, device, cfg=None):
    """Load model from checkpoint (state_dict) or legacy pickle format."""
    print(f"Loading model from: {weights_path}")

    checkpoint = torch.load(weights_path, map_location=device, weights_only=False)

    if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
        # New format: state_dict checkpoint
        ckpt_cfg = checkpoint.get('config', {})
        encoder = ckpt_cfg.get('encoder', cfg.model.encoder if cfg else 'efficientnet-b7')
        decoder = ckpt_cfg.get('decoder', cfg.model.decoder if cfg else 'Unet')
        classes = ckpt_cfg.get('classes', cfg.model.classes if cfg else 1)

        decoder_map = {
            "Unet": smp.Unet,
            "UnetPlusPlus": smp.UnetPlusPlus,
            "DeepLabV3Plus": smp.DeepLabV3Plus,
        }
        model = decoder_map[decoder](
            encoder_name=encoder,
            encoder_weights=None,  # Loading from checkpoint
            classes=classes,
            activation=None,
        )
        model.load_state_dict(checkpoint['model_state_dict'])
        print(f"  Loaded state_dict checkpoint (epoch {checkpoint.get('epoch', '?')}, "
              f"IoU {checkpoint.get('best_iou', '?'):.4f})")
        is_logits = True  # New models output logits
    else:
        # Legacy format: pickled full model
        model = checkpoint
        print("  Loaded legacy pickle model")
        is_logits = False  # Legacy models have sigmoid activation

    model = model.to(device)
    model.eval()
    return model, is_logits


# ---------------------------------------------------------------------------
# Inference with optional TTA
# ---------------------------------------------------------------------------

def predict_single(model, image, preprocessing_fn, padded_size, device, use_tta=False, is_logits=True):
    """Run inference on a single image, optionally with TTA."""
    test_transform = album.Compose([
        album.PadIfNeeded(min_height=padded_size, min_width=padded_size, border_mode=0),
    ])

    def _infer(img):
        padded = test_transform(image=img)['image']
        normed = preprocessing_fn(padded)
        tensor = torch.from_numpy(to_tensor(normed)).to(device).unsqueeze(0)
        with torch.no_grad():
            output = model(tensor)
        if is_logits:
            prob = torch.sigmoid(output)
        else:
            prob = output
        return prob.squeeze(0).cpu().numpy()  # (C, H, W)

    # Base prediction
    pred = _infer(image)

    if use_tta:
        # Horizontal flip
        pred_hflip = _infer(np.fliplr(image).copy())
        pred_hflip = pred_hflip[:, :, ::-1]  # Flip back

        # Vertical flip
        pred_vflip = _infer(np.flipud(image).copy())
        pred_vflip = pred_vflip[:, ::-1, :]  # Flip back

        # Average
        pred = (pred + pred_hflip + pred_vflip) / 3.0

    # For classes=1, pred shape is (1, H, W) → threshold → (H, W)
    if pred.shape[0] == 1:
        pred_mask = (pred[0] > 0.5).astype(int)
    else:
        # Legacy classes=2: argmax
        pred_binary = (pred > 0.5).astype(float)
        pred_mask = np.argmax(pred_binary, axis=0)

    return pred_mask


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    cfg = parse_args(description="Run inference on test images")

    os.makedirs(cfg.outputs_dir, exist_ok=True)

    task = cfg.data.task
    num_examples = cfg._num_examples
    idx = cfg._idx
    use_tta = cfg._tta

    # Determine weights path
    weights_path = cfg._weights_path or cfg.best_model_path
    if not os.path.exists(weights_path):
        # Fallback to legacy naming
        legacy_paths = {
            'road': 'weights/best_road_model.pth',
            'building': 'weights/best_model.pth',
        }
        weights_path = legacy_paths.get(task, weights_path)

    if not os.path.exists(weights_path):
        print(f"ERROR: Weights file not found: {weights_path}")
        return

    # Setup
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {DEVICE}")

    model, is_logits = load_model(weights_path, DEVICE, cfg)

    preprocessing_fn = smp.encoders.get_preprocessing_fn(
        cfg.model.encoder, cfg.model.encoder_weights
    )

    class_rgb_values = [[0, 0, 0], [255, 255, 255]]

    tta_suffix = "_tta" if use_tta else ""

    # Custom image inference mode
    custom_image_path = getattr(cfg, '_input_image', None)
    if custom_image_path:
        if not os.path.exists(custom_image_path):
            print(f"ERROR: Custom image not found: {custom_image_path}")
            return
        image = cv2.cvtColor(cv2.imread(custom_image_path), cv2.COLOR_BGR2RGB)
        orig_h, orig_w = image.shape[:2]
        padded_h = max(cfg.data.padded_size, int(np.ceil(orig_h / 32.0) * 32))
        padded_w = max(cfg.data.padded_size, int(np.ceil(orig_w / 32.0) * 32))
        pad_size = max(padded_h, padded_w)

        print(f"Processing custom image: {custom_image_path} ({orig_w}x{orig_h})")
        pred_mask = predict_single(
            model, image, preprocessing_fn,
            pad_size, DEVICE,
            use_tta=use_tta, is_logits=is_logits,
        )
        pred_mask_cropped = pred_mask[:orig_h, :orig_w]
        pred_colored = colour_code_segmentation(pred_mask_cropped, class_rgb_values)

        # Plot comparison
        plt.figure(figsize=(14, 7))
        plt.subplot(1, 2, 1)
        plt.title("Input Image", fontsize=14)
        plt.axis('off')
        plt.imshow(image)

        plt.subplot(1, 2, 2)
        plt.title(f"Prediction - {task.capitalize()}{' (TTA)' if use_tta else ''}", fontsize=14)
        plt.axis('off')
        plt.imshow(pred_colored)

        base_name = os.path.splitext(os.path.basename(custom_image_path))[0]
        out_vis = os.path.join(cfg.outputs_dir, f'{base_name}_{task}_prediction{tta_suffix}.png')
        out_mask = os.path.join(cfg.outputs_dir, f'{base_name}_{task}_mask{tta_suffix}.png')
        plt.savefig(out_vis, bbox_inches='tight', dpi=150)
        plt.close()

        # Also save binary mask (0 or 255)
        cv2.imwrite(out_mask, (pred_mask_cropped * 255).astype(np.uint8))
        print(f"Visualization saved to: {out_vis}")
        print(f"Binary mask saved to: {out_mask}")
        return

    # Batch test set inference
    image_paths = sorted([
        os.path.join(cfg.data.test_images_dir, f)
        for f in os.listdir(cfg.data.test_images_dir)
    ])
    mask_paths = sorted([
        os.path.join(cfg.data.test_masks_dir, f)
        for f in os.listdir(cfg.data.test_masks_dir)
    ])

    if num_examples == 1:
        # Single demo mode
        indices = [idx]
    else:
        indices = list(range(min(num_examples, len(image_paths))))

    tta_suffix = "_tta" if use_tta else ""

    print(f"\nGenerating {len(indices)} example(s) for '{task}' segmentation...")
    if use_tta:
        print("  TTA enabled (original + hflip + vflip)")

    for i in tqdm(indices, desc="Inference"):
        image = cv2.cvtColor(cv2.imread(image_paths[i]), cv2.COLOR_BGR2RGB)
        mask = cv2.cvtColor(cv2.imread(mask_paths[i]), cv2.COLOR_BGR2RGB)

        pred_mask = predict_single(
            model, image, preprocessing_fn,
            cfg.data.padded_size, DEVICE,
            use_tta=use_tta, is_logits=is_logits,
        )

        pred_mask_cropped = crop_image(pred_mask, target_size=cfg.data.image_size)
        pred_colored = colour_code_segmentation(pred_mask_cropped, class_rgb_values)

        # Plot
        plt.figure(figsize=(20, 8))

        plt.subplot(1, 3, 1)
        plt.title(f"Original Test Image {i+1}", fontsize=14)
        plt.axis('off')
        plt.imshow(image)

        plt.subplot(1, 3, 2)
        plt.title("Ground Truth Mask", fontsize=14)
        plt.axis('off')
        plt.imshow(mask)

        plt.subplot(1, 3, 3)
        title = f"Prediction — {task.capitalize()}"
        if use_tta:
            title += " (TTA)"
        plt.title(title, fontsize=14)
        plt.axis('off')
        plt.imshow(pred_colored)

        if len(indices) == 1:
            out_path = os.path.join(cfg.outputs_dir, f'{task}_demo{tta_suffix}_output.png')
        else:
            out_path = os.path.join(cfg.outputs_dir, f'{task}_example_{i+1}{tta_suffix}.png')

        plt.savefig(out_path, bbox_inches='tight', dpi=150)
        plt.close()

    print(f"\nResults saved to {cfg.outputs_dir}/")


if __name__ == '__main__':
    main()
