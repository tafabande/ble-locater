import asyncio
import struct
import json
import time
import os
from bleak import BleakClient, BleakError
TAG_MAC = '52:06:26:03:01:DA'
SERVICE_UUID = '00001803-494c-4f47-4943-544543480000'
TELEMETRY_CHAR_UUID = '00001804-494c-4f47-4943-544543480000'
AUTH_CHAR_UUID = '00001805-494c-4f47-4943-544543480000'
AUTH_PASSWORD = '123456'
REPORT_FILE = 'reports/ble_investigation_log.txt'

def decode_value(data: bytes) -> dict:
    interpretations = {}
    interpretations['raw_bytes'] = list(data)
    interpretations['hex_dump'] = data.hex().upper()
    try:
        interpretations['ascii'] = data.decode('utf-8').strip()
    except UnicodeDecodeError:
        interpretations['ascii'] = 'Non-printable (UnicodeDecodeError)'
    if 'ascii' in interpretations and interpretations['ascii'].startswith('{'):
        try:
            interpretations['json'] = json.loads(interpretations['ascii'])
        except Exception:
            interpretations['json'] = 'Invalid JSON string structure'
    length = len(data)
    if length >= 1:
        interpretations['int8'] = struct.unpack('>b', data[0:1])[0]
        interpretations['uint8'] = struct.unpack('>B', data[0:1])[0]
    if length >= 2:
        interpretations['int16_le'] = struct.unpack('<h', data[0:2])[0]
        interpretations['int16_be'] = struct.unpack('>h', data[0:2])[0]
        interpretations['uint16_le'] = struct.unpack('<H', data[0:2])[0]
        interpretations['uint16_be'] = struct.unpack('>H', data[0:2])[0]
    if length >= 4:
        interpretations['int32_le'] = struct.unpack('<i', data[0:4])[0]
        interpretations['int32_be'] = struct.unpack('>i', data[0:4])[0]
        interpretations['uint32_le'] = struct.unpack('<I', data[0:4])[0]
        interpretations['uint32_be'] = struct.unpack('>I', data[0:4])[0]
        try:
            interpretations['float_le'] = struct.unpack('<f', data[0:4])[0]
            interpretations['float_be'] = struct.unpack('>f', data[0:4])[0]
        except Exception:
            pass
    if length >= 8:
        try:
            interpretations['double_le'] = struct.unpack('<d', data[0:8])[0]
            interpretations['double_be'] = struct.unpack('>d', data[0:8])[0]
        except Exception:
            pass
    return interpretations

async def main():
    print(f'=== Starting Phase 5.5 BLE Capability Investigation ===')
    print(f'Target Device MAC: {TAG_MAC}')
    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
    report_lines = []

    def log(msg: str):
        print(msg)
        report_lines.append(msg)
    log(f"Connection initiated at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    client = BleakClient(TAG_MAC, timeout=15.0)
    try:
        log(f'[CONN] Connecting to {TAG_MAC}...')
        await client.connect()
        log(f'[CONN] Connected: {client.is_connected}')
        log('[DISCO] Discovering GATT services and characteristics...')
        services = await client.get_services()
        custom_service_found = False
        for s in services:
            log(f'Service: {s.uuid} ({s.description})')
            for c in s.characteristics:
                log(f'  └─ Char: {c.uuid} - Properties: {c.properties}')
                if s.uuid.lower() == SERVICE_UUID.lower():
                    custom_service_found = True
        if custom_service_found:
            log(f'[DISCO] SUCCESS: Target Custom Service UUID {SERVICE_UUID} found!')
        else:
            log(f'[DISCO] WARNING: Custom Service UUID {SERVICE_UUID} was not found on this peripheral device.')
        log(f'[AUTH] Attempting authentication to write-char {AUTH_CHAR_UUID}...')
        auth_outcome = 'Unknown'
        try:
            await asyncio.wait_for(client.write_gatt_char(AUTH_CHAR_UUID, AUTH_PASSWORD.encode('utf-8'), response=True), timeout=5.0)
            auth_outcome = 'Success'
            log(f'[AUTH] Outcome: Success (Password accepted)')
        except asyncio.TimeoutError:
            auth_outcome = 'Timeout'
            log(f'[AUTH] Outcome: Timeout (Device did not respond in time)')
        except BleakError as be:
            err_msg = str(be).lower()
            if 'permission' in err_msg or 'not permitted' in err_msg:
                auth_outcome = 'Permission denied'
            elif 'not found' in err_msg or 'unsupported' in err_msg:
                auth_outcome = 'Unsupported'
            else:
                auth_outcome = f'Failure ({str(be)})'
            log(f'[AUTH] Outcome: {auth_outcome}')
        except Exception as e:
            auth_outcome = f'Failure ({str(e)})'
            log(f'[AUTH] Outcome: {auth_outcome}')
        log(f'[READ] Reading telemetry characteristic {TELEMETRY_CHAR_UUID}...')
        try:
            val_bytes = await asyncio.wait_for(client.read_gatt_char(TELEMETRY_CHAR_UUID), timeout=5.0)
            log(f'[READ] Success: Retrieved {len(val_bytes)} bytes.')
            decodings = decode_value(val_bytes)
            log('\n--- Decoded Telemetry Characteristic Data ---')
            log(f"Hex Dump:   {decodings.get('hex_dump')}")
            log(f"Raw Bytes:  {decodings.get('raw_bytes')}")
            log(f"ASCII Str:  {decodings.get('ascii')}")
            if 'json' in decodings:
                log(f"JSON Dict:  {json.dumps(decodings['json'], indent=2)}")
            if 'int8' in decodings:
                log(f"Integers:   int8={decodings['int8']}, uint8={decodings['uint8']}")
            if 'int16_le' in decodings:
                log(f"16-bit Int: LE={decodings['int16_le']} | BE={decodings['int16_be']}")
            if 'int32_le' in decodings:
                log(f"32-bit Int: LE={decodings['int32_le']} | BE={decodings['int32_be']}")
            if 'float_le' in decodings:
                log(f"Floats:     LE={decodings['float_le']:.4f} | BE={decodings['float_be']:.4f}")
            if 'double_le' in decodings:
                log(f"Doubles:    LE={decodings['double_le']:.6f} | BE={decodings['double_be']:.6f}")
            log('---------------------------------------------\n')
            with open(REPORT_FILE, 'a') as rf:
                rf.write(f'\nTelemetry decoded at {time.time()}:\n{json.dumps(decodings, indent=2)}\n')
        except asyncio.TimeoutError:
            log('[READ] Failure: Timeout reading characteristic')
        except BleakError as be:
            log(f'[READ] Failure: {be}')
        except Exception as e:
            log(f'[READ] Failure: {e}')
    except Exception as e:
        log(f'[CONN] Connection error: {e}')
    finally:
        if client.is_connected:
            log('[CONN] Disconnecting...')
            await client.disconnect()
            log('[CONN] Disconnected.')
    with open(REPORT_FILE, 'w') as rf:
        rf.write('\n'.join(report_lines) + '\n')
    print(f'[INFO] Full investigation log saved to: {REPORT_FILE}')
if __name__ == '__main__':
    asyncio.run(main())
