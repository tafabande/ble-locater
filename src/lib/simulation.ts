import { useEffect, useRef, useState } from 'react'

// ---- Types ------------------------------------------------------------------

export type TagStatus = 'online' | 'stale' | 'lost'
export type Severity = 'info' | 'warning' | 'critical'

export interface Calibration {
  n: number // path-loss exponent (ML-fitted)
  envDb: number // environmental attenuation offset, dB
  rmse: number // model residual, meters
  r2: number // fit quality 0..1
  samples: number
  updated: number // ts
}

export interface Anchor {
  id: string
  label: string
  x: number // percent of floor width
  y: number // percent of floor depth
  z: number // mount height within its storey, meters
  floor: number // storey index, 0 = ground
  ssid: string
  channel: number
  txPower: number // calibrated 1m RSSI, dBm
  host: boolean // serves the web UI
  cal: Calibration
}

export interface AnchorReading {
  anchorId: string
  rssi: number // dBm
  distance: number // meters
  used: boolean // used in the position solve
}

export interface Tag {
  id: string
  label: string
  zone: string
  x: number
  y: number
  floor: number // storey the tag is on
  battery: number
  status: TagStatus
  lastSeen: number // ms since last packet
  nearest: string // anchor id
  uncertainty: number // 1σ position uncertainty, meters (post-Kalman)
  readings: AnchorReading[]
  trail: { x: number; y: number }[]
  rssiHistory: number[]
  violating: string | null // geofence id currently violated
}

export interface Geofence {
  id: string
  name: string
  x: number
  y: number
  w: number
  h: number
  restricted: boolean // triggers alerts on unauthorized entry
  allow: string[] // tag ids permitted inside a restricted fence
}

export type MapItemKind = 'wall' | 'furniture' | 'door'

export interface MapItem {
  id: string
  kind: MapItemKind
  label: string
  x: number
  y: number
  w: number
  h: number
  attenuation: number // dB added when line-of-sight crosses this item
}

export interface EventRow {
  id: string
  ts: number
  tag: string
  zone: string
  type: 'enter' | 'exit' | 'connect' | 'disconnect' | 'low-battery'
  detail: string
}

export interface Alert {
  id: string
  ts: number
  severity: Severity
  kind: 'geofence' | 'signal-lost' | 'low-battery' | 'calibration'
  tag: string
  message: string
  acknowledged: boolean
}

export interface PipelineStage {
  id: string
  label: string
  status: 'ok' | 'warn' | 'error'
  latencyMs: number
  detail: string
}

export interface SimState {
  anchors: Anchor[]
  tags: Tag[]
  geofences: Geofence[]
  events: EventRow[]
  alerts: Alert[]
  pipeline: PipelineStage[]
  seenSeries: { t: string; tags: number; packets: number }[]
  packetsPerSec: number
  startedAt: number
}

// ---- Static topology --------------------------------------------------------

// Storey height in iso/scene units; total building height derives from it.
export const STOREY_HEIGHT = 10
export const FLOORS: { id: number; name: string }[] = [
  { id: 0, name: 'Ground' },
  { id: 1, name: 'Level 2' },
  { id: 2, name: 'Level 3' },
]
export const BUILDING = { width: 100, depth: 100, height: FLOORS.length * STOREY_HEIGHT }

export const GEOFENCES: Geofence[] = [
  { id: 'lobby', name: 'Lobby', x: 4, y: 4, w: 40, h: 34, restricted: false, allow: [] },
  { id: 'office', name: 'Office', x: 48, y: 4, w: 48, h: 34, restricted: false, allow: [] },
  { id: 'warehouse', name: 'Warehouse A', x: 4, y: 42, w: 56, h: 54, restricted: false, allow: [] },
  // Cold Store is restricted: only the cold-chain bin tag may dwell inside.
  { id: 'cold', name: 'Cold Store', x: 64, y: 42, w: 32, h: 54, restricted: true, allow: ['0x2E55'] },
]

export const FLOOR_ZONES = GEOFENCES

