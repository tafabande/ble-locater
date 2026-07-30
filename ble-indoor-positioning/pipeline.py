"""
BLE Indoor Positioning — End-to-End Pipeline
=============================================

Runs the complete pipeline:
  1. Feature Engineering: raw CSVs → observation windows
  2. ML Training: observation windows → trained model
  3. Evaluation: metrics + diagnostic plots

Usage:
    python pipeline.py
    python pipeline.py --target-mac 52:06:26:03:01:DA
    python pipeline.py --target-mac 52:06:26:03:01:DA --tune
"""

import os
import sys
import argparse

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from feature_engineering.engineer import process_all_raw_csvs
from training.train import load_dataset, train_model, save_model, generate_plots


def main():
    parser = argparse.ArgumentParser(
        description="BLE Indoor Positioning — End-to-End Pipeline"
    )
    parser.add_argument(
        "--raw-dir",
        type=str,
        default=None,
        help="Directory with raw collector CSVs (default: ../ble tracker/collector/data/raw)"
    )
    parser.add_argument(
        "--target-mac",
        type=str,
        default=None,
        help="Filter for a specific BLE device MAC (e.g. 52:06:26:03:01:DA)"
    )
    parser.add_argument(
        "--model-type",
        type=str,
        choices=["random_forest", "gradient_boosting"],
        default="random_forest",
        help="ML model type"
    )
    parser.add_argument(
        "--tune",
        action="store_true",
        help="Run hyperparameter tuning"
    )
    args = parser.parse_args()

    # Resolve paths
    if args.raw_dir is None:
        # Look for raw data in the sibling 'ble tracker' project
        args.raw_dir = os.path.join(
            os.path.dirname(PROJECT_ROOT), "ble tracker", "collector", "data", "raw"
        )

    dataset_path = os.path.join(PROJECT_ROOT, "datasets", "observations.csv")
    model_dir    = os.path.join(PROJECT_ROOT, "models")
    reports_dir  = os.path.join(PROJECT_ROOT, "reports")

    # ── Step 1: Feature Engineering ──────────────────────────────────
    print("=" * 70)
    print("  STEP 1: FEATURE ENGINEERING")
    print("=" * 70)

    df = process_all_raw_csvs(args.raw_dir, dataset_path, target_mac=args.target_mac)

    # ── Step 2: Training ─────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  STEP 2: MODEL TRAINING")
    print("=" * 70)

    df = load_dataset(dataset_path)
    result = train_model(df, model_type=args.model_type, tune_hyperparams=args.tune)

    # ── Step 3: Save & Evaluate ──────────────────────────────────────
    print("\n" + "=" * 70)
    print("  STEP 3: SAVING MODEL & GENERATING REPORTS")
    print("=" * 70)

    save_model(result, model_dir)
    generate_plots(result, reports_dir)

    # ── Summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  [DONE] PIPELINE COMPLETE")
    print("=" * 70)
    print(f"  Engineered dataset : {dataset_path}")
    print(f"  Trained model      : {os.path.join(model_dir, 'distance_estimator.joblib')}")
    print(f"  Model scaler       : {os.path.join(model_dir, 'scaler.joblib')}")
    print(f"  Model metadata     : {os.path.join(model_dir, 'model_metadata.json')}")
    print(f"  Diagnostic plots   : {os.path.join(reports_dir, 'model_diagnostics.png')}")
    print(f"\n  Test MAE:  {result['metrics']['test_mae']:.4f} m")
    print(f"  Test R²:   {result['metrics']['test_r2']:.4f}")
    print("=" * 70)


if __name__ == "__main__":
    main()
