"""Unit tests for Model DB Registry and Academic Monograph Renderer."""
import re
import tempfile
from pathlib import Path
import pytest

from training.model_db import (
    init_db,
    log_training_session,
    get_latest_session,
    get_db_stats,
    get_db_connection
)
from training.report_renderer import render_academic_html_report


def test_sqlite_model_db_logging():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_registry.db"
        init_db(db_path)

        mock_metadata = {
            "session_id": "test_session_001",
            "champion_model": "XGBoost (Deep Tuned)",
            "trained_at": "2026-10-02T12:00:00",
            "train_samples": 12000,
            "test_samples": 3000,
            "feature_cols": ["f1", "f2", "f3"],
            "metrics": {
                "test_mae": 0.4063,
                "test_rmse": 0.8590,
                "test_r2": 0.7810,
                "test_median_ae": 0.1049,
                "tolerances": {"within_50cm": 77.2, "within_100cm": 88.6, "within_150cm": 92.8},
                "extended": {"per_distance_mae": {"0.5m": 0.0437, "1.0m": 0.6235, "7.0m": 1.4247}},
                "cv_metrics": {"cv_mae_mean": 0.4060}
            },
            "importances": {"f1": 0.5, "f2": 0.3, "f3": 0.2},
            "tournament": [
                {"name": "XGBoost (Deep Tuned)", "mae": 0.4063, "rmse": 0.8590, "r2": 0.7810, "med_ae": 0.1049},
                {"name": "LightGBM (Deep Tuned)", "mae": 0.4116, "rmse": 0.8725, "r2": 0.7741, "med_ae": 0.0980}
            ],
            "effective_config": {"dataset": "observations.csv", "n_windows_after_filter": 33741}
        }

        sess_id = log_training_session(mock_metadata, db_path=db_path)
        assert sess_id == "test_session_001"

        stats = get_db_stats(db_path=db_path)
        assert stats["total_sessions"] == 1
        assert stats["total_tournament_entries"] == 2
        assert stats["total_feature_attributions"] == 3
        assert stats["total_spatial_telemetry_points"] == 3

        latest = get_latest_session(db_path=db_path)
        assert latest is not None
        assert latest["session_id"] == "test_session_001"
        assert latest["champion_model"] == "XGBoost (Deep Tuned)"
        assert len(latest["tournament"]) == 2
        assert len(latest["spatial_decay"]) == 3


def test_academic_html_report_rendering_no_emojis():
    with tempfile.TemporaryDirectory() as tmp_dir:
        report_dir = Path(tmp_dir)
        report_path = render_academic_html_report(reports_dir=report_dir)
        assert report_path.exists()

        content = report_path.read_text(encoding="utf-8")

        # 1. Zero emojis
        emoji_pattern = re.compile(
            r"[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf\U0001f300-\U0001f64f\U0001f680-\U0001f6ff]"
        )
        found_emojis = emoji_pattern.findall(content)
        assert len(found_emojis) == 0, f"Disallowed emojis detected: {found_emojis}"

        # 2. Key Academic Sections Present
        assert "Technical Research Monograph" in content
        assert "TR-BLE-2026-RTLS-04" in content
        assert 'class="sec-num">1.0</span> Statistical Nomenclature &amp; Evaluation Metrics' in content
        assert 'class="sec-num">2.0</span> Primary Empirical Findings &amp; Executive Performance Matrix' in content
        assert 'class="sec-num">3.0</span> Algorithmic Tournament Benchmark: The 19-Model Evaluation Matrix' in content
        assert 'class="sec-num">4.0</span> Spatial Error Distribution &amp; Distance Decay Dynamics' in content
        assert 'class="sec-num">5.0</span> Feature Permutation Attribution &amp; Parametric Sensitivity' in content
        assert 'class="sec-num">6.0</span> Theoretical Synthesis &amp; Bias-Variance Analysis' in content
        assert 'class="sec-num">7.0</span> Operational Engineering Directives &amp; Topological Deployment' in content
        assert 'class="sec-num">8.0</span> Database Schematics, Logging &amp; Audit Telemetry' in content
        assert 'class="sec-num">9.0</span> Methodological Reproducibility &amp; Environmental Specifications' in content

        # 3. Vector Icons Present
        assert "<svg" in content
        assert "viewBox=" in content

        # 4. Actual Light and Dark Themes (No Blue Theme)
        assert "Paper Mode: Light" in content
        assert "theme-dark" in content
        assert "--bg: #f9fafb;" in content
        assert "--bg: #0f1117;" in content

        # 5. Real Data & Provenance
        assert "XGBoost (Deep Tuned)" in content
        assert "0.4063" in content
        assert "33,741" in content
