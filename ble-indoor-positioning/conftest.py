import os
import sys
import shutil
import pytest

# Ensure ble-indoor-positioning package modules are importable during test runs
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

@pytest.fixture(scope="session", autouse=True)
def isolated_test_environment(tmp_path_factory):
    """
    Isolates all test runs from live production databases and schematics.
    Prevents SQLite write locks, permission errors, and workspace pollution.
    """
    temp_dir = tmp_path_factory.mktemp("ble_test_env")
    temp_dir_str = str(temp_dir)

    schematic_path = os.path.join(temp_dir_str, "schematic.json")
    asset_db_path = os.path.join(temp_dir_str, "asset_registry.db")
    alerts_db_path = os.path.join(temp_dir_str, "alerts.db")
    position_db_path = os.path.join(temp_dir_str, "position_history.db")
    calib_path = os.path.join(temp_dir_str, "learned_calibrations.json")
    pipeline_run_path = os.path.join(temp_dir_str, "last_pipeline_run.json")

    # Seed temporary schematic from project schematic if present
    orig_schematic = os.path.join(project_root, "models", "schematic.json")
    if os.path.exists(orig_schematic):
        try:
            shutil.copy2(orig_schematic, schematic_path)
        except Exception:
            pass

    # Export environment variables for isolation
    os.environ["BLE_SCHEMATIC_FILE"] = schematic_path
    os.environ["BLE_ASSET_DB_PATH"] = asset_db_path
    os.environ["BLE_ALERTS_DB_PATH"] = alerts_db_path
    os.environ["BLE_POSITION_DB_PATH"] = position_db_path
    os.environ["BLE_CALIBRATION_FILE"] = calib_path
    os.environ["BLE_PIPELINE_RUN_FILE"] = pipeline_run_path

    # Point any already-initialized shared server singletons to the isolated test stores
    try:
        import server.app as app_mod
        from server.asset_registry import AssetRegistry, SearchEngine
        from engineering.geofence_engine import GeofenceEngine, AlertHistoryDB

        app_mod.SCHEMATIC_FILE = schematic_path
        app_mod.shared["asset_registry"] = AssetRegistry(db_path=asset_db_path)
        app_mod.shared["search_engine"] = SearchEngine(app_mod.shared["asset_registry"])
        app_mod.shared["position_db"] = app_mod.PositionHistoryDB(db_path=position_db_path)
        app_mod.shared["online_learner"].calib_filepath = calib_path
        app_mod.shared["geofence_engine"] = GeofenceEngine()
        app_mod.shared["geofence_engine"].db = AlertHistoryDB(db_path=alerts_db_path)
    except Exception:
        pass

    yield temp_dir_str

    for key in ["BLE_SCHEMATIC_FILE", "BLE_ASSET_DB_PATH", "BLE_ALERTS_DB_PATH", "BLE_POSITION_DB_PATH", "BLE_CALIBRATION_FILE", "BLE_PIPELINE_RUN_FILE"]:
        os.environ.pop(key, None)
