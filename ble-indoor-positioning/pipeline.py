"""
BLE Indoor Positioning — End-to-End Pipeline
=============================================

Runs the complete pipeline:
  1. Feature Engineering: raw CSVs → observation windows (38 features)
  2. ML Training: observation windows → trained model (regression + zone classification)
  3. Evaluation: metrics + diagnostic plots

Usage:
    python pipeline.py
    python pipeline.py --target-mac 52:06:26:03:01:DA
    python pipeline.py --target-mac 52:06:26:03:01:DA --tune
    python pipeline.py --mode regression
    python pipeline.py --mode classification
    python pipeline.py --mode both
"""

import os
import sys
import argparse

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from feature_engineering.engineer import process_all_raw_csvs
from training.train import load_dataset, train_model, train_zone_classifier, save_model, generate_plots


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
    parser.add_argument(
        "--mode",
        type=str,
        choices=["regression", "classification", "both"],
        default="both",
        help="Training mode: regression, classification (zones), or both (default)"
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
    print("  STEP 1: FEATURE ENGINEERING (38 Features)")
    print("=" * 70)

    df = process_all_raw_csvs(args.raw_dir, dataset_path, target_mac=args.target_mac)

    # ── Step 2: Training ─────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  STEP 2: MODEL TRAINING")
    print("=" * 70)

    df = load_dataset(dataset_path)

    result = None
    zone_result = None

    if args.mode in ("regression", "both"):
        print("\n" + "-" * 70)
        print("  STEP 2a: REGRESSION TOURNAMENT")
        print("-" * 70)
        result = train_model(df, model_type=args.model_type, tune_hyperparams=args.tune)

    if args.mode in ("classification", "both"):
        print("\n" + "-" * 70)
        print("  STEP 2b: ZONE CLASSIFICATION TOURNAMENT")
        print("-" * 70)
        zone_result = train_zone_classifier(df)

    # ── Step 3: Save & Evaluate ──────────────────────────────────────
    print("\n" + "=" * 70)
    print("  STEP 3: SAVING MODEL & GENERATING REPORTS")
    print("=" * 70)

    if result:
        save_model(result, model_dir, zone_result=zone_result)
        generate_plots(result, reports_dir, zone_result=zone_result)

    # ── Summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  [DONE] PIPELINE COMPLETE")
    print("=" * 70)
    print(f"  Engineered dataset : {dataset_path}")
    print(f"  Trained model      : {os.path.join(model_dir, 'distance_estimator.joblib')}")
    print(f"  Model scaler       : {os.path.join(model_dir, 'scaler.joblib')}")
    print(f"  Model metadata     : {os.path.join(model_dir, 'model_metadata.json')}")
    print(f"  Diagnostic plots   : {os.path.join(reports_dir, 'model_diagnostics.png')}")

    if result:
        print(f"\n  [REGRESSION]")
        print(f"  Test MAE:  {result['metrics']['test_mae']:.4f} m")
        print(f"  Test R²:   {result['metrics']['test_r2']:.4f}")
        print(f"  Champion:  {result['model_type']}")

    if zone_result and zone_result.get("zone_accuracy"):
        print(f"\n  [ZONE CLASSIFICATION]")
        print(f"  Zone Accuracy: {zone_result['zone_accuracy']:.2f}%")
        print(f"  Zone Champion: {zone_result['champion_name']}")
        print(f"  Zone Model:    {os.path.join(model_dir, 'zone_classifier.joblib')}")

    print("=" * 70)


if __name__ == "__main__":
    main()
