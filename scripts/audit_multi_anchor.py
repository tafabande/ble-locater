import pandas as pd

df = pd.read_csv('ble-indoor-positioning/datasets/multi_anchor_observations.csv')
print("=== MULTI-ANCHOR DATASET RECALCULATION ===")
print(f"Total windows: {len(df)}")
print(f"Total unique sessions: {df['session_id'].nunique()}\n")

summary = []
grp = df.groupby(['target_x', 'target_y'])
for (tx, ty), g in grp:
    sess_list = sorted(g['session_id'].unique())
    summary.append({
        'coord': f"({tx:.1f}, {ty:.1f})",
        'n_sessions': len(sess_list),
        'n_windows': len(g),
        'sessions': sess_list
    })
    print(f"Coordinate ({tx:.1f}, {ty:.1f}): {len(sess_list)} session(s), {len(g)} windows")
    for s in sess_list:
        sub_len = len(g[g['session_id'] == s])
        print(f"    • {s}: {sub_len} windows")
    print()

print("Summary DataFrame:")
sdf = pd.DataFrame(summary)[['coord', 'n_sessions', 'n_windows']]
print(sdf.to_string(index=False))
