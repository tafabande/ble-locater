"""Indoor Positioning — Explicit Model Export & Versioning Engine.

Handles intentional promotion of candidate models to production,
version tagging, metadata preservation, and non-destructive backups.
"""
from __future__ import annotations

import datetime
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import joblib

import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import MODELS_DIR, REPORTS_DIR


class ModelExporter:
    """Manages deliberate export and versioning of trained positioning models."""

    @staticmethod
    def export_champion_model(
        candidate_model: Any,
        candidate_scaler: Any,
        metadata: Dict[str, Any],
        version_tag: Optional[str] = None,
        target_dir: Optional[Path] = None,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Explicitly promote a candidate trained model to the active production model."""
        m_dir = Path(target_dir) if target_dir else MODELS_DIR
        m_dir.mkdir(parents=True, exist_ok=True)

        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        tag = version_tag or f"v_{now_str}"

        prod_model_path = m_dir / "distance_estimator.joblib"
        prod_scaler_path = m_dir / "scaler.joblib"
        prod_meta_path = m_dir / "model_metadata.json"

        # 1. Create safety backup of existing production models if present
        if prod_model_path.exists():
            backup_model = m_dir / f"distance_estimator_backup_{now_str}.joblib"
            shutil.copy2(prod_model_path, backup_model)
        if prod_meta_path.exists():
            backup_meta = m_dir / f"model_metadata_backup_{now_str}.json"
            shutil.copy2(prod_meta_path, backup_meta)

        try:
            # 2. Save candidate model and scaler
            joblib.dump(candidate_model, prod_model_path)
            joblib.dump(candidate_scaler, prod_scaler_path)

            # 3. Enrich metadata with explicit export tracking
            export_meta = dict(metadata)
            export_meta["version_tag"] = tag
            export_meta["exported_at"] = datetime.datetime.now().isoformat()
            export_meta["feature_schema_version"] = "2.0"

            with open(prod_meta_path, "w", encoding="utf-8") as f:
                json.dump(export_meta, f, indent=2)

            return True, f"Model successfully exported to production as '{tag}'.", export_meta

        except Exception as e:
            return False, f"Failed to export model artifacts: {e}", {}