// Pre-mapped, furnished floor (Unity-style static geometry). Walls & furniture
// are solid (tags cannot occupy them) and occlude RF (fixed, known distortion
// the position solver can compensate for). Doors are passable openings.
export const DEFAULT_MAP: MapItem[] = [
  // interior partition walls (with door gaps left open)
  { id: 'w1', kind: 'wall', label: 'Partition', x: 44, y: 4, w: 1.6, h: 13, attenuation: 8 },
  { id: 'w2', kind: 'wall', label: 'Partition', x: 44, y: 24, w: 1.6, h: 14, attenuation: 8 },
  { id: 'w3', kind: 'wall', label: 'Partition', x: 4, y: 38, w: 38, h: 1.6, attenuation: 8 },
  { id: 'w4', kind: 'wall', label: 'Cold wall', x: 62.4, y: 40, w: 1.6, h: 20, attenuation: 10 },
  { id: 'w5', kind: 'wall', label: 'Cold wall', x: 62.4, y: 68, w: 1.6, h: 28, attenuation: 10 },
  // openings
  { id: 'd1', kind: 'door', label: 'Door', x: 44, y: 17, w: 1.6, h: 7, attenuation: 0 },
  { id: 'd2', kind: 'door', label: 'Door', x: 62.4, y: 60, w: 1.6, h: 8, attenuation: 0 },
  // furniture
  { id: 'f1', kind: 'furniture', label: 'Racking A', x: 10, y: 50, w: 22, h: 4.5, attenuation: 4 },
  { id: 'f2', kind: 'furniture', label: 'Racking B', x: 10, y: 64, w: 22, h: 4.5, attenuation: 4 },
  { id: 'f3', kind: 'furniture', label: 'Racking C', x: 10, y: 78, w: 22, h: 4.5, attenuation: 4 },
  { id: 'f4', kind: 'furniture', label: 'Desks', x: 54, y: 12, w: 13, h: 8, attenuation: 2 },
  { id: 'f5', kind: 'furniture', label: 'Reception', x: 8, y: 10, w: 14, h: 6, attenuation: 2 },
  { id: 'f6', kind: 'furniture', label: 'Freezer bank', x: 70, y: 46, w: 18, h: 8, attenuation: 6 },
]

// ---- Geometry ---------------------------------------------------------------

export function pointInRect(px: number, py: number, r: { x: number; y: number; w: number; h: number }): boolean {
  return px >= r.x && px <= r.x + r.w && py >= r.y && py <= r.y + r.h
}

// Liang–Barsky: does segment (x0,y0)->(x1,y1) intersect the rectangle?
export function segIntersectsRect(x0: number, y0: number, x1: number, y1: number, r: { x: number; y: number; w: number; h: number }): boolean {
  const dx = x1 - x0
  const dy = y1 - y0
  const p = [-dx, dx, -dy, dy]
  const q = [x0 - r.x, r.x + r.w - x0, y0 - r.y, r.y + r.h - y0]
  let t0 = 0
  let t1 = 1
  for (let i = 0; i < 4; i++) {
    if (p[i] === 0) {
      if (q[i] < 0) return false
    } else {
      const t = q[i] / p[i]
      if (p[i] < 0) {
        if (t > t1) return false
        if (t > t0) t0 = t
      } else {
        if (t < t0) return false
        if (t < t1) t1 = t
      }
    }
  }
  return true
}

const SOLID: MapItemKind[] = ['wall', 'furniture']
export function isSolid(item: MapItem): boolean {
  return SOLID.includes(item.kind)
}

function mkCal(n: number, r2: number, rmse: number): Calibration {
  return { n, envDb: Math.round((n - 2) * 6 * 10) / 10, rmse, r2, samples: 1200 + Math.round(Math.random() * 800), updated: Date.now() - Math.round(Math.random() * 6e6) }
}

// Base anchor layout, replicated on every storey so each floor has coverage.
const ANCHOR_LAYOUT: { x: number; y: number; z: number; txPower: number; cal: Calibration }[] = [
  { x: 14, y: 16, z: 8.5, txPower: -59, cal: mkCal(2.2, 0.96, 0.42) },
  { x: 78, y: 16, z: 8.5, txPower: -61, cal: mkCal(2.35, 0.93, 0.58) },
  { x: 30, y: 74, z: 8.2, txPower: -58, cal: mkCal(2.1, 0.97, 0.36) },
  { x: 80, y: 74, z: 8.8, txPower: -60, cal: mkCal(2.5, 0.89, 0.71) },
  { x: 50, y: 40, z: 8.8, txPower: -59, cal: mkCal(2.25, 0.95, 0.47) },
]
const CHANNELS = [1, 6, 11, 6, 1]

