# Massive Machine-Type Communication (mMTC) for ESP32 Indoor Positioning

## 1. Executive Summary & Objective

In high-density industrial and healthcare environments (e.g., automated warehouses, hospitals with thousands of tagged assets and personnel), indoor positioning systems encounter the **Massive Machine-Type Communication (mMTC)** challenge: reliably tracking hundreds to thousands of low-power wireless transmitters (BLE tags) simultaneously without channel saturation, packet loss, or server-side latency spikes.

This architecture specification outlines the roadmap and implementation principles for scaling the ESP32 anchor firmware, communication protocols, and server ingestion pipelines to support mMTC-level device densities.

---

## 2. Key Challenges in Dense BLE Deployments

1. **RF Contention on Primary Advertising Channels (37, 38, 39)**:
   - Standard BLE advertising operates across three designated channels (37, 38, and 39).
   - As tag count $N$ increases, the probability of uncoordinated packet collisions follows an unslotted Aloha curve:
     $$P_{\text{collision}} = 1 - e^{-2 G}$$
     where $G = N \times \frac{T_{\text{packet}}}{T_{\text{interval}}}$.
2. **Active Scanning Contention**:
   - When anchors execute active scanning (`passive = 0`), they transmit a `SCAN_REQ` frame for every detected advertisement, prompting a `SCAN_RSP` frame from the tag.
   - In dense multi-anchor deployments, multiple anchors transmit `SCAN_REQ` simultaneously, causing mutual interference and degrading the effective packet reception rate (PRR).
3. **Backhaul Bottlenecks (Serial UART vs Networked Ingestion)**:
   - USB UART at 115,200 baud tops out at ~11.5 KB/s. At 50+ packets/sec per anchor, serial buffers overflow.
   - Point-to-point USB tethering prevents realistic physical anchor distribution across a large building.

---

## 3. Firmware Architecture for mMTC Scalability

### 3.1. Zero-Contention Passive Scanning

In `main.c`, the scanning mode should be strictly **passive** during multi-tag production operation:

```c
struct ble_gap_disc_params params = {
    .itvl = 0x10,           // 10ms scan interval
    .window = 0x10,         // 10ms scan window (100% continuous duty cycle)
    .filter_duplicates = 0, // Ingest all raw packets for variance analysis
    .passive = 1            // PASSIVE SCAN: Listen-only, emits 0 SCAN_REQ packets
};
```

**Benefits**:
- Anchors generate zero RF noise on the advertising channels.
- Scalable to arbitrarily high numbers of anchors observing the same physical space without mutual interference.

### 3.2. Edge Window Aggregation on ESP32

Rather than transmitting every individual BLE advertisement frame across the backhaul, the ESP32 can maintain a lightweight in-memory hash table of observed devices during a 1-second aggregation epoch:

```
[ Raw Advertisements ] ──► [ ESP32 FreeRTOS Ring Buffer ]
                                  │
                                  ▼
                         [ Epoch Aggregator (1.0s) ]
                         - Count packets
                         - Running RSSI mean & variance
                         - Min / Max RSSI
                                  │
                                  ▼
                         [ Consolidated JSON / Protobuf Frame ]
                         (90% reduction in backhaul traffic)
```

**Memory Footprint on ESP32**:
- For 200 concurrently active tags: $200 \times 32\text{ bytes} \approx 6.4\text{ KB}$ of SRAM, which easily fits within the ESP32's 520 KB internal SRAM.

### 3.3. Dynamic NVS-Based Configuration & Hardware Identity

Instead of compile-time constants (`#define ANCHOR_ID`), anchors should automatically derive their identity or load parameters from Non-Volatile Storage (NVS):

1. **Auto-Identity**: Read the factory base MAC address and format as `ANCHOR_A1B2` (last 2 octets).
2. **Runtime Configuration**: Allow updating anchor coordinates, scan intervals, and RSSI threshold filters over UART/WiFi without re-flashing.

---

## 4. Network Backhaul & Ingestion Pipeline

### 4.1. MQTT Over WiFi / Ethernet

Anchors report telemetry and observations over a standard broker (e.g., Eclipse Mosquitto or embedded broker) using lightweight JSON or Protocol Buffers:

- **Telemetry Topic**: `ble/anchor/{anchor_id}/telemetry` (heartbeats, uptime, free heap, RSSI noise floor).
- **Observation Topic**: `ble/anchor/{anchor_id}/observations` (batched tag sightings).

```json
{
  "anchor_id": "ANCHOR_01",
  "timestamp_ms": 1700000000120,
  "devices": [
    { "mac": "52:06:26:03:01:DA", "count": 12, "rssi_mean": -62.4, "rssi_std": 1.4 },
    { "mac": "A4:C1:38:12:34:56", "count": 8,  "rssi_mean": -78.1, "rssi_std": 2.1 }
  ]
}
```

### 4.2. Asynchronous Ingestion & Decoupling

The FastAPI server provides high-throughput ingestion via `/api/packets/batch`:
- Incoming observations are placed into an in-memory `asyncio.Queue`.
- Dedicated worker tasks drain the queue to update tag states and log to `position_history.db` using WAL mode.
- Front-end WebSocket clients receive debounced updates at 10–20 Hz rather than raw per-packet updates, preserving browser render performance.

---

## 5. Tag-Side Power & Transmission Tuning

To maximize battery lifetime and minimize channel collisions for hundreds of tags:

| Tag Motion State | Advertising Interval | Transmit Power (Tx) | Estimated Battery Life (CR2032) |
|---|---|---|---|
| **Stationary / Static** | 1000 ms (1.0 Hz) | -4 dBm | 3.5 – 5.0 years |
| **In-Motion (IMU Triggered)** | 200 ms (5.0 Hz) | 0 dBm | 1.0 – 1.8 years |
| **Emergency / Alert** | 50 ms (20.0 Hz) | +4 dBm | 3 – 6 months |

By incorporating IMU-based accelerometer interrupt waking (broadcasting rapidly only when movement is detected), mMTC channel load is reduced by over 80% in typical enterprise environments.
