# Dissertation Project Audit

Audit date: 2026-09-06

## Scope

I reviewed the frontend React/Vite workspace, the dissertation validation docs, and the backend Python test surface in `ble-indoor-positioning/`.

## Verdict

The project is close, but it is not fully up to the agreed standards yet.

The strongest parts are the breadth of the UI, the preserved zero-default workflow, and the passing frontend test suite. The main blockers are:

1. TypeScript still fails.
2. The backend test suite does not fully pass in the current environment.
3. The default build path is affected by a workspace permission issue.
4. A few docs and runtime assumptions are stale or non-offline.

## Checks Run

- `cmd /c npm test -- --run`
- `cmd /c npx tsc --noEmit`
- `cmd /c npm run build`
- `cmd /c npm run build -- --outDir .tmp-build-audit`
- `cmd /c .\ble-indoor-positioning\.venv\Scripts\python.exe -m pytest --collect-only -q`
- `cmd /c .\ble-indoor-positioning\.venv\Scripts\python.exe -m pytest`

## Results

### Passed

- Frontend Vitest suite passed: 5 files, 54 tests.
- A production build succeeded when written to an alternate output directory.
- The repository structure is organized and the main feature areas are present.

### Failed or Incomplete

- TypeScript type checking failed.
- Default production build to `dist/` failed in this workspace because Vite could not clear `dist/assets`.
- Backend pytest did not complete cleanly.

## Findings

### 1. TypeScript errors remain

Severity: High

- [src/components/AppShell.tsx](C:/Users/bleig/OneDrive/Desktop/Dissertation/Dissertation/src/components/AppShell.tsx#L268) checks `view === 'control'` and `view === 'training'`, but the `View` type only allows `monitor`, `collector`, `reports`, and `admin`.
- [src/components/collector/CollectorView.tsx](C:/Users/bleig/OneDrive/Desktop/Dissertation/Dissertation/src/components/collector/CollectorView.tsx#L2528) uses `M3Monitor` without importing it.

Impact:

- The codebase does not satisfy the strict type-safety standard yet.
- This also means the current frontend is one refactor away from a compile break in a stricter CI gate.

### 2. Backend tests are not clean in the current environment

Severity: High

Observed pytest result:

- 39 tests collected
- 33 passed
- 2 failed
- 4 errored

The failures are mostly permission and writeability issues:

- `ble-indoor-positioning/server/app.py` attempted to write `ble-indoor-positioning/models/schematic.json` and hit `PermissionError`.
- `ble-indoor-positioning/server/asset_registry.py` hit `sqlite3.OperationalError: attempt to write a readonly database`.
- Several pytest fixtures also failed while creating temporary paths under `C:\Users\bleig\AppData\Local\Temp\pytest-of-bleig`.

Impact:

- The backend validation matrix is not currently reproducible end-to-end in this workspace.
- The project still needs a clean writable test/runtime setup for dissertation-grade verification.

### 3. The default build path is blocked by workspace permissions

Severity: Medium

- `cmd /c npm run build` failed when Vite tried to clear `dist/assets`.
- The same build succeeded when directed to `.tmp-build-audit`.

Impact:

- The source appears buildable.
- The standard `dist/` workflow is not currently reliable in this workspace.

### 4. The project is not fully offline-safe yet

Severity: Medium

- [src/index.css](C:/Users/bleig/OneDrive/Desktop/Dissertation/Dissertation/src/index.css#L2) imports Google Fonts from `fonts.googleapis.com`.

Impact:

- This conflicts with the documented standalone/offline expectation.
- The app can still render, but it depends on an external network resource for typography.

### 5. Documentation is stale in places

Severity: Medium

- [README.md](C:/Users/bleig/OneDrive/Desktop/Dissertation/Dissertation/README.md#L147) links to a broken `file:///c:/Users/User/Desktop/...` path instead of the current workspace.
- [README.md](C:/Users/bleig/OneDrive/Desktop/Dissertation/Dissertation/README.md#L150) and [DISSERTATION_VALIDATION_PROTOCOL.md](C:/Users/bleig/OneDrive/Desktop/Dissertation/Dissertation/DISSERTATION_VALIDATION_PROTOCOL.md#L365) still describe the frontend/backend test counts as `39` and `37`, but the current frontend suite now reports `54` passing Vitest tests.

Impact:

- The dissertation record is less trustworthy than it should be.
- The validation protocol should reflect the live codebase, not an older snapshot.

## Positive Notes

- The frontend is well structured and has a broad component surface.
- The zero-default setup flow is preserved in the UI and docs.
- The frontend test suite is healthy.
- A production build is possible when the output directory is writable.

## Recommendation

Before calling the project standards-complete, fix these in order:

1. Resolve the TypeScript errors.
2. Remove or locally bundle the remote font dependency.
3. Make backend tests write to isolated, writable test fixtures.
4. Update the docs to match the current test counts and workspace paths.
5. Re-run backend tests, type checking, and the default production build.

## Bottom Line

This is a strong dissertation project, but it is not yet fully audit-clean.
The frontend is close; the main remaining work is compile correctness, test isolation, and documentation hygiene.
