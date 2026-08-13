import math
import logging
import numpy as np
from scipy.optimize import least_squares
logger = logging.getLogger('TRILATERATION')

class TrilaterationEngine:

    def __init__(self, anchors_config: dict):
        self.anchors = {}
        if isinstance(anchors_config, dict):
            for k, v in anchors_config.items():
                try:
                    arr = np.array(v, dtype=float)
                    if arr.shape == (2,) and np.all(np.isfinite(arr)):
                        self.anchors[str(k)] = arr
                except Exception as e:
                    logger.warning(f'Invalid coordinate configuration for anchor {k}: {v}. Error: {e}')

    def estimate_position(self, distances: dict, raise_on_insufficient: bool=False) -> tuple:
        active_anchors = []
        active_coords = []
        active_dists = []
        if isinstance(distances, dict):
            for anchor_id, dist in distances.items():
                if str(anchor_id) in self.anchors and dist is not None:
                    try:
                        d_val = float(dist)
                        if np.isfinite(d_val) and d_val >= 0:
                            active_anchors.append(str(anchor_id))
                            active_coords.append(self.anchors[str(anchor_id)])
                            active_dists.append(d_val)
                    except (ValueError, TypeError):
                        continue
        n_anchors = len(active_anchors)
        if n_anchors < 2:
            if raise_on_insufficient:
                raise ValueError(f'At least 2 active anchors required for trilateration. Found: {n_anchors}')
            if n_anchors == 1:
                cx, cy = (float(active_coords[0][0]), float(active_coords[0][1]))
            elif len(self.anchors) > 0:
                all_coords = np.array(list(self.anchors.values()))
                cx, cy = (float(np.mean(all_coords[:, 0])), float(np.mean(all_coords[:, 1])))
            else:
                cx, cy = (0.0, 0.0)
            return ((cx, cy), 99.9, 99.9)
        active_coords = np.array(active_coords)
        active_dists = np.array(active_dists)
        x0 = np.mean(active_coords, axis=0)
        estimated_pos = x0.copy()

        def residuals(pos):
            diffs = active_coords - pos
            calculated_dists = np.linalg.norm(diffs, axis=1)
            return calculated_dists - active_dists
        try:
            res = least_squares(residuals, x0, method='lm')
            if res.success and np.all(np.isfinite(res.x)):
                estimated_pos = res.x
            else:
                logger.warning('Least-squares optimization did not converge cleanly. Using centroid fallback.')
        except Exception as e:
            logger.error(f'Trilateration optimization error: {e}. Falling back to centroid.')
            estimated_pos = x0
        gdop = 99.9
        uncertainty_radius = 5.0
        try:
            diffs = estimated_pos - active_coords
            norms = np.linalg.norm(diffs, axis=1)[:, np.newaxis]
            norms[norms == 0] = 1e-05
            J = diffs / norms
            sigma = 0.35
            JTJ = J.T @ J
            JTJ_inv = np.linalg.inv(JTJ)
            trace_inv = np.trace(JTJ_inv)
            if trace_inv > 0 and np.isfinite(trace_inv):
                gdop = float(np.sqrt(trace_inv))
                cov = sigma ** 2 * JTJ_inv
                uncertainty_radius = float(np.sqrt(np.trace(cov)))
        except (np.linalg.LinAlgError, ZeroDivisionError, ValueError, OverflowError):
            gdop = 99.9
            uncertainty_radius = 5.0
        est_x = float(estimated_pos[0]) if np.isfinite(estimated_pos[0]) else 0.0
        est_y = float(estimated_pos[1]) if np.isfinite(estimated_pos[1]) else 0.0
        return ((est_x, est_y), round(uncertainty_radius, 3), round(gdop, 2))

    def compute_gdop_grid(self, bounds_x=(0.0, 10.0), bounds_y=(0.0, 10.0), step=0.5, active_anchors=None) -> dict:
        if active_anchors is not None:
            target_coords = [self.anchors[a] for a in active_anchors if a in self.anchors]
        else:
            target_coords = list(self.anchors.values())
        if len(target_coords) < 2:
            target_coords = list(self.anchors.values())
        xs = np.arange(bounds_x[0], bounds_x[1] + step, step)
        ys = np.arange(bounds_y[0], bounds_y[1] + step, step)
        grid_z_confidence = []
        grid_z_gdop = []
        coords_arr = np.array(target_coords) if target_coords else np.empty((0, 2))
        for y in ys:
            row_conf = []
            row_gdop = []
            for x in xs:
                pos = np.array([x, y])
                if len(coords_arr) >= 2:
                    try:
                        diffs = pos - coords_arr
                        norms = np.linalg.norm(diffs, axis=1)[:, np.newaxis]
                        norms[norms == 0] = 1e-05
                        J = diffs / norms
                        JTJ = J.T @ J
                        JTJ_inv = np.linalg.inv(JTJ)
                        trace_inv = np.trace(JTJ_inv)
                        if trace_inv > 0 and np.isfinite(trace_inv):
                            gdop_val = float(np.sqrt(trace_inv))
                        else:
                            gdop_val = 10.0
                    except Exception:
                        gdop_val = 10.0
                else:
                    gdop_val = 10.0
                conf = max(0.0, min(100.0, 100.0 * math.exp(-max(0.0, gdop_val - 1.0) / 1.8)))
                row_conf.append(round(conf, 1))
                row_gdop.append(round(min(15.0, gdop_val), 2))
            grid_z_confidence.append(row_conf)
            grid_z_gdop.append(row_gdop)
        return {'x': [round(float(x), 2) for x in xs], 'y': [round(float(y), 2) for y in ys], 'confidence': grid_z_confidence, 'gdop': grid_z_gdop}

