/*
 * ESP32 Wireless BLE Anchor Node Firmware
 *
 * Scans for the designated BLE target tag and transmits real-time telemetry
 * wirelessly over local Wi-Fi via UDP directly to the laptop Collector.
 *
 * Configurable dynamically via Serial UART or permanently saved in NVS Flash.
 */

#include <WiFi.h>
#include <WiFiUdp.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>
#include <Preferences.h>

#define STATUS_LED_PIN 2
#define SERIAL_BAUD 115200

// Default Configuration Defaults
static const char* DEFAULT_SSID = "IndoorPositioning_WiFi";
static const char* DEFAULT_PASS = "YOUR_WIFI_PASSWORD";
static const char* DEFAULT_ANCHOR_ID = "NODE_A";
static const char* DEFAULT_TARGET_MAC = "52:06:26:03:01:DA";
static const char* DEFAULT_HOST_IP = "255.255.255.255"; // UDP Broadcast by default
static const uint16_t DEFAULT_UDP_PORT = 5005;

// Runtime Configuration Variables
String g_wifi_ssid;
String g_wifi_pass;
String g_anchor_id;
String g_target_mac;
String g_host_ip;
uint16_t g_udp_port = DEFAULT_UDP_PORT;

String g_device_mac = "";
WiFiUDP g_udp;
Preferences g_prefs;
BLEScan* g_ble_scan = nullptr;
bool g_is_scanning = false;
unsigned long g_last_heartbeat = 0;
bool g_led_state = false;

// Forward declarations
void load_configuration();
void save_configuration();
void setup_wifi();
void setup_ble();
void process_serial_commands();
void send_udp_packet(const String& payload);
void send_heartbeat();

class AdvertisedDeviceCallbacks: public BLEAdvertisedDeviceCallbacks {
    void onResult(BLEAdvertisedDevice advertisedDevice) override {
        String dev_mac = advertisedDevice.getAddress().toString().c_str();
        dev_mac.toUpperCase();

        if (dev_mac.equalsIgnoreCase(g_target_mac)) {
            int rssi = advertisedDevice.getRSSI();
            unsigned long timestamp_ms = millis();

            // Toggle Status LED on valid packet capture
            g_led_state = !g_led_state;
            digitalWrite(STATUS_LED_PIN, g_led_state ? HIGH : LOW);

            // Construct JSON Telemetry
            String json_payload = "{\"type\":\"raw\",\"node\":\"" + g_anchor_id + "\","
                                  "\"mac\":\"" + g_device_mac + "\","
                                  "\"tag\":\"" + dev_mac + "\","
                                  "\"rssi\":" + String(rssi) + ","
                                  "\"timestamp\":" + String(timestamp_ms) + "}";

            // Send via UDP over local Wi-Fi
            send_udp_packet(json_payload);

            // Also echo over Serial for debugging/diagnostics
            Serial.println(json_payload);
        }
    }
};

void setup() {
    Serial.begin(SERIAL_BAUD);
    pinMode(STATUS_LED_PIN, OUTPUT);
    digitalWrite(STATUS_LED_PIN, LOW);

    delay(500);
    Serial.println("\n--- ESP32 Wireless BLE Anchor Node Initializing ---");

    // Fetch hardware silicon MAC address
    g_device_mac = WiFi.macAddress();
    g_device_mac.toUpperCase();
    Serial.print("[SYSTEM] Silicon Hardware MAC: ");
    Serial.println(g_device_mac);

    // Load persisted settings from NVS Flash
    load_configuration();

    // Connect to local Wi-Fi network
    setup_wifi();

    // Initialize BLE Scanner
    setup_ble();

    Serial.println("[SYSTEM] Anchor Ready. Listening for serial commands or target tags...");
}

void loop() {
    // 1. Process runtime UART configuration commands from setup tool
    process_serial_commands();

    // 2. Periodic heartbeat over UDP (every 3000ms) to indicate online status
    if (WiFi.status() == WL_CONNECTED && (millis() - g_last_heartbeat > 3000)) {
        send_heartbeat();
        g_last_heartbeat = millis();
    }

    // 3. Keep BLE scan active
    if (!g_is_scanning && g_ble_scan != nullptr) {
        g_ble_scan->start(0, nullptr, false);
        g_is_scanning = true;
    }

    delay(10);
}