export const ANCHORS: Anchor[] = FLOORS.flatMap((f) =>
  ANCHOR_LAYOUT.map((a, i) => {
    const n = f.id * ANCHOR_LAYOUT.length + i + 1
    return {
      id: `N${n}`,
      label: `ANCHOR-N${n}`,
      x: a.x,
      y: a.y,
      z: a.z,
      floor: f.id,
      ssid: `FleetMesh-${String(n).padStart(2, '0')}`,
      channel: CHANNELS[i],
      txPower: a.txPower,
      host: f.id === 0 && i === 0, // ground-floor N1 serves the web UI
      cal: a.cal,
    }
  })
)

interface Seed {
  id: string
  label: string
  battery: number
  x: number
  y: number
  vx: number
  vy: number
  floor: number
}

const TAG_SEEDS: Seed[] = [
  { id: '0x4F2A', label: 'Forklift 3', battery: 82, x: 22, y: 55, vx: 0.5, vy: 0.3, floor: 0 },
  { id: '0x18C7', label: 'Pallet Jack', battery: 46, x: 70, y: 60, vx: -0.4, vy: 0.4, floor: 0 },
  { id: '0x9B03', label: 'Asset Cart', battery: 91, x: 30, y: 20, vx: 0.3, vy: 0.5, floor: 0 },
  { id: '0x2E55', label: 'Cold Bin 7', battery: 63, x: 78, y: 66, vx: 0.2, vy: -0.3, floor: 0 },
  { id: '0xA1D9', label: 'Tech Badge', battery: 28, x: 60, y: 18, vx: -0.5, vy: 0.2, floor: 1 },
  { id: '0x77F1', label: 'Scanner 12', battery: 74, x: 45, y: 80, vx: 0.4, vy: -0.4, floor: 1 },
  { id: '0xC4B8', label: 'Visitor 04', battery: 55, x: 15, y: 25, vx: 0.6, vy: 0.4, floor: 2 },
]

// ---- Helpers ----------------------------------------------------------------

export function geofenceAt(x: number, y: number): Geofence | null {
  for (const z of GEOFENCES) {
    if (x >= z.x && x <= z.x + z.w && y >= z.y && y <= z.y + z.h) return z
  }
  return null
}

function zoneAt(x: number, y: number): string {
  return geofenceAt(x, y)?.name ?? 'Transit'
}

// RSSI from log-distance path loss model, plus fixed occlusion from mapped
// obstacles between the anchor and the tag. Floor is ~100% x 100% (meters-ish).
export function readingFor(anchor: Anchor, tag: { x: number; y: number }, items?: MapItem[]): AnchorReading {
  const dx = (anchor.x - tag.x) * 0.28
  const dy = (anchor.y - tag.y) * 0.28
  const dist = Math.max(0.4, Math.hypot(dx, dy))
  const n = anchor.cal?.n ?? 2.2
  let att = 0
  if (items) {
    for (const it of items) {
      if (it.attenuation > 0 && segIntersectsRect(anchor.x, anchor.y, tag.x, tag.y, it)) att += it.attenuation
    }
  }
  const rssi = anchor.txPower - 10 * n * Math.log10(dist) - att + (Math.random() * 3 - 1.5)
  return { anchorId: anchor.id, rssi: Math.round(rssi), distance: Math.round(dist * 10) / 10, used: false }
}

// Position uncertainty (post-Kalman 1σ) from anchor geometry + signal quality.
export function uncertaintyFor(readings: AnchorReading[]): number {
  const strong = readings.filter((r) => r.rssi > -78).length
  const base = strong >= 4 ? 0.5 : strong === 3 ? 0.9 : strong === 2 ? 1.8 : strong === 1 ? 3.0 : 4.5
  return Math.round((base + Math.random() * 0.4) * 10) / 10
}

