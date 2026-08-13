import os
import sys
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import StandardScaler
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNTHETIC_DATA_PATH = os.path.join(PROJECT_ROOT, 'datasets', 'synthetic_observations.csv')
MODEL_SAVE_PATH = os.path.join(PROJECT_ROOT, 'models', 'direct_2d_position_regressor.joblib')
SCALER_SAVE_PATH = os.path.join(PROJECT_ROOT, 'models', 'direct_2d_scaler.joblib')

def main():
    print('======================================================================')
    print(' 🚀 DIRECT 2D MULTI-ANCHOR POSITION REGRESSOR TRAINER')
    print('======================================================================')
    if not os.path.exists(SYNTHETIC_DATA_PATH):
        print(f'❌ Synthetic dataset file not found: {SYNTHETIC_DATA_PATH}')
        print('Please run the Unity simulation for 20-30 seconds to generate synthetic telemetry data!')
        return
    df = pd.read_csv(SYNTHETIC_DATA_PATH)
    print(f'📊 Total Raw Telemetry Packets Logged: {len(df):,}')
    if len(df) < 50:
        print('⚠️ Insufficient data logged (< 50 packets). Run Unity simulation longer to accumulate data!')
        return
    df['time_group'] = df['timestamp'] // 500 * 500
    pivoted = df.pivot_table(index=['time_group', 'true_x', 'true_y'], columns='anchor', values='rssi', aggfunc='mean').reset_index()
    required_anchors = ['ANCHOR_01', 'ANCHOR_02', 'ANCHOR_03']
    for anc in required_anchors:
        if anc not in pivoted.columns:
            pivoted[anc] = -95.0
    pivoted[required_anchors] = pivoted[required_anchors].fillna(-95.0)
    pivoted = pivoted.dropna(subset=['true_x', 'true_y'])
    print(f'🎯 Total Synchronized 2D Observation Windows: {len(pivoted):,}')
    X = pivoted[required_anchors].values
    y = pivoted[['true_x', 'true_y']].values
    split_idx = int(len(pivoted) * 0.8)
    X_train, X_test = (X[:split_idx], X[split_idx:])
    y_train, y_test = (y[:split_idx], y[split_idx:])
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    print('\n[TRAINING] Fitting ExtraTrees Multi-Output 2D Position Regressor...')
    model = MultiOutputRegressor(ExtraTreesRegressor(n_estimators=200, random_state=42))
    model.fit(X_train_scaled, y_train)
    y_pred = model.predict(X_test_scaled)
    euclidean_errors = np.sqrt(np.sum((y_test - y_pred) ** 2, axis=1))
    mae_2d = np.mean(euclidean_errors)
    median_2d = np.median(euclidean_errors)
    p95_2d = np.percentile(euclidean_errors, 95)
    print('\n===========================================================================')
    print(' 🏆 DIRECT 2D REGRESSOR EVALUATION RESULTS')
    print('===========================================================================')
    print(f'  Test Set 2D MAE Error  : {mae_2d:.4f} meters')
    print(f'  Median 2D Error        : {median_2d:.4f} meters')
    print(f'  95th Percentile Error  : {p95_2d:.4f} meters')
    print('===========================================================================')
    joblib.dump(model, MODEL_SAVE_PATH)
    joblib.dump(scaler, SCALER_SAVE_PATH)
    print(f'\n✅ Direct 2D Model saved to: {MODEL_SAVE_PATH}')
if __name__ == '__main__':
    main()
