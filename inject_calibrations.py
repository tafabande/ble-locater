import json
import re

with open('ble-indoor-positioning/models/learned_calibrations.json') as f:
    data = json.load(f)
etas = [v['eta'] for v in data['anchors'].values()]
avg_eta = sum(etas) / len(etas)

def inject_in_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    content = re.sub(r'public float pathLossExponentClear = [\d.]+f;', f'public float pathLossExponentClear = {avg_eta:.1f}f;', content)
    with open(filepath, 'w') as f:
        f.write(content)

inject_in_file('build_unity_env.py')
inject_in_file('Unity_BLE_Simulator/Assets/Scripts/BLESimulator.cs')
print("Injected calibrations successfully.")
