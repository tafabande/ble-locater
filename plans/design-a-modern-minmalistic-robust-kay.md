# BLE Indoor Tag-Tracking Dashboard

## Context

The project is a blank Figma Make scaffold (`src/App.tsx` is just a placeholder dot-grid). The user wants a modern, minimalistic yet classic dashboard for monitoring BLE tag movement in an indoor space, showing real-time tag positions relative to ESP32 anchor nodes, plus an admin area with history, analytics, and configuration tabs.

Since a Figma Make frontend has no real ESP32/WiFi backend, all data is **simulated in-app**: anchors, tags, RSSI, and positions update on an interval to feel live. Navigation is **in-app view switching** (no react-router), per the user's choice. The "WiFi-hosted web server distributed from the nodes" requirement is represented in the UI as connection/node-status affordances (host node, SSID, served-from indicators, connectivity states) rather than actual networking.

## Design direction

- **Stance:** minimalist–technical, calm. Near-white ground, generous whitespace, hairline borders, one confident accent (signal teal/cyan) reserved for live pings and interactive state. Color coding only for status (online/stale/lost).
- **Fonts (Google, via `@import` at top of `src/index.css`):**
  - UI/body: `Inter`
  - Data/labels/coords/RSSI/IDs: `JetBrains Mono`
  - Headings (classic touch): `Fraunces` (used sparingly for page/section titles)
- **Tokens:** define CSS variables + a small `@theme inline` block in `src/index.css` (Tailwind v4) for background/foreground/card/border/accent/status colors so utility classes stay consistent.

## Structure

Single-page app with an app shell + in-app view switcher. Keep components modest and colocated under `src/components/`.

- `src/App.tsx` — app shell: sidebar/top nav, holds active-view state (`monitor` | `admin`), renders the simulation provider and the active view.
- `src/lib/simulation.ts` — the simulated data model + a `useSimulation` hook: fixed anchor node layout, a set of tags with (x,y) positions that drift over time, derived RSSI/distance per anchor, status (online/stale/lost), plus rolling history buffer for analytics. Uses `setInterval` in an effect; single source of truth passed via props/context.
- `src/components/AppShell.tsx` — layout, brand, nav, live clock, host-node/SSID status strip.
- **Monitor view** (`src/components/monitor/`):
  - `FloorPlan.tsx` — the hero: SVG floor plan with ESP32 anchors, animated tag dots, trilateration rings/lines to nearest anchors, hover/select a tag. Selecting a tag highlights its anchor links.
  - `TagList.tsx` — live roster: tag id, zone, nearest anchor, RSSI, battery, last-seen; click to select (syncs with FloorPlan).
  - `StatTiles.tsx` — KPI row: active tags, anchors online, avg latency, packets/s (see dataviz skill for tile craft).
  - `TagDetail.tsx` — selected-tag panel: per-anchor RSSI bars, coordinates, movement sparkline.
- **Admin view** (`src/components/admin/`) — tabbed (in-app state, not routes):
  - `History.tsx` — filterable event/movement log table (zone entry/exit, connect/disconnect, low battery) with realistic timestamps.
  - `Analytics.tsx` — `recharts`: tags-seen-over-time line, dwell-time-by-zone bar, RSSI distribution / heat-ish view. Colors from tokens (follow dataviz skill).
  - `Configuration.tsx` — settings form: anchor node table (name, coords, host/SSID, calibration TX power), refresh interval, geofence zones, retention. Controlled inputs with local state (no persistence needed).

## Key implementation notes

- Install `recharts` (charts) before use; everything else is React 19 + Tailwind v4 (already present).
- Follow the `dataviz` skill before writing any chart / stat tile / heatmap.
- Responsive: grid page layout collapses at ~1000px (floor plan stacks above roster/detail; sidebar becomes top bar). Hide scrollbars until scrolling.
- Realistic placeholder content: real-looking tag IDs (e.g. `TAG-0x4F2A`), zone names (Lobby, Warehouse A, Cold Store), ESP32 anchor names (`ANCHOR-N1`…), plausible RSSI (−40…−95 dBm) and battery %.
- Micro-details: subtle transitions on tag movement, hover/focus states, selection color, pulsing "live" indicator.
- Accessibility: AA body contrast; status conveyed by icon/label + color, not color alone.

## Files to create/modify

- Modify: `src/App.tsx`, `src/index.css`
- Create: `src/lib/simulation.ts`, `src/components/AppShell.tsx`, `src/components/monitor/*`, `src/components/admin/*`

## Verification

- Dev server already runs on `$PORT`; confirm the app compiles (hot reload).
- Manually verify: tags animate on the floor plan; selecting a tag syncs list ↔ floor plan ↔ detail; admin tabs switch and render charts; layout reflows below ~1000px.
- Optionally run `figma logs` only if a concrete runtime error appears.