export function statusFromLastSeen(ms: number): TagStatus {
  if (ms < 4000) return 'online'
  if (ms < 12000) return 'stale'
  return 'lost'
}

let uid = 0
function nextId(p: string) {
  return `${p}${Date.now()}-${uid++}`
}

// ---- The hook ---------------------------------------------------------------

interface Internal extends Seed {
  lastSeen: number
  zone: string
  dropping: boolean
  violating: string | null
}

export function useSimulation(intervalMs = 1500, enabled = true, mapItems: MapItem[] = DEFAULT_MAP) {
  // All refs first, then useState — the state initializer calls build(), which
  // reads mapRef/trails/startedAt, so those refs must exist beforehand.
  const internal = useRef<Internal[]>(
    TAG_SEEDS.map((s) => ({ ...s, lastSeen: 0, zone: zoneAt(s.x, s.y), dropping: false, violating: null }))
  )
  const startedAt = useRef(Date.now())
  const trails = useRef<Record<string, { x: number; y: number }[]>>({})
  const rssiHist = useRef<Record<string, number[]>>({})
  const mapRef = useRef(mapItems)
  mapRef.current = mapItems
  const intervalRef = useRef(intervalMs)
  intervalRef.current = intervalMs

  const [state, setState] = useState<SimState>(() => build(internal.current, [], [], []))

  function build(items: Internal[], events: EventRow[], alerts: Alert[], series: SimState['seenSeries']): SimState {
    const map = mapRef.current
    const tags: Tag[] = items.map((it) => {
      // only same-floor anchors can hear the tag
      const floorAnchors = ANCHORS.filter((a) => a.floor === it.floor)
      const readings = floorAnchors.map((a) => readingFor(a, it, map)).sort((x, y) => y.rssi - x.rssi)
      readings.forEach((r, i) => (r.used = i < 3)) // strongest 3 feed the solver
      const nearest = readings[0].anchorId
      return {
        id: it.id,
        label: it.label,
        zone: it.zone,
        x: it.x,
        y: it.y,
        floor: it.floor,
        battery: Math.round(it.battery),
        status: statusFromLastSeen(it.lastSeen),
        lastSeen: it.lastSeen,
        nearest,
        uncertainty: uncertaintyFor(readings),
        readings,
        trail: trails.current[it.id] ?? [],
        rssiHistory: rssiHist.current[it.id] ?? [],
        violating: it.violating,
      }
    })
    const online = tags.filter((t) => t.status !== 'lost').length
    return {
      anchors: ANCHORS,
      tags,
      geofences: GEOFENCES,
      events,
      alerts,
      pipeline: buildPipeline(tags, alerts, online),
      seenSeries: series,
      packetsPerSec: online * 5 + Math.round(Math.random() * 6),
      startedAt: startedAt.current,
    }
  }

  useEffect(() => {
    if (!enabled) return
    const now = Date.now()
    const seedSeries = Array.from({ length: 16 }, (_, i) => {
      const t = new Date(now - (15 - i) * 60000)
      return {
        t: `${t.getHours().toString().padStart(2, '0')}:${t.getMinutes().toString().padStart(2, '0')}`,
        tags: 4 + Math.round(Math.sin(i / 2) * 2 + Math.random()),
        packets: 30 + Math.round(Math.cos(i / 3) * 10 + Math.random() * 8),
      }
    })

    let events: EventRow[] = seedEvents()
    let alerts: Alert[] = seedAlerts()
    let series = seedSeries
    setState((s) => ({ ...s, seenSeries: seedSeries, events, alerts }))

    const tick = () => {
      const items = internal.current
      const newEvents: EventRow[] = []
      const newAlerts: Alert[] = []
      for (const it of items) {
        if (Math.random() < 0.04) it.dropping = !it.dropping
        const wasLost = statusFromLastSeen(it.lastSeen) === 'lost'
        it.lastSeen = it.dropping ? it.lastSeen + intervalRef.current : 0

        if (!it.dropping) {
          const px = it.x
          const py = it.y
          it.x += it.vx
          it.y += it.vy
          if (it.x < 6 || it.x > 94) { it.vx *= -1; it.x = Math.max(6, Math.min(94, it.x)) }
          if (it.y < 8 || it.y > 92) { it.vy *= -1; it.y = Math.max(8, Math.min(92, it.y)) }

          // solid-obstacle collision: a tag can never be inside a wall or
          // furniture — resolve per-axis so it slides along edges realistically.
          const solids = mapRef.current.filter(isSolid)
          const hitsX = solids.some((s) => pointInRect(it.x, py, s))
          if (hitsX) { it.x = px; it.vx *= -1 }
          const hitsY = solids.some((s) => pointInRect(it.x, it.y, s))
          if (hitsY) { it.y = py; it.vy *= -1 }

          it.vx += (Math.random() - 0.5) * 0.12
          it.vy += (Math.random() - 0.5) * 0.12
          it.vx = Math.max(-0.9, Math.min(0.9, it.vx))
          it.vy = Math.max(-0.9, Math.min(0.9, it.vy))

          const fence = geofenceAt(it.x, it.y)
          const newZone = fence?.name ?? 'Transit'
          if (newZone !== it.zone) {
            newEvents.push(mkEvent(it, 'exit', `Left ${it.zone}`))
            newEvents.push(mkEvent(it, 'enter', `Entered ${newZone}`, newZone))
            it.zone = newZone
          }

          // geofence violation detection
          const violating = fence && fence.restricted && !fence.allow.includes(it.id) ? fence.id : null
          if (violating && it.violating !== violating) {
            newAlerts.push(mkAlert(it, 'critical', 'geofence', `Unauthorized entry into ${fence!.name}`))
          }
          it.violating = violating

          it.battery = Math.max(3, it.battery - Math.random() * 0.25)
          if (it.battery < 20 && Math.random() < 0.05) {
            newEvents.push(mkEvent(it, 'low-battery', `Battery ${Math.round(it.battery)}%`))
            newAlerts.push(mkAlert(it, 'warning', 'low-battery', `Battery critical at ${Math.round(it.battery)}%`))
          }

          const tr = trails.current[it.id] ?? []
          tr.push({ x: it.x, y: it.y })
          if (tr.length > 16) tr.shift()
          trails.current[it.id] = tr
        } else if (!wasLost && statusFromLastSeen(it.lastSeen) === 'lost') {
          newEvents.push(mkEvent(it, 'disconnect', 'Signal lost'))
          newAlerts.push(mkAlert(it, 'warning', 'signal-lost', 'Lost BLE signal — position stale'))
          it.violating = null
        }

        const best = ANCHORS.map((a) => readingFor(a, it, mapRef.current)).sort((x, y) => y.rssi - x.rssi)[0]
        const hist = rssiHist.current[it.id] ?? []
        hist.push(best.rssi)
        if (hist.length > 20) hist.shift()
        rssiHist.current[it.id] = hist
      }

      if (newEvents.length) events = [...newEvents, ...events].slice(0, 60)
      if (newAlerts.length) alerts = [...newAlerts, ...alerts].slice(0, 40)

      const now2 = new Date()
      const online = items.filter((it) => statusFromLastSeen(it.lastSeen) !== 'lost').length
      series = [
        ...series,
        {
          t: `${now2.getHours().toString().padStart(2, '0')}:${now2.getMinutes().toString().padStart(2, '0')}`,
          tags: online,
          packets: online * 5 + Math.round(Math.random() * 8),
        },
      ].slice(-20)

      setState(build(items, events, alerts, series))
    }

    const iv = setInterval(tick, intervalMs)
    return () => clearInterval(iv)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs, enabled])

  return state
}