void load_configuration() {
    g_prefs.begin("anchor_cfg", true);
    g_wifi_ssid = g_prefs.getString("ssid", DEFAULT_SSID);
    g_wifi_pass = g_prefs.getString("pass", DEFAULT_PASS);
    g_anchor_id = g_prefs.getString("anchor", DEFAULT_ANCHOR_ID);
    g_target_mac = g_prefs.getString("tag", DEFAULT_TARGET_MAC);
    g_target_mac.toUpperCase();
    g_host_ip = g_prefs.getString("host", DEFAULT_HOST_IP);
    g_udp_port = g_prefs.getUShort("port", DEFAULT_UDP_PORT);
    g_prefs.end();

    Serial.println("[CONFIG] Configuration Loaded from NVS:");
    Serial.println("  • Node ID:    " + g_anchor_id);
    Serial.println("  • Target MAC: " + g_target_mac);
    Serial.println("  • Wi-Fi SSID: " + g_wifi_ssid);
    Serial.println("  • Host IP:    " + g_host_ip + ":" + String(g_udp_port));
}

void save_configuration() {
    g_prefs.begin("anchor_cfg", false);
    g_prefs.putString("ssid", g_wifi_ssid);
    g_prefs.putString("pass", g_wifi_pass);
    g_prefs.putString("anchor", g_anchor_id);
    g_prefs.putString("tag", g_target_mac);
    g_prefs.putString("host", g_host_ip);
    g_prefs.putUShort("port", g_udp_port);
    g_prefs.end();
    Serial.println("{\"status\":\"ok\",\"message\":\"Configuration permanently committed to NVS flash\"}");
}

void setup_wifi() {
    Serial.print("[WIFI] Connecting to SSID: ");
    Serial.println(g_wifi_ssid);

    WiFi.mode(WIFI_STA);
    WiFi.disconnect();
    delay(100);

    WiFi.begin(g_wifi_ssid.c_str(), g_wifi_pass.c_str());

    unsigned long start_attempt = millis();
    int blink = 0;
    while (WiFi.status() != WL_CONNECTED && millis() - start_attempt < 10000) {
        delay(250);
        digitalWrite(STATUS_LED_PIN, (blink++ % 2 == 0) ? HIGH : LOW);
        Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n[WIFI] Connected Successfully!");
        Serial.print("[WIFI] Node IP: ");
        Serial.println(WiFi.localIP());
        digitalWrite(STATUS_LED_PIN, HIGH);
        g_udp.begin(g_udp_port);
    } else {
        Serial.println("\n[WIFI] Connection Timeout! Check SSID/Password or AP availability.");
        digitalWrite(STATUS_LED_PIN, LOW);
    }
}

void setup_ble() {
    Serial.println("[BLE] Initializing BLE Scanner...");
    BLEDevice::init(g_anchor_id.c_str());
    g_ble_scan = BLEDevice::getScan();
    g_ble_scan->setAdvertisedDeviceCallbacks(new AdvertisedDeviceCallbacks(), true);
    g_ble_scan->setActiveScan(true);
    g_ble_scan->setInterval(100);
    g_ble_scan->setWindow(99);
    Serial.println("[BLE] Scanner Initialized and Listening.");
}

void send_udp_packet(const String& payload) {
    if (WiFi.status() != WL_CONNECTED) return;

    IPAddress targetIP;
    if (g_host_ip == "255.255.255.255") {
        targetIP = IPAddress(255, 255, 255, 255);
    } else if (!targetIP.fromString(g_host_ip)) {
        targetIP = IPAddress(255, 255, 255, 255);
    }

    g_udp.beginPacket(targetIP, g_udp_port);
    g_udp.write((const uint8_t*)payload.c_str(), payload.length());
    g_udp.endPacket();
}

void send_heartbeat() {
    String hb = "{\"type\":\"heartbeat\",\"node\":\"" + g_anchor_id + "\","
                "\"mac\":\"" + g_device_mac + "\","
                "\"ip\":\"" + WiFi.localIP().toString() + "\","
                "\"wifi_rssi\":" + String(WiFi.RSSI()) + "}";
    send_udp_packet(hb);
}