class KalmanFilter2D:

    def __init__(self, dt: float=1.0, process_noise: float=0.1, measurement_noise: float=0.35):
        self.dt = float(dt) if np.isfinite(dt) and dt > 0 else 1.0
        self.initialized = False
        self._last_update_time = None
        self.H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], dtype=float)
        p_noise = float(process_noise) if np.isfinite(process_noise) and process_noise >= 0 else 0.1
        m_noise = float(measurement_noise) if np.isfinite(measurement_noise) and measurement_noise >= 0 else 0.35
        self._process_noise = p_noise
        self.Q = np.eye(4) * p_noise
        self.R = np.eye(2) * m_noise
        self.P = np.eye(4) * 1.0
        self.x = np.zeros(4, dtype=float)

    def _build_F(self, dt: float) -> np.ndarray:
        return np.array([[1, 0, dt, 0], [0, 1, 0, dt], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=float)

    def _update_dt(self):
        import time as _time
        now = _time.monotonic()
        if self._last_update_time is not None:
            elapsed = now - self._last_update_time
            self.dt = max(0.01, min(5.0, elapsed))
        self._last_update_time = now

    def initialize(self, x0: float, y0: float):
        import time as _time
        try:
            x_val = float(x0) if np.isfinite(x0) else 0.0
            y_val = float(y0) if np.isfinite(y0) else 0.0
            self.x = np.array([x_val, y_val, 0.0, 0.0], dtype=float)
            self.P = np.eye(4) * 1.0
            self.initialized = True
            self._last_update_time = _time.monotonic()
        except Exception:
            self.x = np.zeros(4, dtype=float)
            self.P = np.eye(4) * 1.0
            self.initialized = True
            self._last_update_time = _time.monotonic()

    def predict(self):
        try:
            F = self._build_F(self.dt)
            self.x = F @ self.x
            self.P = F @ self.P @ F.T + self.Q
        except Exception as e:
            logger.error(f'Kalman prediction error: {e}')

    def update(self, zx: float, zy: float):
        try:
            if not (np.isfinite(zx) and np.isfinite(zy)):
                return
            z = np.array([float(zx), float(zy)])
            y = z - self.H @ self.x
            S = self.H @ self.P @ self.H.T + self.R
            K = self.P @ self.H.T @ np.linalg.inv(S)
            self.x = self.x + K @ y
            self.P = (np.eye(4) - K @ self.H) @ self.P
        except np.linalg.LinAlgError:
            logger.warning('Kalman gain matrix inversion failed (singular matrix). Skipping measurement update.')
        except Exception as e:
            logger.error(f'Kalman update error: {e}')

    def filter(self, x_meas: float, y_meas: float) -> tuple:
        try:
            if not (np.isfinite(x_meas) and np.isfinite(y_meas)):
                if self.initialized:
                    return (float(self.x[0]), float(self.x[1]))
                return (0.0, 0.0)
            if not self.initialized:
                self.initialize(x_meas, y_meas)
                return (float(x_meas), float(y_meas))
            self._update_dt()
            self.predict()
            self.update(x_meas, y_meas)
            return (float(self.x[0]), float(self.x[1]))
        except Exception as e:
            logger.error(f'Kalman filter execution error: {e}')
            return (float(x_meas) if np.isfinite(x_meas) else 0.0, float(y_meas) if np.isfinite(y_meas) else 0.0)
