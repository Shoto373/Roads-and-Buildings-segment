"""
Evaluate trained model on the full test set.

Usage:
    python evaluate.py --task road                         # Evaluate road model
    python evaluate.py --task building                     # Evaluate building model
    python evaluate.py --task road --tta                   # With Test-Time Augmentation
    python evaluate.py --task road --weights weights/road_model_30_epochs.pth
"""

import os
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"
import json
import cv2
import numpy as np
import torch
import segmentation_models_pytorch as smp
from tqdm import tqdm

from config import parse_args
from inference import load_model, predict_single, to_tensor


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(pred_mask, gt_mask):
    """Compute binary segmentation metrics.

    Both inputs are 2D numpy arrays with values 0 or 1.
    Returns dict with IoU, Dice, Precision, Recall, F1, Accuracy.
    """
    pred = pred_mask.astype(bool).flatten()
    gt = gt_mask.astype(bool).flatten()

    tp = np.sum(pred & gt)
    fp = np.sum(pred & ~gt)
    fn = np.sum(~pred & gt)
    tn = np.sum(~pred & ~gt)

    eps = 1e-7
    precision = tp / (tp + fp + eps)
    recall = tp / (tp + fn + eps)
    f1 = 2 * precision * recall / (precision + recall + eps)
    accuracy = (tp + tn) / (tp + tn + fp + fn + eps)
    iou = tp / (tp + fp + fn + eps)
    dice = 2 * tp / (2 * tp + fp + fn + eps)

    return {
        'iou': float(iou),
        'dice': float(dice),
        'precision': float(precision),
        'recall': float(recall),
        'f1': float(f1),
        'accuracy': float(accuracy),
    }


def crop_image(img, target_size=1500):
    """Crop padded image back to original size."""
    padding = (img.shape[0] - target_size) // 2
    if padding <= 0:
        return img
    return img[padding:-padding, padding:-padding]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    cfg = parse_args(description="Evaluate segmentation model on test set")

    task = cfg.data.task
    use_tta = cfg._tta

    # Determine weights path
    weights_path = cfg._weights_path or cfg.best_model_path
    if not os.path.exists(weights_path):
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
    print(f"Task: {task}")
    print(f"Weights: {weights_path}")
    print(f"TTA: {use_tta}")

    model, is_logits = load_model(weights_path, DEVICE, cfg)

    preprocessing_fn = smp.encoders.get_preprocessing_fn(
        cfg.model.encoder, cfg.model.encoder_weights
    )

    # Test data
    image_paths = sorted([
        os.path.join(cfg.data.test_images_dir, f)
        for f in os.listdir(cfg.data.test_images_dir)
    ])
    mask_paths = sorted([
        os.path.join(cfg.data.test_masks_dir, f)
        for f in os.listdir(cfg.data.test_masks_dir)
    ])

    n_test = len(image_paths)
    print(f"\nEvaluating on {n_test} test images...\n")

    all_metrics = []

    for i in tqdm(range(n_test), desc="Evaluating"):
        image = cv2.cvtColor(cv2.imread(image_paths[i]), cv2.COLOR_BGR2RGB)
        gt_mask_rgb = cv2.imread(mask_paths[i], cv2.IMREAD_GRAYSCALE)
        gt_mask = (gt_mask_rgb > 127).astype(int)

        pred_mask = predict_single(
            model, image, preprocessing_fn,
            cfg.data.padded_size, DEVICE,
            use_tta=use_tta, is_logits=is_logits,
        )

        pred_mask_cropped = crop_image(pred_mask, target_size=cfg.data.image_size)

        # Ensure gt_mask matches dimensions
        gt_h, gt_w = gt_mask.shape[:2]
        pr_h, pr_w = pred_mask_cropped.shape[:2]
        min_h, min_w = min(gt_h, pr_h), min(gt_w, pr_w)
        gt_crop = gt_mask[:min_h, :min_w]
        pr_crop = pred_mask_cropped[:min_h, :min_w]

        metrics = compute_metrics(pr_crop, gt_crop)
        all_metrics.append(metrics)

    # Aggregate
    avg_metrics = {}
    for key in all_metrics[0].keys():
        values = [m[key] for m in all_metrics]
        avg_metrics[key] = float(np.mean(values))
        avg_metrics[f'{key}_std'] = float(np.std(values))

    # Print results
    print(f"\n{'='*60}")
    print(f"  Test Results - {task.upper()} segmentation")
    print(f"  Model: {weights_path}")
    if use_tta:
        print(f"  TTA: enabled")
    print(f"{'='*60}")
    print(f"  IoU:       {avg_metrics['iou']:.4f} +/- {avg_metrics['iou_std']:.4f}")
    print(f"  Dice:      {avg_metrics['dice']:.4f} +/- {avg_metrics['dice_std']:.4f}")
    print(f"  Precision: {avg_metrics['precision']:.4f} +/- {avg_metrics['precision_std']:.4f}")
    print(f"  Recall:    {avg_metrics['recall']:.4f} +/- {avg_metrics['recall_std']:.4f}")
    print(f"  F1:        {avg_metrics['f1']:.4f} +/- {avg_metrics['f1_std']:.4f}")
    print(f"  Accuracy:  {avg_metrics['accuracy']:.4f} +/- {avg_metrics['accuracy_std']:.4f}")
    print(f"{'='*60}")

    # Save to JSON
    os.makedirs(cfg.outputs_dir, exist_ok=True)
    tta_suffix = "_tta" if use_tta else ""
    output_path = os.path.join(cfg.outputs_dir, f'{task}_test_metrics{tta_suffix}.json')

    result = {
        'task': task,
        'weights': weights_path,
        'tta': use_tta,
        'n_test': n_test,
        'metrics': avg_metrics,
        'per_image': all_metrics,
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nMetrics saved to: {output_path}")


if __name__ == '__main__':
    main()
