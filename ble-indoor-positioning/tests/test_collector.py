import csv
import json
import os
import tempfile
from collector.collector import init_csv_file, process_line

def test_init_csv_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, 'test_dir', 'test_output.csv')
        headers = ['col1', 'col2']
        init_csv_file(filepath, headers)
        assert os.path.exists(filepath)
        with open(filepath, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0] == headers

def test_process_line_observation():
    with tempfile.TemporaryDirectory() as tmpdir:
        obs_path = os.path.join(tmpdir, 'obs.csv')
        raw_path = os.path.join(tmpdir, 'raw.csv')
        obs_headers = ['anchor_id', 'timestamp', 'host_timestamp', 'device_mac', 'packet_count', 'scan_duration_ms', 'rssi_mean', 'rssi_std', 'rssi_variance', 'rssi_min', 'rssi_max', 'rssi_range', 'rssi_delta_mean', 'advertising_interval_ms', 'rssi_median', 'rssi_mode', 'skewness', 'kurtosis', 'percentile_25', 'percentile_75', 'packet_loss_estimate', 'max_consecutive_gap_ms']
        init_csv_file(obs_path, obs_headers)
        init_csv_file(raw_path, ['anchor_id', 'timestamp', 'host_timestamp', 'device_mac', 'rssi'])
        obs_payload = {'type': 'observation', 'anchor_id': 'A1', 'timestamp': 123456, 'device_mac': '52:06:26:03:01:DA', 'packet_count': 10, 'scan_duration_ms': 1000, 'rssi_mean': -55.5, 'rssi_std': 1.2, 'rssi_variance': 1.44, 'rssi_min': -58, 'rssi_max': -53, 'rssi_range': 5, 'rssi_delta_mean': 0.5, 'advertising_interval_ms': 100.0, 'rssi_median': -56.0, 'rssi_mode': -56, 'skewness': -0.1542, 'kurtosis': 2.145, 'percentile_25': -57.5, 'percentile_75': -54.5, 'packet_loss_estimate': 0.1, 'max_consecutive_gap_ms': 120}
        with open(obs_path, 'a', newline='', encoding='utf-8') as obs_f, open(raw_path, 'a', newline='', encoding='utf-8') as raw_f:
            obs_writer = csv.writer(obs_f)
            raw_writer = csv.writer(raw_f)
            process_line(json.dumps(obs_payload), obs_writer, obs_f, raw_writer, raw_f, None)
        with open(obs_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert len(rows) == 2
            row = rows[1]
            assert row[0] == 'A1'
            assert row[1] == '123456'
            assert float(row[2]) > 0
            assert row[3] == '52:06:26:03:01:DA'
            assert row[4] == '10'
            assert row[5] == '1000'
            assert row[6] == '-55.5'
            assert row[14] == '-56.0'
            assert row[15] == '-56'
            assert row[16] == '-0.1542'
            assert row[17] == '2.145'
            assert row[18] == '-57.5'
            assert row[19] == '-54.5'
            assert row[20] == '0.1'
            assert row[21] == '120'

def test_process_line_observation_fallback_keys():
    with tempfile.TemporaryDirectory() as tmpdir:
        obs_path = os.path.join(tmpdir, 'obs.csv')
        raw_path = os.path.join(tmpdir, 'raw.csv')
        obs_headers = ['anchor_id', 'timestamp', 'host_timestamp', 'device_mac', 'packet_count']
        init_csv_file(obs_path, obs_headers)
        init_csv_file(raw_path, ['anchor_id', 'timestamp', 'host_timestamp', 'device_mac', 'rssi'])
        obs_payload = {'type': 'observation', 'anchor': 'A2', 'timestamp': 654321, 'device': '52:06:26:03:01:DA', 'packet_count': 8}
        with open(obs_path, 'a', newline='', encoding='utf-8') as obs_f, open(raw_path, 'a', newline='', encoding='utf-8') as raw_f:
            obs_writer = csv.writer(obs_f)
            raw_writer = csv.writer(raw_f)
            process_line(json.dumps(obs_payload), obs_writer, obs_f, raw_writer, raw_f, None)
        with open(obs_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert len(rows) == 2
            row = rows[1]
            assert row[0] == 'A2'
            assert row[1] == '654321'
            assert row[3] == '52:06:26:03:01:DA'
            assert row[4] == '8'

def test_process_line_raw():
    with tempfile.TemporaryDirectory() as tmpdir:
        obs_path = os.path.join(tmpdir, 'obs.csv')
        raw_path = os.path.join(tmpdir, 'raw.csv')
        init_csv_file(obs_path, ['anchor_id'])
        init_csv_file(raw_path, ['anchor_id', 'timestamp', 'host_timestamp', 'device_mac', 'rssi'])
        raw_payload = {'type': 'raw', 'timestamp': 9999, 'mac': '52:06:26:03:01:DA', 'rssi': -64}
        with open(obs_path, 'a', newline='', encoding='utf-8') as obs_f, open(raw_path, 'a', newline='', encoding='utf-8') as raw_f:
            obs_writer = csv.writer(obs_f)
            raw_writer = csv.writer(raw_f)
            process_line(json.dumps(raw_payload), obs_writer, obs_f, raw_writer, raw_f, 'A2')
        with open(raw_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert len(rows) == 2
            assert rows[1][0] == 'A2'
            assert rows[1][1] == '9999'
            assert float(rows[1][2]) > 0
            assert rows[1][3] == '52:06:26:03:01:DA'
            assert rows[1][4] == '-64'

def test_process_line_invalid():
    with tempfile.TemporaryDirectory() as tmpdir:
        obs_path = os.path.join(tmpdir, 'obs.csv')
        raw_path = os.path.join(tmpdir, 'raw.csv')
        init_csv_file(obs_path, ['anchor_id'])
        init_csv_file(raw_path, ['anchor_id'])
        with open(obs_path, 'a', newline='', encoding='utf-8') as obs_f, open(raw_path, 'a', newline='', encoding='utf-8') as raw_f:
            obs_writer = csv.writer(obs_f)
            raw_writer = csv.writer(raw_f)
            process_line('This is plain text and not JSON!', obs_writer, obs_f, raw_writer, raw_f, None)
            process_line('{"type": "broken_json_without_close', obs_writer, obs_f, raw_writer, raw_f, None)
        with open(obs_path, 'r') as f:
            assert len(f.readlines()) == 1
        with open(raw_path, 'r') as f:
            assert len(f.readlines()) == 1

def test_process_line_verbatim_log_and_datasheet():
    with tempfile.TemporaryDirectory() as tmpdir:
        obs_path = os.path.join(tmpdir, 'obs.csv')
        raw_path = os.path.join(tmpdir, 'raw.csv')
        ds_path = os.path.join(tmpdir, 'datasheet.csv')
        log_path = os.path.join(tmpdir, 'stream.log')

        init_csv_file(obs_path, ['anchor_id'])
        init_csv_file(raw_path, ['anchor_id', 'timestamp', 'host_timestamp', 'device_mac', 'rssi'])
        init_csv_file(ds_path, ['date', 'time', 'timestamp', 'anchor_id', 'device_mac', 'rssi', 'raw_payload'])

        with open(obs_path, 'a', newline='', encoding='utf-8') as obs_f, \
             open(raw_path, 'a', newline='', encoding='utf-8') as raw_f, \
             open(ds_path, 'a', newline='', encoding='utf-8') as ds_f, \
             open(log_path, 'a', encoding='utf-8') as log_f:
            obs_writer = csv.writer(obs_f)
            raw_writer = csv.writer(raw_f)
            ds_writer = csv.writer(ds_f)

            # Test 1: Raw CSV node line from ESP32 firmware
            esp_node_line = '1693800000,ESP32_01,52:06:26:03:01:DA,-68,ESP_TAG'
            process_line(esp_node_line, obs_writer, obs_f, raw_writer, raw_f, None, ds_writer, ds_f, log_f)

            # Test 2: Raw JSON packet
            json_line = json.dumps({'type': 'raw', 'timestamp': 1693800001, 'mac': '52:06:26:03:01:DA', 'rssi': -71})
            process_line(json_line, obs_writer, obs_f, raw_writer, raw_f, 'ESP32_02', ds_writer, ds_f, log_f)

        # Verify Plain Text Log is 100% verbatim copy with zero transformations
        with open(log_path, 'r', encoding='utf-8') as f:
            log_lines = [l.strip() for l in f.readlines()]
            assert len(log_lines) == 2
            assert log_lines[0] == esp_node_line
            assert log_lines[1] == json_line

        # Verify Data Sheet preserves exact date, time, raw RSSI, and payload
        with open(ds_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert len(rows) == 3 # Header + 2 data rows
            # Row 1 (ESP32 CSV)
            row1 = rows[1]
            assert len(row1[0].split('-')) == 3 # YYYY-MM-DD
            assert ':' in row1[1] # HH:MM:SS.mmm
            assert row1[2] == '1693800000'
            assert row1[3] == 'ESP32_01'
            assert row1[4] == '52:06:26:03:01:DA'
            assert row1[5] == '-68'
            assert row1[6] == esp_node_line

            # Row 2 (JSON)
            row2 = rows[2]
            assert row2[3] == 'ESP32_02'
            assert row2[4] == '52:06:26:03:01:DA'
            assert row2[5] == '-71'
            assert row2[6] == json_line

