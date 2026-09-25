# ESP32 Precompiled Binary Directory

Place compiled application binaries (`.bin`) here (e.g. `esp32_wifi_anchor.bin`).

When present, `setup.py` automatically detects them and flashes them to the connected ESP32 board ROM at offset `0x10000` via `esptool write_flash` at 460800 baud before injecting the NVS wireless parameters.
