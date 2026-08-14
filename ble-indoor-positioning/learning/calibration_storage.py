import os
import json
import time
import logging
logger = logging.getLogger('CALIBRATION_STORAGE')

class CalibrationStorage:
    DEFAULT_FILEPATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models', 'learned_calibrations.json')

    @classmethod
    def load(cls, filepath: str=None) -> dict:
        target_path = filepath or cls.DEFAULT_FILEPATH
        if os.path.exists(target_path):
            try:
                if os.path.getsize(target_path) == 0:
                    raise json.JSONDecodeError("File is empty (0 bytes)", "", 0)
                with open(target_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f'💾 CalibrationStorage: Loaded calibration data from {target_path}')
                return data
            except Exception as e:
                logger.warning(f'⚠️ CalibrationStorage: Failed to load calibration file ({e}). Resetting to defaults.')
        return {'version': 1, 'building_name': 'Hospital Main Wing (Floor 1)', 'firmware_version': '2.4.0-esp32', 'training_sessions': 1, 'anchors': {}, 'total_samples': 0, 'last_updated': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}

    @classmethod
    def save(cls, learner, filepath: str=None, building_name: str='Hospital Main Wing (Floor 1)', firmware_version: str='2.4.0-esp32') -> bool:
        target_path = filepath or cls.DEFAULT_FILEPATH
        try:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            existing = cls.load(target_path)
            sessions = existing.get('training_sessions', 0) + 1
            anchors_dict = {}
            all_anchors = set(list(learner.anchor_eta.keys()) + list(learner.anchor_bias.keys()) + list(learner.anchor_samples.keys()))
            for anc_id in all_anchors:
                anchors_dict[anc_id] = {'eta': round(learner.anchor_eta[anc_id], 4), 'bias': round(learner.anchor_bias[anc_id], 4), 'samples': learner.anchor_samples[anc_id]}
            payload = {'version': 1, 'building_name': building_name, 'firmware_version': firmware_version, 'training_sessions': sessions, 'anchors': anchors_dict, 'total_samples': learner.samples_learned_count, 'last_updated': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
            
            # Atomic file save using temporary file + replace
            temp_path = target_path + '.tmp'
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=4)
            os.replace(temp_path, target_path)
            
            logger.info(f'💾 CalibrationStorage: Saved calibrations ({learner.samples_learned_count} total samples) to {target_path}')
            return True
        except Exception as e:
            logger.error(f'Failed to save calibration storage file: {e}')
            return False

