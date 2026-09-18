"""Sync Unity simulator C# scripts into the automated builder script."""
import re
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPTS_DIR.parent
BUILD_SCRIPT = SCRIPTS_DIR / "build_unity_env.py"
SIM_ROOT = WORKSPACE_ROOT / "Unity_BLE_Simulator" / "Assets"


def main():
    if not BUILD_SCRIPT.exists():
        print(f"Error: {BUILD_SCRIPT} not found.")
        return

    with open(BUILD_SCRIPT, "r", encoding="utf-8") as f:
        text = f.read()

    hw_file = SIM_ROOT / "Scripts" / "HumanWalker.cs"
    if hw_file.exists():
        with open(hw_file, "r", encoding="utf-8") as f:
            hw_code = f.read()
        hw_pattern = r'human_walker_code = """using UnityEngine;.*?\n"""'
        text = re.sub(hw_pattern, lambda m: f'human_walker_code = """{hw_code}"""', text, flags=re.DOTALL)

    dc_file = SIM_ROOT / "Scripts" / "DoorController.cs"
    if dc_file.exists():
        with open(dc_file, "r", encoding="utf-8") as f:
            dc_code = f.read()
        dc_pattern = r'door_ctrl_code = """using UnityEngine;.*?\n"""'
        text = re.sub(dc_pattern, lambda m: f'door_ctrl_code = """{dc_code}"""', text, flags=re.DOTALL)

    sb_file = SIM_ROOT / "Editor" / "SceneBuilder.cs"
    if sb_file.exists():
        with open(sb_file, "r", encoding="utf-8") as f:
            sb_code = f.read()
        sb_pattern = r'scene_builder_code = """#if UNITY_EDITOR.*?\n"""'
        text = re.sub(sb_pattern, lambda m: f'scene_builder_code = """{sb_code}"""', text, flags=re.DOTALL)

    with open(BUILD_SCRIPT, "w", encoding="utf-8") as f:
        f.write(text)

    print("build_unity_env.py synced successfully!")


if __name__ == "__main__":
    main()
