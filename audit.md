# Dissertation Project Audit

Audit date: 2026-09-06
Resolution & Verification date: 2026-09-07

## Scope

I reviewed the frontend React/Vite workspace, the dissertation validation docs, and the backend Python test surface in `ble-indoor-positioning/`.

## Verdict: Fully Standards-Compliant & Verified (Clean)

All 5 audit findings have been completely resolved and independently verified. The repository satisfies strict offline standalone requirements, TypeScript compilation standards, backend test isolation, build file stability, and documentation synchronization.

## Checks Run & Current Results

| Check | Command | Result | Details |
|---|---|---|---|
| Frontend Vitest | `cmd /c npm test -- --run` | **PASSED** | 5 test files, 54 unit and component tests passing |
| TypeScript Compiler | `cmd /c npx tsc --noEmit` | **PASSED** | 0 errors; strict type safety enforced across all components |
| Default Production Build | `cmd /c npm run build` | **PASSED** | Bundled to standard `dist/` in ~2.3s without file-lock collisions |
| Backend Pytest Suite | `.\ble-indoor-positioning\.venv\Scripts\python.exe -m pytest` | **PASSED** | 39 tests passing with 100% database & schematic fixture isolation |

---

## Findings & Resolutions

### 1. TypeScript errors remain -> RESOLVED
- **Identified Issue**: `AppShell.tsx` checked `view === 'control'` and `view === 'training'`, outside of the defined `View` union (`'monitor' | 'collector' | 'reports' | 'admin'`). `CollectorView.tsx` referenced `M3Monitor` without an import.
- **Resolution**: Updated `AppShell.tsx` to check against valid `View` literals. Added `M3Monitor` to `MaterialIcon.tsx` imports in `CollectorView.tsx`. `npx tsc --noEmit` now completes cleanly with 0 errors.

### 2. Backend test isolation & writeability -> RESOLVED
- **Identified Issue**: Tests were writing directly to production SQLite databases (`asset_registry.db`, `alerts.db`, `position_history.db`), `schematic.json`, and `last_pipeline_run.json` under `models/`. Concurrent runs or read-only file locks caused `PermissionError` and `sqlite3.OperationalError: attempt to write a readonly database`.
- **Resolution**:
  - Configured environment variable overrides in `server/app.py`, `server/asset_registry.py`, and `engineering/geofence_engine.py` (`BLE_SCHEMATIC_FILE`, `BLE_ASSET_DB_PATH`, `BLE_ALERTS_DB_PATH`, `BLE_POSITION_DB_PATH`, `BLE_CALIBRATION_FILE`, `BLE_PIPELINE_RUN_FILE`).
  - Added session-wide autouse isolation fixture in `ble-indoor-positioning/conftest.py` with `tmp_path_factory`.
  - Configured `ble-indoor-positioning/pytest.ini`.
  - All 39 backend tests now run inside an isolated temporary sandbox, leaving production models and databases completely pristine and untouched.

### 3. Default build path blocked by workspace permissions -> RESOLVED
- **Identified Issue**: Vite failed with `EPERM` when attempting to delete and recreate `dist/assets` due to Windows / OneDrive directory lock behavior.
- **Resolution**: Configured `emptyOutDir: false` in `vite.config.ts`. Default `npm run build` now completes reliably into `dist/` in ~2.3s.

### 4. Remote font dependency at runtime -> RESOLVED
- **Identified Issue**: `src/index.css` imported Google Fonts from `fonts.googleapis.com`, violating the 100% standalone and offline-compatible requirement.
- **Resolution**: Replaced the external `@import` with an offline-native system font stack (`-apple-system`, `BlinkMacSystemFont`, `'Segoe UI'`, `Roboto`, `ui-monospace`).

### 5. Documentation synchronization -> RESOLVED
- **Identified Issue**: `README.md` linked to a broken absolute file path, and both `README.md` and `DISSERTATION_VALIDATION_PROTOCOL.md` referenced outdated test counts (39/37 instead of current suites).
- **Resolution**: Updated `README.md` to link directly to `./DISSERTATION_VALIDATION_PROTOCOL.md`. Synchronized test matrices across `README.md` and `DISSERTATION_VALIDATION_PROTOCOL.md` to reflect 54 passing Vitest tests and 39 passing Pytest tests.

---

## Tooling & Architecture Notes

- **ESP32 Toolchain (`esptool`)**: `esptool v5.3.1`, `espefuse`, and `espsecure` from the Espressif toolchain have been integrated with executable wrappers in `ble-indoor-positioning\.venv\Scripts\`, allowing direct command-line execution without PATH conflicts.
- **Massive Machine-Type Communications (mMTC) Scaling**: To support scaling to dense deployments (dozens of anchors, hundreds of tags), recommendations and architecture specifications for firmware-level passive scanning, observation window aggregation, and network-backed MQTT/HTTP batching have been documented for future expansion.
