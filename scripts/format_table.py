import pandas as pd
import os

df = pd.read_csv('ble-indoor-positioning/reports/session_performance_ranking.csv')

out_path = r'C:\Users\DEV\.gemini\antigravity-ide\brain\0720a890-3203-4c2a-aac8-dac060c0d70a\session_performance_table_33.md'

lines = []
lines.append("# 📊 Complete 33-Session Physical Tracking & Jitter Performance Table\n")
lines.append("> **Empirical Evaluation Data for Chapter 4 (Results) & Chapter 3 (Methodology Appendix)**")
lines.append("> Evaluates all 33 multi-anchor physical collection sessions ($1,961$ observation windows) across raw coordinate predictions versus 2D Adaptive Kalman Filtered coordinates.\n")
lines.append("## 🏆 Summary Benchmark Statistics Across All 33 Sessions\n")
lines.append(f"- **Total Multi-Anchor Physical Sessions**: 33 sessions")
lines.append(f"- **Total Synchronized 4-Anchor Windows**: {int(df['n_windows'].sum()):,} windows")
lines.append(f"- **Mean Raw Positioning Error**: {df['raw_mean_err_m'].mean():.4f} m (Median: {df['raw_median_err_m'].median():.4f} m)")
lines.append(f"- **Mean Kalman Filtered Positioning Error**: {df['kalman_mean_err_m'].mean():.4f} m (Median: {df['kalman_median_err_m'].median():.4f} m)")
lines.append(f"- **Mean Raw Stationary Jitter (σ)**: {df['raw_jitter_m'].mean():.4f} m")
lines.append(f"- **Mean Kalman Filtered Jitter (σ)**: {df['kalman_jitter_m'].mean():.4f} m")
lines.append(f"- **Overall Mean Jitter Reduction**: **{df['kalman_jitter_reduction_pct'].mean():.2f}%** (Median: **{df['kalman_jitter_reduction_pct'].median():.2f}%**, Max: **{df['kalman_jitter_reduction_pct'].max():.2f}%**)\n")

lines.append("## 📋 Per-Session Comprehensive Ranking Table\n")
lines.append("| # | Recording Session File | Target $(X, Y)$ | Windows | Raw Mean (m) | Raw Median (m) | KF Mean (m) | KF Median (m) | Trilateration (m) | Raw Jitter $\\sigma$ (m) | KF Jitter $\\sigma$ (m) | Jitter Reduction | Estimated Centroid $(X, Y)$ |")
lines.append("| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

for i, r in df.iterrows():
    lines.append(
        f"| {i+1} | `{r['session_id']}` | $({r['target_x']:.1f}, {r['target_y']:.1f})$ | "
        f"{int(r['n_windows'])} | {r['raw_mean_err_m']:.3f} | {r['raw_median_err_m']:.3f} | "
        f"{r['kalman_mean_err_m']:.3f} | {r['kalman_median_err_m']:.3f} | {r['trilat_mean_err_m']:.3f} | "
        f"{r['raw_jitter_m']:.3f} | {r['kalman_jitter_m']:.3f} | **{r['kalman_jitter_reduction_pct']:.1f}%** | "
        f"$({r['centroid_raw_x']:.2f}, {r['centroid_raw_y']:.2f})$ |"
    )

with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f"Wrote table to {out_path}")
