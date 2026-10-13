"""Unit & Integration Tests for Multi-Anchor Coordinate Regression in Server."""
import os
import sys
import time
import pytest
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from server.app import (
    shared, load_ml_assets, TagState, perform_localization,
    extract_multi_anchor_features, COORD_FEATURE_COLS
)


def test_coordinate_assets_loaded():
    """Verify coordinate model, scaler, and metadata are loaded into shared dict."""
    load_ml_assets()
    assert shared.get("coord_model") is not None, "Coordinate model was not loaded."
    assert shared.get("coord_scaler") is not None, "Coordinate scaler was not loaded."
    assert shared.get("coord_metadata") is not None, "Coordinate metadata was not loaded."


def test_feature_extraction_with_full_anchors():
    """Verify that extract_multi_anchor_features extracts 21 valid features."""
    tag = TagState("TEST_TAG_01", "Test Tag 1")
    now_ms = int(time.time() * 1000)

    tag.last_raw_packets["ANCHOR_01"].append((now_ms - 200, -65))
    tag.last_raw_packets["ANCHOR_02"].append((now_ms - 150, -70))
    tag.last_raw_packets["ANCHOR_03"].append((now_ms - 300, -68))
    tag.last_raw_packets["ANCHOR_04"].append((now_ms - 100, -72))

    feat = extract_multi_anchor_features(tag, now_ms)
    assert feat is not None
    assert feat.shape == (1, 21)
    assert np.all(np.isfinite(feat))


def test_feature_extraction_partial_anchors_3():
    """Verify feature extraction works with exactly 3 anchors and sensitivity floors 4th."""
    tag = TagState("TEST_TAG_02", "Test Tag 2")
    now_ms = int(time.time() * 1000)

    tag.last_raw_packets["ANCHOR_01"].append((now_ms - 200, -65))
    tag.last_raw_packets["ANCHOR_02"].append((now_ms - 150, -70))
    tag.last_raw_packets["ANCHOR_03"].append((now_ms - 300, -68))

    feat = extract_multi_anchor_features(tag, now_ms)
    assert feat is not None
    assert feat.shape == (1, 21)
    # ANCHOR_04_rssi should be floor (-100.0)
    assert feat[0, 3] == -100.0
    # ANCHOR_04_present should be 0.0
    assert feat[0, 11] == 0.0


def test_feature_extraction_insufficient_anchors():
    """Verify feature extraction returns None when fewer than 3 anchors are active."""
    tag = TagState("TEST_TAG_03", "Test Tag 3")
    now_ms = int(time.time() * 1000)

    tag.last_raw_packets["ANCHOR_01"].append((now_ms - 200, -65))
    tag.last_raw_packets["ANCHOR_02"].append((now_ms - 150, -70))

    feat = extract_multi_anchor_features(tag, now_ms)
    assert feat is None


def test_perform_localization_coordinate_champion():
    """Verify end-to-end perform_localization executes coordinate champion."""
    load_ml_assets()
    tag = TagState("TEST_TAG_04", "Test Tag 4")
    now_ms = int(time.time() * 1000)

    tag.last_raw_packets["ANCHOR_01"].append((now_ms - 100, -62))
    tag.last_raw_packets["ANCHOR_02"].append((now_ms - 100, -64))
    tag.last_raw_packets["ANCHOR_03"].append((now_ms - 100, -63))
    tag.last_raw_packets["ANCHOR_04"].append((now_ms - 100, -65))

    perform_localization(tag)

    assert tag.last_position is not None
    assert 0.0 <= tag.last_position["x"] <= 5.0
    assert 0.0 <= tag.last_position["y"] <= 5.0
    assert tag.last_position["uncertainty"] == 0.41
    assert tag.current_room != "Unknown"
