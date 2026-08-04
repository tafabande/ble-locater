"""
End-to-End Pipeline
===================
1. Feature Engineering (raw CSVs -> features)
2. ML Training (train regression & zone models)
3. Evaluation & Diagnostic Plots
"""

import os
import sys
import json
import argparse
import time
import builtins

START_TIME = time.time()

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from feature_engineering.engineer import process_all_raw_csvs
from training.train import load_dataset, train_model, train_zone_classifier, save_model, generate_plots


def progress(stage: str, percent: int, metrics: dict = None):
    """Emit JSON progress for GUI tracking."""
    event = {
        "type": "progress", 
        "stage": stage, 
        "percent": percent,
        "elapsed": round(time.time() - START_TIME, 1)
    }
    if metrics:
        event["metrics"] = metrics
    # Use original print to guarantee raw JSON bypass
    original_print(json.dumps(event), flush=True)

# ── Global JSON Print wrapper ──
original_print = builtins.print
def json_print(*args, **kwargs):
    text = " ".join(str(a) for a in args)
    if text.strip().startswith('{') and text.strip().endswith('}'):
        original_print(text, **kwargs)
    else:
        original_print(json.dumps({"type": "log", "message": text}), **kwargs)
builtins.print = json_print

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
    parser.add_argument(
        "--drop-duplicates",
        action="store_true",
        help="Drop packets flagged as duplicate_candidate in raw CSVs"
    )
    parser.add_argument(
        "--eval-mode",
        type=str,
        choices=["balanced_session", "strict_session", "random"],
        default="balanced_session",
        help="Evaluation mode for train/test split"
    )
    args = parser.parse_args()

    # Resolve paths
    if args.raw_dir is None:
        args.raw_dir = os.path.join(
            os.path.dirname(PROJECT_ROOT), "ble tracker", "collector", "data", "raw"
        )

    dataset_path = os.path.join(PROJECT_ROOT, "datasets", "observations.csv")
    model_dir    = os.path.join(PROJECT_ROOT, "models")
    reports_dir  = os.path.join(PROJECT_ROOT, "reports")

    # ── Step 1: Feature Engineering ──────────────────────────────────
    progress("Scanning & Engineering Features from Raw CSVs...", 5)
    print("=" * 70)
    print("  STEP 1: FEATURE ENGINEERING (60 Features)")
    print("=" * 70)

    df = process_all_raw_csvs(
        args.raw_dir, 
        dataset_path, 
        target_mac=args.target_mac, 
        drop_duplicates=args.drop_duplicates,
        progress_callback=progress
    )

    progress("Dataset Engineered. Loading Observations...", 35)

    # ── Step 2: Training ─────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  STEP 2: MODEL TRAINING")
    print("=" * 70)

    df = load_dataset(dataset_path)

    result = None
    zone_result = None

    if args.mode in ("regression", "both"):
        progress("Running Super Learner Regression Tournament...", 45)
        print("\n" + "-" * 70)
        print("  STEP 2a: REGRESSION TOURNAMENT")
        print("-" * 70)
        result = train_model(df, tune_hyperparams=args.tune, eval_mode=args.eval_mode, progress_callback=progress)

    if args.mode in ("classification", "both"):
        progress("Running Zone Classification Tournament...", 85)
        print("\n" + "-" * 70)
        print("  STEP 2b: ZONE CLASSIFICATION TOURNAMENT")
        print("-" * 70)
        zone_result = train_zone_classifier(df, progress_callback=progress)

    # ── Step 3: Save & Evaluate ──────────────────────────────────────
    progress("Saving Champion Artifacts & Diagnostic Plots...", 90)
    print("\n" + "=" * 70)
    print("  STEP 3: SAVING MODEL & GENERATING REPORTS")
    print("=" * 70)

    if result:
        save_model(result, model_dir, zone_result=zone_result)
        generate_plots(result, reports_dir, zone_result=zone_result)

    # Prepare summary metrics
    summary_metrics = {
        "windows": len(df),
        "mae": result["metrics"]["test_mae"] if result else 0.0,
        "r2": result["metrics"]["test_r2"] if result else 0.0,
        "zone_acc": zone_result.get("zone_accuracy", 0.0) if zone_result else 0.0
    }

    progress("Pipeline Complete!", 100, metrics=summary_metrics)

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
