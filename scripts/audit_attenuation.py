import pandas as pd

df = pd.read_csv('ble-indoor-positioning/datasets/observations.csv')
print("=== EMPIRICAL ATTENUATION VERIFICATION IN OBSERVATIONS.CSV ===")
for dist in [1.0, 2.0, 3.0, 3.4]:
    sub = df[df['distance_m'] == dist]
    if len(sub) == 0:
        continue
    los = sub[sub['obstacle'] == 'No']
    los_rssi = los['rssi_mean'].mean() if len(los) > 0 else None
    print(f"\nDistance {dist:.1f}m (Clean LOS Mean RSSI: {los_rssi:.2f} dBm, N={len(los)}):")
    for obs, g in sub.groupby('obstacle_type'):
        if str(obs).strip() in ['None', 'Nan', 'Tape Measure', 'Tape  Measure', '']:
            continue
        m_rssi = g['rssi_mean'].mean()
        atten = (los_rssi - m_rssi) if los_rssi is not None else 0.0
        print(f"   • {str(obs):<22}: Mean = {m_rssi:.2f} dBm | Attenuation = {atten:+.2f} dB | N={len(g)}")