// ---- Pipeline (system state) ------------------------------------------------

export function buildPipeline(tags: Tag[], alerts: Alert[], online: number): PipelineStage[] {
  const lostCount = tags.filter((t) => t.status === 'lost').length
  const meanUnc = tags.length ? tags.reduce((a, t) => a + t.uncertainty, 0) / tags.length : 0
  const activeViolations = tags.filter((t) => t.violating).length
  const jit = () => 1 + Math.round(Math.random() * 4)
  return [
    { id: 'anchors', label: 'ESP32 Anchors', status: 'ok', latencyMs: jit(), detail: `${ANCHORS.length} nodes · mesh nominal` },
    { id: 'ble', label: 'BLE Telemetry', status: online > 0 ? 'ok' : 'error', latencyMs: 3 + jit(), detail: `${online * 5} pkt/s ingest` },
    { id: 'ml', label: 'ML Distance Est.', status: 'ok', latencyMs: 8 + jit(), detail: 'log-distance regressor' },
    { id: 'cal', label: 'Calibration', status: 'ok', latencyMs: jit(), detail: `mean R² ${(ANCHORS.reduce((a, x) => a + x.cal.r2, 0) / ANCHORS.length).toFixed(2)}` },
    { id: 'trilat', label: 'Trilateration', status: lostCount > 2 ? 'warn' : 'ok', latencyMs: 6 + jit(), detail: `${tags.length - lostCount}/${tags.length} solved` },
    { id: 'kalman', label: 'Kalman Filter', status: meanUnc > 2.5 ? 'warn' : 'ok', latencyMs: 4 + jit(), detail: `σ̄ ${meanUnc.toFixed(1)} m` },
    { id: 'pos', label: '3D Position', status: 'ok', latencyMs: jit(), detail: 'x·y·z resolved' },
    { id: 'geo', label: 'Room / Geofence', status: activeViolations > 0 ? 'error' : 'ok', latencyMs: jit(), detail: activeViolations > 0 ? `${activeViolations} breach` : 'all clear' },
    { id: 'alert', label: 'Alerts', status: alerts.some((a) => a.severity === 'critical' && !a.acknowledged) ? 'error' : alerts.some((a) => !a.acknowledged) ? 'warn' : 'ok', latencyMs: jit(), detail: `${alerts.filter((a) => !a.acknowledged).length} open` },
  ]
}

