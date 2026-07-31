"""
BLE Indoor Positioning — Localization & Filtering Engine
==========================================================

Implements:
  1. 2D Weighted Least-Squares Trilateration
  2. 2D Kalman Filter for trajectory smoothing
  3. Geometric Dilution of Precision (GDOP) / uncertainty estimation
"""

import numpy as np
from scipy.optimize import least_squares


class TrilaterationEngine:
    def __init__(self, anchors_config: dict):
        """
        Parameters
        ----------
        anchors_config : dict
            Dictionary mapping anchor_id to coordinates (x, y) in meters.
            Example: {"ANCHOR_01": (0.0, 0.0), "ANCHOR_02": (5.0, 0.0), "ANCHOR_03": (2.5, 4.33)}
        """
        self.anchors = {k: np.array(v, dtype=float) for k, v in anchors_config.items()}

    def estimate_position(self, distances: dict) -> tuple:
        """
        Estimate 2D coordinates (x, y) from predicted distances using Non-linear Least Squares.

        Parameters
        ----------
        distances : dict
            Dictionary mapping anchor_id to estimated distance in meters.

        Returns
        -------
        tuple
            ((x, y), uncertainty_radius, gdop)
        """
        active_anchors = []
        active_coords = []
        active_dists = []

        for anchor_id, dist in distances.items():
            if anchor_id in self.anchors and dist is not None:
                active_anchors.append(anchor_id)
                active_coords.append(self.anchors[anchor_id])
                active_dists.append(float(dist))

        n_anchors = len(active_anchors)
        if n_anchors < 2:
            raise ValueError(f"At least 2 active anchors required for trilateration. Found: {n_anchors}")

        active_coords = np.array(active_coords)
        active_dists = np.array(active_dists)

        # 1. Initial guess: centroid of active anchors
        x0 = np.mean(active_coords, axis=0)

        # 2. Residual function to minimize: sum((dist_calculated - dist_measured)^2)
        def residuals(pos):
            return np.linalg.norm(active_coords - pos, axis=1) - active_dists

        # 3. Solve using Levenberg-Marquardt least-squares optimization
        res = least_squares(residuals, x0, method="lm")
        estimated_pos = res.x

        # 4. Uncertainty Estimation (GDOP proxy & Standard Errors)
        # Jacobian matrix J represents rate of change of distances w.r.t coordinates
        # J_i = [(x - x_i)/d_i, (y - y_i)/d_i]
        try:
            diffs = estimated_pos - active_coords
            norms = np.linalg.norm(diffs, axis=1)[:, np.newaxis]
            # Prevent division by zero
            norms[norms == 0] = 1e-5
            J = diffs / norms

            # Covariance matrix: Cov = sigma^2 * (J^T * J)^-1
            # Assuming distance prediction standard error (sigma) is ~0.35m (matching MAE)
            sigma = 0.35
            JTJ_inv = np.linalg.inv(J.T @ J)
            cov = (sigma ** 2) * JTJ_inv

            # GDOP = sqrt(trace((J^T * J)^-1))
            gdop = float(np.sqrt(np.trace(JTJ_inv)))
            uncertainty_radius = float(np.sqrt(np.trace(cov)))
        except (np.linalg.LinAlgError, ZeroDivisionError):
            gdop = 99.9
            uncertainty_radius = 2.0  # Fallback uncertainty radius

        return (float(estimated_pos[0]), float(estimated_pos[1])), round(uncertainty_radius, 3), round(gdop, 2)


class KalmanFilter2D:
    def __init__(self, dt: float = 1.0, process_noise: float = 0.1, measurement_noise: float = 0.35):
        """
        2D Constant Velocity Kalman Filter to smooth location estimates.

        State vector x = [pos_x, pos_y, vel_x, vel_y]^T
        """
        self.dt = dt
        self.initialized = False

        # State transition matrix F
        self.F = np.array([
            [1, 0, dt,  0],
            [0, 1,  0, dt],
            [0, 0,  1,  0],
            [0, 0,  0,  1]
        ], dtype=float)

        # Measurement matrix H (we only measure position, not velocity)
        self.H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ], dtype=float)

        # Process covariance matrix Q (system model uncertainty)
        self.Q = np.eye(4) * process_noise

        # Measurement covariance matrix R (sensor noise)
        self.R = np.eye(2) * measurement_noise

        # Initial state covariance P
        self.P = np.eye(4) * 1.0

        # State vector x
        self.x = np.zeros(4)

    def initialize(self, x0: float, y0: float):
        self.x = np.array([x0, y0, 0.0, 0.0], dtype=float)
        self.P = np.eye(4) * 1.0
        self.initialized = True

    def predict(self):
        """Predict the next state."""
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q

    def update(self, zx: float, zy: float):
        """Update the state with a new position measurement."""
        z = np.array([zx, zy])

        # Innovation
        y = z - self.H @ self.x

        # Innovation covariance
        S = self.H @ self.P @ self.H.T + self.R

        # Kalman Gain
        K = self.P @ self.H.T @ np.linalg.inv(S)

        # Update state and covariance
        self.x = self.x + K @ y
        self.P = (np.eye(4) - K @ self.H) @ self.P

    def filter(self, x_meas: float, y_meas: float) -> tuple:
        """Runs one predict-update step and returns smoothed (x, y)."""
        if not self.initialized:
            self.initialize(x_meas, y_meas)
            return x_meas, y_meas

        self.predict()
        self.update(x_meas, y_meas)
        return float(self.x[0]), float(self.x[1])
