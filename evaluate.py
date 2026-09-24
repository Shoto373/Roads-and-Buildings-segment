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
from deepglobe_dataset import load_deepglobe_samples


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_relaxed_metrics(pred_mask, gt_mask, slacks=(2, 3, 5)):
    """Compute relaxed segmentation metrics with spatial tolerance buffer (slack).

    Standard benchmark metric for road extraction (Mnih 2013, SpaceNet, DeepGlobe).
    For a given slack distance rho:
    - A predicted road pixel is considered a true positive if it lies within rho
      pixels of any ground truth road pixel (Relaxed Precision).
    - A ground truth road pixel is considered detected if it lies within rho
      pixels of any predicted road pixel (Relaxed Recall).
    - Relaxed F1 and Relaxed IoU:
      IoU_relaxed = F1_relaxed / (2 - F1_relaxed)
    """
    pred = (pred_mask > 0).astype(np.uint8)
    gt = (gt_mask > 0).astype(np.uint8)
    eps = 1e-7

    n_pred = int(np.sum(pred))
    n_gt = int(np.sum(gt))

    relaxed_metrics = {}

    for s in slacks:
        if n_pred == 0 and n_gt == 0:
            relaxed_metrics[f'relaxed_{s}px_iou'] = 1.0
            relaxed_metrics[f'relaxed_{s}px_f1'] = 1.0
            relaxed_metrics[f'relaxed_{s}px_precision'] = 1.0
            relaxed_metrics[f'relaxed_{s}px_recall'] = 1.0
            continue
        elif n_pred == 0 or n_gt == 0:
            relaxed_metrics[f'relaxed_{s}px_iou'] = 0.0
            relaxed_metrics[f'relaxed_{s}px_f1'] = 0.0
            relaxed_metrics[f'relaxed_{s}px_precision'] = 0.0
            relaxed_metrics[f'relaxed_{s}px_recall'] = 0.0
            continue

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * s + 1, 2 * s + 1))
        gt_dil = cv2.dilate(gt, kernel)
        pred_dil = cv2.dilate(pred, kernel)

        tp_pred = np.sum((pred & gt_dil).astype(bool))
        tp_gt = np.sum((gt & pred_dil).astype(bool))

        rel_prec = tp_pred / (n_pred + eps)
        rel_rec = tp_gt / (n_gt + eps)
        rel_f1 = 2 * rel_prec * rel_rec / (rel_prec + rel_rec + eps)
        rel_iou = rel_f1 / (2 - rel_f1 + eps)

        relaxed_metrics[f'relaxed_{s}px_iou'] = float(rel_iou)
        relaxed_metrics[f'relaxed_{s}px_f1'] = float(rel_f1)
        relaxed_metrics[f'relaxed_{s}px_precision'] = float(rel_prec)
        relaxed_metrics[f'relaxed_{s}px_recall'] = float(rel_rec)

    return relaxed_metrics


def compute_metrics(pred_mask, gt_mask, slacks=(2, 3, 5)):
    """Compute binary segmentation metrics (strict and relaxed).

    Both inputs are 2D numpy arrays with values 0 or 1.
    Returns dict with strict and relaxed IoU, Dice, Precision, Recall, Accuracy.
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

    metrics = {
        'iou': float(iou),
        'dice': float(dice),
        'precision': float(precision),
        'recall': float(recall),
        'f1': float(f1),
        'accuracy': float(accuracy),
    }

    # Add relaxed metrics with buffer tolerance
    if slacks:
        relaxed = compute_relaxed_metrics(pred_mask, gt_mask, slacks=slacks)
        metrics.update(relaxed)

    return metrics


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
    if cfg.data.task == "deepglobe":
        _, val_samples, _ = load_deepglobe_samples(cfg.data.dataset_dir)
        if len(val_samples) == 0:
            raise FileNotFoundError(f"No labeled validation samples found in: {cfg.data.dataset_dir}")
        image_paths = [p[0] for p in val_samples]
        mask_paths = [p[1] for p in val_samples]
    else:
        image_paths = sorted([
            os.path.join(cfg.data.test_images_dir, f)
            for f in os.listdir(cfg.data.test_images_dir)
        ])
        mask_paths = sorted([
            os.path.join(cfg.data.test_masks_dir, f)
            for f in os.listdir(cfg.data.test_masks_dir)
        ])

    if getattr(cfg, '_limit', None):
        image_paths = image_paths[:cfg._limit]
        mask_paths = mask_paths[:cfg._limit]

    n_test = len(image_paths)
    slacks = getattr(cfg, '_slacks', (2, 3, 5))
    print(f"\nEvaluating on {n_test} test images (Relaxed slacks: {slacks} px)...\n")

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

        metrics = compute_metrics(pr_crop, gt_crop, slacks=slacks)
        all_metrics.append(metrics)

    # Aggregate
    avg_metrics = {}
    for key in all_metrics[0].keys():
        values = [m[key] for m in all_metrics]
        avg_metrics[key] = float(np.mean(values))
        avg_metrics[f'{key}_std'] = float(np.std(values))

    # Print results
    print(f"\n{'='*65}")
    print(f"  Test Results - {task.upper()} segmentation")
    print(f"  Model: {weights_path}")
    if use_tta:
        print(f"  TTA: enabled")
    print(f"{'='*65}")
    print(f"  [STRICT METRICS - EXACT PIXEL-TO-PIXEL MATCH]")
    print(f"  Strict IoU:       {avg_metrics['iou']:.4f} +/- {avg_metrics['iou_std']:.4f} ({avg_metrics['iou']*100:.2f}%)")
    print(f"  Strict Dice/F1:   {avg_metrics['dice']:.4f} +/- {avg_metrics['dice_std']:.4f} ({avg_metrics['dice']*100:.2f}%)")
    print(f"  Strict Precision: {avg_metrics['precision']:.4f} +/- {avg_metrics['precision_std']:.4f} ({avg_metrics['precision']*100:.2f}%)")
    print(f"  Strict Recall:    {avg_metrics['recall']:.4f} +/- {avg_metrics['recall_std']:.4f} ({avg_metrics['recall']*100:.2f}%)")
    print(f"  Pixel Accuracy:   {avg_metrics['accuracy']:.4f} +/- {avg_metrics['accuracy_std']:.4f} ({avg_metrics['accuracy']*100:.2f}%)")
    
    # Relaxed metrics printout
    has_relaxed = any(k.startswith('relaxed_') for k in avg_metrics.keys())
    if has_relaxed:
        print(f"{'-'*65}")
        print(f"  [RELAXED METRICS - GIS/MNIH BENCHMARK WITH SPATIAL TOLERANCE]")
        for s in slacks:
            if f'relaxed_{s}px_iou' in avg_metrics:
                iou_val = avg_metrics[f'relaxed_{s}px_iou']
                iou_std = avg_metrics.get(f'relaxed_{s}px_iou_std', 0.0)
                rec_val = avg_metrics.get(f'relaxed_{s}px_recall', 0.0)
                prec_val = avg_metrics.get(f'relaxed_{s}px_precision', 0.0)
                print(f"  Slack {s} px:")
                print(f"    • Relaxed IoU:       {iou_val:.4f} +/- {iou_std:.4f} ({iou_val*100:.2f}%)")
                print(f"    • Relaxed Precision: {prec_val:.4f} ({prec_val*100:.2f}%)")
                print(f"    • Relaxed Recall:    {rec_val:.4f} ({rec_val*100:.2f}%)")
    print(f"{'='*65}")

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
