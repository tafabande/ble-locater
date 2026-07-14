# Dataset Specification

Each observation window represents one second of BLE scanning.

## Features

| Feature | Description |
|----------|-------------|
| timestamp | Time of observation |
| anchor_id | ESP32 identifier |
| packet_count | Number of advertisements received |
| scan_duration_ms | Observation window duration |
| rssi_mean | Mean RSSI |
| rssi_min | Minimum RSSI |
| rssi_max | Maximum RSSI |
| rssi_std | Standard deviation |
| rssi_variance | RSSI variance |
| rssi_delta_mean | Mean RSSI difference |
| observed_adv_interval | Estimated advertisement interval |

## Target

distance_m

Measured physical distance between the anchor and BLE tag.
