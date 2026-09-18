"""Inject learned path-loss calibrations into Unity simulator scripts."""
import json
import re
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
CALIBRATION_FILE = WORKSPACE_ROOT / "ble-indoor-positioning" / "models" / "learned_calibrations.json"
BUILD_SCRIPT = Path(__file__).resolve().parent / "build_unity_env.py"
UNITY_SIM_SCRIPT = WORKSPACE_ROOT / "Unity_BLE_Simulator" / "Assets" / "Scripts" / "BLESimulator.cs"

if CALIBRATION_FILE.exists():
    with open(CALIBRATION_FILE, "r") as f:
        data = json.load(f)
    etas = [v["eta"] for v in data.get("anchors", {}).values() if "eta" in v]
    avg_eta = sum(etas) / len(etas) if etas else 2.5
else:
    avg_eta = 2.5


def inject_in_file(filepath: Path) -> None:
    if not filepath.exists():
        return
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    content = re.sub(
        r"public float pathLossExponentClear = [\d.]+f;",
        f"public float pathLossExponentClear = {avg_eta:.1f}f;",
        content,
    )
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    inject_in_file(BUILD_SCRIPT)
    inject_in_file(UNITY_SIM_SCRIPT)
    print(f"Injected calibrations successfully (avg_eta: {avg_eta:.2f}).")
