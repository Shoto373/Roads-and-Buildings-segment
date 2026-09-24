"""
Helper script to download and verify the DeepGlobe Road Extraction dataset from Kaggle.
Dataset: https://www.kaggle.com/datasets/balraj98/deepglobe-road-extraction-dataset
"""

import os
import sys
import shutil
import argparse
import subprocess
from deepglobe_dataset import load_deepglobe_samples, find_deepglobe_root


def parse_args():
    parser = argparse.ArgumentParser(description="Download and verify DeepGlobe Road Extraction dataset")
    parser.add_argument(
        "--target-dir",
        type=str,
        default="notebooks/input/deepglobe-road-extraction-dataset",
        help="Destination directory for DeepGlobe dataset",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip download and only verify existing dataset files",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    target_dir = os.path.abspath(args.target_dir)

    print("=" * 65)
    print("  DeepGlobe Road Extraction Dataset Helper")
    print(f"  Target path: {target_dir}")
    print("=" * 65)

    os.makedirs(target_dir, exist_ok=True)

    # Check if dataset is already present
    train_samples, val_samples, test_samples = load_deepglobe_samples(target_dir)
    total_labeled = len(train_samples) + len(val_samples)

    if total_labeled > 0:
        print(f"\n[OK] Dataset already detected at: {target_dir}")
        print(f"     Found {total_labeled} labeled image-mask pairs.")
        print(f"     - Training split:   {len(train_samples)} samples")
        print(f"     - Validation split: {len(val_samples)} samples")
        print(f"     - Unlabeled test:   {len(test_samples)} samples")
        print("\nYou are ready to train! Example command:")
        print("  python train.py --task deepglobe --decoder DeepLabV3Plus --encoder resnet34 --batch-size 4")
        return

    if args.skip_download:
        print(f"\n[ERROR] No DeepGlobe images found in {target_dir}")
        sys.exit(1)

    # Attempt to download via Kaggle CLI
    print("\nAttempting automated download via Kaggle API...")
    kaggle_cmd = shutil.which("kaggle") or shutil.which("kaggle.exe")

    if not kaggle_cmd:
        # Check python -m kaggle
        try:
            subprocess.run([sys.executable, "-m", "kaggle", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            kaggle_cmd = f"{sys.executable} -m kaggle"
        except Exception:
            kaggle_cmd = None

    dataset_slug = "balraj98/deepglobe-road-extraction-dataset"

    if kaggle_cmd:
        print(f"Kaggle CLI found. Downloading {dataset_slug}...")
        try:
            cmd = f'kaggle datasets download -d {dataset_slug} -p "{target_dir}" --unzip'
            ret = subprocess.run(cmd, shell=True)
            if ret.returncode == 0:
                print("\n[SUCCESS] Dataset downloaded and extracted successfully!")
                train_samples, val_samples, _ = load_deepglobe_samples(target_dir)
                print(f"Total labeled pairs verified: {len(train_samples) + len(val_samples)}")
                return
        except Exception as e:
            print(f"Kaggle download failed: {e}")

    # Manual instructions if CLI not available or failed
    print("\n" + "!" * 65)
    print("  Kaggle API is not configured or download requires authentication.")
    print("  To download the dataset manually:")
    print("!" * 65)
    print(f"\n1. Go to: https://www.kaggle.com/datasets/{dataset_slug}")
    print("2. Click 'Download' (ZIP file ~1.5 GB)")
    print(f"3. Unpack the contents into this folder:\n   {target_dir}\n")
    print("4. Verify by running:")
    print("   python download_deepglobe.py --skip-download\n")


if __name__ == "__main__":
    main()