void process_serial_commands() {
    if (!Serial.available()) return;

    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) return;

    if (line.equalsIgnoreCase("HELP")) {
        Serial.println("--- ESP32 Anchor Console Commands ---");
        Serial.println("HELP                          Show this command list");
        Serial.println("GET_CONFIG                    Output current configuration JSON");
        Serial.println("GET_MAC                       Print hardware silicon MAC");
        Serial.println("SET_ANCHOR=<ID>               Set Anchor Node ID (e.g. NODE_A)");
        Serial.println("SET_TAG=<MAC>                 Set Target Tag MAC (e.g. 52:06:26:03:01:DA)");
        Serial.println("SET_SSID=<SSID>               Set Wi-Fi SSID");
        Serial.println("SET_PASS=<PASS>               Set Wi-Fi Password");
        Serial.println("SET_WIFI=<SSID>,<PASS>        Set both Wi-Fi SSID and Password");
        Serial.println("SET_HOST=<IP>                 Set Host Laptop Receiver IP");
        Serial.println("SET_PORT=<PORT>               Set UDP Port (default 5005)");
        Serial.println("SAVE_CONFIG                   Commit settings to NVS Flash");
        Serial.println("RECONNECT_WIFI                Reconnect to Wi-Fi with active credentials");
        Serial.println("REBOOT                        Restart ESP32");
        return;
    }

    if (line.equalsIgnoreCase("GET_CONFIG")) {
        String out = "{\"type\":\"config\",\"node\":\"" + g_anchor_id + "\","
                     "\"mac\":\"" + g_device_mac + "\","
                     "\"tag\":\"" + g_target_mac + "\","
                     "\"ssid\":\"" + g_wifi_ssid + "\","
                     "\"host\":\"" + g_host_ip + "\","
                     "\"port\":" + String(g_udp_port) + ","
                     "\"wifi_connected\":" + (WiFi.status() == WL_CONNECTED ? "true" : "false") + ","
                     "\"ip\":\"" + (WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : "0.0.0.0") + "\"}";
        Serial.println(out);
        return;
    }

    if (line.equalsIgnoreCase("GET_MAC")) {
        Serial.println("{\"status\":\"ok\",\"mac\":\"" + g_device_mac + "\"}");
        return;
    }

    if (line.startsWith("SET_ANCHOR=")) {
        g_anchor_id = line.substring(11);
        save_configuration();
        Serial.println("{\"status\":\"ok\",\"anchor_id\":\"" + g_anchor_id + "\"}");
        return;
    }

    if (line.startsWith("SET_TAG=")) {
        g_target_mac = line.substring(8);
        g_target_mac.toUpperCase();
        save_configuration();
        Serial.println("{\"status\":\"ok\",\"target_mac\":\"" + g_target_mac + "\"}");
        return;
    }

    if (line.startsWith("SET_SSID=")) {
        g_wifi_ssid = line.substring(9);
        save_configuration();
        Serial.println("{\"status\":\"ok\",\"ssid\":\"" + g_wifi_ssid + "\"}");
        return;
    }

    if (line.startsWith("SET_PASS=")) {
        g_wifi_pass = line.substring(9);
        save_configuration();
        Serial.println("{\"status\":\"ok\",\"message\":\"Password updated\"}");
        return;
    }

    if (line.startsWith("SET_WIFI=")) {
        String val = line.substring(9);
        int comma = val.indexOf(',');
        if (comma != -1) {
            g_wifi_ssid = val.substring(0, comma);
            g_wifi_pass = val.substring(comma + 1);
            save_configuration();
            Serial.println("{\"status\":\"ok\",\"ssid\":\"" + g_wifi_ssid + "\"}");
        } else {
            Serial.println("{\"status\":\"error\",\"message\":\"Usage: SET_WIFI=SSID,PASSWORD\"}");
        }
        return;
    }

    if (line.startsWith("SET_HOST=")) {
        g_host_ip = line.substring(9);
        save_configuration();
        Serial.println("{\"status\":\"ok\",\"host\":\"" + g_host_ip + "\"}");
        return;
    }

    if (line.startsWith("SET_PORT=")) {
        g_udp_port = (uint16_t)line.substring(9).toInt();
        save_configuration();
        Serial.println("{\"status\":\"ok\",\"port\":" + String(g_udp_port) + "}");
        return;
    }

    if (line.equalsIgnoreCase("SAVE_CONFIG")) {
        save_configuration();
        return;
    }

    if (line.equalsIgnoreCase("RECONNECT_WIFI")) {
        setup_wifi();
        return;
    }

    if (line.equalsIgnoreCase("REBOOT")) {
        Serial.println("{\"status\":\"ok\",\"message\":\"Rebooting ESP32...\"}");
        delay(200);
        ESP.restart();
        return;
    }

    Serial.println("{\"status\":\"error\",\"message\":\"Unknown command. Type HELP for available commands.\"}");
}
