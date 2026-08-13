import os
import json
import time
import logging
logger = logging.getLogger('STAGE_RUNTIME_LEARNER')

class StageRuntimeLearner:
    DEFAULT_FILEPATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models', 'pipeline_runtimes.json')
    DEFAULT_STAGE_DURATIONS = {'Feature Engineering': 8.0, 'Dataset Ingestion': 2.0, 'Regression Tournament': 25.0, 'Classification Tournament': 15.0, 'Saving Artifacts & Reports': 3.0}

    def __init__(self, filepath: str=None):
        self.filepath = filepath or self.DEFAULT_FILEPATH
        self.data = self.load()

    def load(self) -> dict:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f'Loaded historical stage runtimes from {self.filepath}')
                return data
            except Exception as e:
                logger.error(f'Failed to load stage runtimes: {e}')
        return {'version': 1, 'total_runs': 0, 'stage_runtimes': self.DEFAULT_STAGE_DURATIONS.copy(), 'last_updated': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}

    def save(self) -> bool:
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            self.data['last_updated'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4)
            logger.info(f'Saved learned stage runtimes to {self.filepath}')
            return True
        except Exception as e:
            logger.error(f'Failed to save stage runtimes: {e}')
            return False

    def record_run(self, stage_durations: dict):
        self.data['total_runs'] = self.data.get('total_runs', 0) + 1
        runtimes = self.data.setdefault('stage_runtimes', {})
        for stage, duration in stage_durations.items():
            if duration <= 0.05:
                continue
            clean_stage = str(stage).strip()
            if clean_stage in runtimes:
                old_val = float(runtimes[clean_stage])
                runtimes[clean_stage] = round(0.7 * old_val + 0.3 * float(duration), 2)
            else:
                runtimes[clean_stage] = round(float(duration), 2)
        self.save()

    def get_total_historical_runtime(self) -> float:
        runtimes = self.data.get('stage_runtimes', self.DEFAULT_STAGE_DURATIONS)
        return float(sum(runtimes.values()))

    def compute_historical_eta(self, current_percent: float, elapsed_sec: float) -> float:
        runtimes = self.data.get('stage_runtimes', self.DEFAULT_STAGE_DURATIONS)
        total_hist_sec = max(10.0, float(sum(runtimes.values())))
        if current_percent <= 0:
            return total_hist_sec
        rem_pct_fraction = max(0.0, (100.0 - current_percent) / 100.0)
        hist_rem_sec = total_hist_sec * rem_pct_fraction
        live_rem_sec = max(0.0, elapsed_sec / (current_percent / 100.0) - elapsed_sec)
        runs_count = self.data.get('total_runs', 0)
        if runs_count >= 2:
            blended_eta = 0.75 * hist_rem_sec + 0.25 * live_rem_sec
        elif runs_count == 1:
            blended_eta = 0.5 * hist_rem_sec + 0.5 * live_rem_sec
        else:
            blended_eta = 0.3 * hist_rem_sec + 0.7 * live_rem_sec
        return max(0.0, blended_eta)
