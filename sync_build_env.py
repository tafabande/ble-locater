import re

def main():
    with open('build_unity_env.py', 'r') as f:
        text = f.read()
    with open('Unity_BLE_Simulator/Assets/Scripts/HumanWalker.cs', 'r') as f:
        hw_code = f.read()
    hw_pattern = 'human_walker_code = """using UnityEngine;.*?\\}' + '\n' + '"""'
    text = re.sub(hw_pattern, f'human_walker_code = """{hw_code}"""', text, flags=re.DOTALL)
    with open('Unity_BLE_Simulator/Assets/Scripts/DoorController.cs', 'r') as f:
        dc_code = f.read()
    dc_pattern = 'door_ctrl_code = """using UnityEngine;.*?\\}' + '\n' + '"""'
    text = re.sub(dc_pattern, f'door_ctrl_code = """{dc_code}"""', text, flags=re.DOTALL)
    with open('Unity_BLE_Simulator/Assets/Editor/SceneBuilder.cs', 'r') as f:
        sb_code = f.read()
    sb_pattern = 'scene_builder_code = """#if UNITY_EDITOR.*?#endif' + '\n' + '"""'
    text = re.sub(sb_pattern, f'scene_builder_code = """{sb_code}"""', text, flags=re.DOTALL)
    with open('build_unity_env.py', 'w') as f:
        f.write(text)
    print('build_unity_env.py synced successfully!')
if __name__ == '__main__':
    main()
