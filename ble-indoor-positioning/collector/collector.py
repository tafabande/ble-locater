import argparse
import csv
import json
import os
import sys
import time
from typing import Optional
try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

def auto_detect_port() -> Optional[str]:
    if not SERIAL_AVAILABLE:
        return None
    ports = list(serial.tools.list_ports.comports())
    if ports:
        print(f'[INFO] Auto-detected serial port: {ports[0].device} ({ports[0].description})')
        return ports[0].device
    return None

def init_csv_file(filepath: str, headers: list[str]) -> None:
    directory = os.path.dirname(filepath)
    if directory and (not os.path.exists(directory)):
        os.makedirs(directory, exist_ok=True)
    if not os.path.exists(filepath):
        with open(filepath, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
        print(f'[INFO] Initialized new CSV file: {filepath}')

import datetime
import urllib.request
import urllib.error

def process_line(
    line: str,
    obs_writer,
    obs_file,
    raw_writer,
    raw_file,
    anchor_id_override: Optional[str],
    datasheet_writer=None,
    datasheet_file=None,
    log_file=None,
    post_to_api: bool = False
) -> None:
    line_stripped = line.strip()
    if not line_stripped:
        return

    # 1. Plain Text Log: Copy and pass what is coming from nodes as-is (Zero-Transformation)
    if log_file is not None:
        try:
            log_file.write(line_stripped + '\n')
            log_file.flush()
        except Exception as log_err:
            print(f'[WARNING] Failed writing to plain text log: {log_err}')

    now = datetime.datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M:%S.%f')[:-3]
    host_timestamp = time.time()

    extracted_anchor = anchor_id_override or 'Unknown'
    extracted_mac = 'Unknown'
    extracted_rssi = 'N/A'
    extracted_ts = int(host_timestamp * 1000)

    # 2. Extract raw data without altering or transforming RSSI/time values
    is_json = line_stripped.startswith('{') and line_stripped.endswith('}')
    if is_json:
        try:
            data = json.loads(line_stripped)
            msg_type = data.get('type')
            extracted_anchor = anchor_id_override or data.get('anchor_id') or data.get('anchor', 'Unknown')
            extracted_ts = data.get('timestamp', int(host_timestamp * 1000))
            extracted_mac = data.get('device_mac') or data.get('mac') or data.get('device', 'Unknown')
            if 'rssi' in data:
                extracted_rssi = data.get('rssi')
            elif 'rssi_mean' in data:
                extracted_rssi = data.get('rssi_mean')

            if msg_type == 'observation':
                packet_count = data.get('packet_count', 0)
                scan_duration_ms = data.get('scan_duration_ms', 1000)
                rssi_mean = data.get('rssi_mean', 0.0)
                rssi_std = data.get('rssi_std', 0.0)
                rssi_variance = data.get('rssi_variance', 0.0)
                rssi_min = data.get('rssi_min', 0)
                rssi_max = data.get('rssi_max', 0)
                rssi_range = data.get('rssi_range', 0)
                rssi_delta_mean = data.get('rssi_delta_mean', 0.0)
                advertising_interval_ms = data.get('advertising_interval_ms', 0.0)
                rssi_median = data.get('rssi_median', 0.0)
                rssi_mode = data.get('rssi_mode', 0)
                skewness = data.get('skewness', 0.0)
                kurtosis = data.get('kurtosis', 0.0)
                percentile_25 = data.get('percentile_25', 0.0)
                percentile_75 = data.get('percentile_75', 0.0)
                packet_loss_estimate = data.get('packet_loss_estimate', 0.0)
                max_consecutive_gap_ms = data.get('max_consecutive_gap_ms', 0)
                obs_writer.writerow([extracted_anchor, extracted_ts, host_timestamp, extracted_mac, packet_count, scan_duration_ms, rssi_mean, rssi_std, rssi_variance, rssi_min, rssi_max, rssi_range, rssi_delta_mean, advertising_interval_ms, rssi_median, rssi_mode, skewness, kurtosis, percentile_25, percentile_75, packet_loss_estimate, max_consecutive_gap_ms])
                obs_file.flush()
                print(f'[OBSERVATION] Anchor: {extracted_anchor} | Packets: {packet_count} | Mean RSSI: {rssi_mean} | Loss: {packet_loss_estimate * 100:.1f}%')
            elif msg_type == 'raw':
                rssi = data.get('rssi', 0)
                raw_writer.writerow([extracted_anchor, extracted_ts, host_timestamp, extracted_mac, rssi])
                raw_file.flush()
                print(f'[RAW PACKET] Anchor: {extracted_anchor} | MAC: {extracted_mac} | RSSI: {rssi}')
            elif msg_type == 'config':
                print(f'[CONFIG] Active firmware configuration: {data}')
            else:
                print(f'[JSON Out] {data}')
        except json.JSONDecodeError:
            print(f"[WARNING] Failed to parse JSON line: '{line_stripped}'")
    else:
        # Check if CSV line from ESP32 firmware: timestamp,anchor,mac,rssi,name
        parts = [p.strip() for p in line_stripped.split(',')]
        if len(parts) >= 4 and not parts[0].lower().startswith('timestamp'):
            extracted_ts = parts[0]
            extracted_anchor = anchor_id_override or parts[1]
            extracted_mac = parts[2]
            extracted_rssi = parts[3]
            try:
                numeric_rssi = int(float(extracted_rssi))
                raw_writer.writerow([extracted_anchor, extracted_ts, host_timestamp, extracted_mac, numeric_rssi])
                raw_file.flush()
            except Exception:
                pass
            print(f'[NODE RAW CSV] Anchor: {extracted_anchor} | MAC: {extracted_mac} | RSSI: {extracted_rssi}')
        else:
            print(f'[NODE SERIAL STREAM] {line_stripped}')

    # 3. Data Sheet CSV Writer: Date is date, time is time, RSSI is raw RSSI
    if datasheet_writer is not None and datasheet_file is not None:
        try:
            datasheet_writer.writerow([
                date_str,
                time_str,
                extracted_ts,
                extracted_anchor,
                extracted_mac,
                extracted_rssi,
                line_stripped
            ])
            datasheet_file.flush()
        except Exception as ds_err:
            print(f'[WARNING] Failed writing to data sheet: {ds_err}')

    # 4. Optional Live API Forwarding to Web Dashboard
    if post_to_api:
        try:
            req_data = json.dumps({
                "date": date_str,
                "time": time_str,
                "timestamp": extracted_ts,
                "anchor_id": extracted_anchor,
                "device_mac": extracted_mac,
                "rssi": extracted_rssi,
                "raw_payload": line_stripped
            }).encode('utf-8')
            req = urllib.request.Request(
                'http://127.0.0.1:8000/api/collector/ingest',
                data=req_data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=0.1):
                pass
        except Exception:
            pass

def main() -> None:
    parser = argparse.ArgumentParser(description='AI-Assisted Indoor BLE Positioning System - Python Collector')
    parser.add_argument('--port', '-p', type=str, default=None, help="Serial port (e.g. COM3 or /dev/ttyUSB0). Set to 'stdin' to read from standard input.")
    parser.add_argument('--baud', '-b', type=int, default=115200, help='Baud rate (default: 115200)')
    parser.add_argument('--output', '-o', type=str, default='datasets/observations.csv', help='Output path for observation window CSV (default: datasets/observations.csv)')
    parser.add_argument('--raw-output', '-r', type=str, default='datasets/raw_packets.csv', help='Output path for raw packet CSV (default: datasets/raw_packets.csv)')
    parser.add_argument('--datasheet', '-s', type=str, default='datasets/raw_datasheet.csv', help='Output path for raw uncleaned data sheet CSV (default: datasets/raw_datasheet.csv)')
    parser.add_argument('--log-output', '-l', type=str, default='datasets/raw_stream.log', help='Output path for verbatim plain text log file (default: datasets/raw_stream.log)')
    parser.add_argument('--mode', '-m', type=str, choices=['NORMAL', 'RAW', 'DUAL'], default=None, help='Send configuration command to set ESP32 node output mode')
    parser.add_argument('--tag', '-t', type=str, default=None, help='Send configuration command to set target BLE Tag MAC address')
    parser.add_argument('--anchor', '-a', type=str, default=None, help='Send configuration command to set ESP32 Anchor ID')
    parser.add_argument('--mac', type=str, default=None, help='ESP32 Anchor hardware MAC address (e.g. 24:6F:28:1A:4C:01)')
    parser.add_argument('--duration', '-d', type=float, default=None, help='Collect data for N seconds and then exit. If not set, collects indefinitely.')
    args = parser.parse_args()
    obs_headers = ['anchor_id', 'timestamp', 'host_timestamp', 'device_mac', 'packet_count', 'scan_duration_ms', 'rssi_mean', 'rssi_std', 'rssi_variance', 'rssi_min', 'rssi_max', 'rssi_range', 'rssi_delta_mean', 'advertising_interval_ms', 'rssi_median', 'rssi_mode', 'skewness', 'kurtosis', 'percentile_25', 'percentile_75', 'packet_loss_estimate', 'max_consecutive_gap_ms']
    raw_headers = ['anchor_id', 'timestamp', 'host_timestamp', 'device_mac', 'rssi']
    datasheet_headers = ['date', 'time', 'timestamp', 'anchor_id', 'device_mac', 'rssi', 'raw_payload']

    init_csv_file(args.output, obs_headers)
    init_csv_file(args.raw_output, raw_headers)
    init_csv_file(args.datasheet, datasheet_headers)

    obs_file = open(args.output, mode='a', newline='', encoding='utf-8')
    raw_file = open(args.raw_output, mode='a', newline='', encoding='utf-8')
    datasheet_file = open(args.datasheet, mode='a', newline='', encoding='utf-8')

    log_dir = os.path.dirname(args.log_output)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    log_file = open(args.log_output, mode='a', encoding='utf-8')

    obs_writer = csv.writer(obs_file)
    raw_writer = csv.writer(raw_file)
    datasheet_writer = csv.writer(datasheet_file)
    ser = None
    input_source = args.port
    if input_source is None:
        detected = auto_detect_port()
        if detected:
            input_source = detected
        else:
            print('[INFO] No serial port detected. Defaulting to stdin input.')
            input_source = 'stdin'
    start_time = time.time()
    try:
        if input_source == 'stdin':
            print('[INFO] Collector reading from standard input. Press Ctrl+C to stop.')
            for line in sys.stdin:
                if args.duration and time.time() - start_time >= args.duration:
                    print(f'[INFO] Target collection duration of {args.duration}s reached.')
                    break
                process_line(line, obs_writer, obs_file, raw_writer, raw_file, args.anchor, datasheet_writer, datasheet_file, log_file, post_to_api=True)
        else:
            if not SERIAL_AVAILABLE:
                print('[ERROR] pyserial is not installed, cannot read from serial port. Run pip install pyserial.')
                sys.exit(1)
            print(f'[INFO] Connecting to serial port {input_source} at {args.baud} baud...')
            ser = serial.Serial(input_source, args.baud, timeout=1)
            time.sleep(1.5)
            if args.anchor:
                print(f'[INFO] Configuring anchor ID to: {args.anchor}')
                ser.write(f'SET_ANCHOR={args.anchor}\n'.encode('utf-8'))
                time.sleep(0.1)
            if args.tag:
                print(f'[INFO] Configuring target tag MAC to: {args.tag}')
                ser.write(f'SET_TAG={args.tag}\n'.encode('utf-8'))
                time.sleep(0.1)
            if args.mode:
                print(f'[INFO] Configuring mode to: {args.mode}')
                ser.write(f'SET_MODE={args.mode}\n'.encode('utf-8'))
                time.sleep(0.1)
            ser.write(b'GET_CONFIG\n')
            ser.reset_input_buffer()
            print('[INFO] Connection established. Gathering telemetry (Press Ctrl+C to exit)...')
            while True:
                if args.duration and time.time() - start_time >= args.duration:
                    print(f'[INFO] Target collection duration of {args.duration}s reached.')
                    break
                if ser.in_waiting > 0:
                    try:
                        line = ser.readline().decode('utf-8', errors='ignore')
                        process_line(line, obs_writer, obs_file, raw_writer, raw_file, args.anchor, datasheet_writer, datasheet_file, log_file, post_to_api=True)
                    except Exception as serial_err:
                        print(f'[WARNING] Serial read error: {serial_err}')
                else:
                    time.sleep(0.01)
    except KeyboardInterrupt:
        print('\n[INFO] Data collection stopped by user.')
    finally:
        obs_file.close()
        raw_file.close()
        datasheet_file.close()
        log_file.close()
        if ser and ser.is_open:
            ser.close()
        print('[INFO] Closed all data sheets, plain text logs, and serial interfaces cleanly.')
if __name__ == '__main__':
    main()