function mkEvent(it: Internal, type: EventRow['type'], detail: string, zone?: string): EventRow {
  return { id: nextId('e'), ts: Date.now(), tag: `TAG-${it.id}`, zone: zone ?? it.zone, type, detail }
}

function mkAlert(it: Internal, severity: Severity, kind: Alert['kind'], message: string): Alert {
  return { id: nextId('a'), ts: Date.now(), severity, kind, tag: `TAG-${it.id}`, message, acknowledged: false }
}

function seedEvents(): EventRow[] {
  const now = Date.now()
  const types: EventRow['type'][] = ['enter', 'exit', 'connect', 'low-battery', 'disconnect']
  return Array.from({ length: 12 }, (_, i) => {
    const s = TAG_SEEDS[i % TAG_SEEDS.length]
    const type = types[i % types.length]
    return {
      id: `seed-e${i}`,
      ts: now - (i + 1) * 47000,
      tag: `TAG-${s.id}`,
      zone: zoneAt(s.x, s.y),
      type,
      detail:
        type === 'enter' ? `Entered ${zoneAt(s.x, s.y)}`
        : type === 'exit' ? 'Left Transit'
        : type === 'connect' ? 'Handshake OK'
        : type === 'low-battery' ? `Battery ${s.battery}%`
        : 'Signal lost',
    }
  })
}

function seedAlerts(): Alert[] {
  const now = Date.now()
  return [
    { id: 'seed-a0', ts: now - 62000, severity: 'critical', kind: 'geofence', tag: 'TAG-0xC4B8', message: 'Unauthorized entry into Cold Store', acknowledged: false },
    { id: 'seed-a1', ts: now - 240000, severity: 'warning', kind: 'low-battery', tag: 'TAG-0xA1D9', message: 'Battery critical at 28%', acknowledged: false },
    { id: 'seed-a2', ts: now - 510000, severity: 'warning', kind: 'signal-lost', tag: 'TAG-0x18C7', message: 'Lost BLE signal — position stale', acknowledged: true },
    { id: 'seed-a3', ts: now - 900000, severity: 'info', kind: 'calibration', tag: 'ANCHOR-N4', message: 'Recalibration recommended (R² 0.89)', acknowledged: true },
  ]
}

export function dwellByZone(tags: Tag[]) {
  return GEOFENCES.map((z) => ({
    zone: z.name,
    tags: tags.filter((t) => t.zone === z.name).length,
    dwell: 6 + Math.round((z.name.length * 3) % 22),
  }))
}
