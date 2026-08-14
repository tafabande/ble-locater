import { useEffect, useRef, useState } from 'react'
import {
  ANCHORS,
  DEFAULT_MAP,
  GEOFENCES,
  buildPipeline,
  geofenceAt,
  readingFor,
  statusFromLastSeen,
  uncertaintyFor,
  type Anchor,
  type Alert,
  type EventRow,
  type SimState,
  type Tag,
} from './simulation'

export type Mode = 'demo' | 'live'
export type ConnStatus = 'connecting' | 'connected' | 'error'

export interface LiveSource {
  state: SimState | null
  status: ConnStatus
  error: string | null
  lastUpdate: number | null
  retry: () => void
}

export const EMPTY_STATE: SimState = {
  anchors: ANCHORS,
  tags: [],
  geofences: GEOFENCES,
  events: [],
  alerts: [],
  pipeline: buildPipeline([], [], 0),
  seenSeries: [],
  packetsPerSec: 0,
  startedAt: Date.now(),
}

// Shape we expect back from an anchor's web server (`GET <endpoint>`).
// Everything except tag id + position is optional — we backfill the rest.
interface RawTag {
  id: string
  label?: string
  zone?: string
  x: number
  y: number
  floor?: number
  battery?: number
  lastSeen?: number
  readings?: { anchorId: string; rssi: number; distance?: number }[]
}
interface RawPayload {
  anchors?: Anchor[]
  tags: RawTag[]
  events?: EventRow[]
  alerts?: Alert[]
}

function mapPayload(raw: RawPayload | any, prev: SimState | null): SimState {
  const anchors = Array.isArray(raw.anchors) && raw.anchors.length ? raw.anchors : ANCHORS
  const prevTrails = new Map(prev?.tags.map((t) => [t.id, t.trail]))
  const prevHist = new Map(prev?.tags.map((t) => [t.id, t.rssiHistory]))

  let rawTagList: RawTag[] = []
  if (Array.isArray(raw.tags)) {
    rawTagList = raw.tags
  } else if (raw.tags && typeof raw.tags === 'object') {
    rawTagList = Object.values(raw.tags).map((item: any) => ({
      id: item.tag_id || item.id || 'TAG_01',
      label: item.label || item.tag_id || item.id,
      zone: item.room || item.zone,
      x: item.position?.x ?? item.x ?? 2.5,
      y: item.position?.y ?? item.y ?? 2.5,
      floor: item.floor ?? 0,
      battery: item.battery ?? 100,
      lastSeen: item.last_seen ? Math.round(item.last_seen * 1000) : Date.now(),
      readings: item.distances
        ? Object.entries(item.distances).map(([ancId, dist]) => ({
            anchorId: ancId,
            rssi: -60,
            distance: typeof dist === 'number' ? dist : 2.0,
          }))
        : [],
    }))
  }

  const tags: Tag[] = rawTagList.map((rt: RawTag) => {
    const readings = (
      rt.readings?.length
        ? rt.readings.map((r: { anchorId: string; rssi: number; distance?: number }) => ({
            anchorId: r.anchorId,
            rssi: r.rssi,
            distance: r.distance ?? Math.round(Math.pow(10, ((anchors.find((a: Anchor) => a.id === r.anchorId)?.txPower ?? -59) - r.rssi) / 22) * 10) / 10,
            used: false,
          }))
        : anchors.map((a: Anchor) => readingFor(a, rt, DEFAULT_MAP))
    ).sort((a: { rssi: number }, b: { rssi: number }) => b.rssi - a.rssi)
    readings.forEach((r: { used: boolean }, i: number) => (r.used = i < 3))

    const trail = [...(prevTrails.get(rt.id) ?? []), { x: rt.x, y: rt.y }].slice(-16)
    const hist = [...(prevHist.get(rt.id) ?? []), readings[0]?.rssi ?? -100].slice(-20)
    const lastSeen = rt.lastSeen ?? 0
    const fence = geofenceAt(rt.x, rt.y)
    const violating = fence && fence.restricted && !fence.allow.includes(rt.id) ? fence.id : null

    return {
      id: rt.id,
      label: rt.label ?? `Tag ${rt.id}`,
      zone: rt.zone ?? fence?.name ?? 'Transit',
      x: rt.x,
      y: rt.y,
      floor: rt.floor ?? 0,
      battery: rt.battery ?? 100,
      status: statusFromLastSeen(lastSeen),
      lastSeen,
      nearest: readings[0]?.anchorId ?? anchors[0].id,
      uncertainty: uncertaintyFor(readings),
      readings,
      trail,
      rssiHistory: hist,
      violating,
    }
  })

  const online = tags.filter((t) => t.status !== 'lost').length
  const now = new Date()
  const stamp = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`
  const seenSeries = [
    ...(prev?.seenSeries ?? []),
    { t: stamp, tags: online, packets: online * 5 },
  ].slice(-20)
  const alerts = raw.alerts ?? prev?.alerts ?? []

  return {
    anchors,
    tags,
    geofences: GEOFENCES,
    events: raw.events ?? prev?.events ?? [],
    alerts,
    pipeline: buildPipeline(tags, alerts, online),
    seenSeries,
    packetsPerSec: online * 5,
    startedAt: prev?.startedAt ?? Date.now(),
  }
}

/**
 * Polls a live anchor-mesh web server for positioning data. Disabled entirely
 * unless `enabled` (i.e. the user switched to Live mode). Any network/parse
 * failure surfaces as `status: 'error'` so the UI can show a connection screen
 * rather than silently falling back to fake data.
 */
export function useLiveSource(enabled: boolean, endpoint: string, intervalMs: number): LiveSource {
  const [state, setState] = useState<SimState | null>(null)
  const [status, setStatus] = useState<ConnStatus>('connecting')
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<number | null>(null)
  const [nonce, setNonce] = useState(0)
  const stateRef = useRef<SimState | null>(null)
  stateRef.current = state

  useEffect(() => {
    if (!enabled) {
      setState(null)
      setStatus('connecting')
      setError(null)
      stateRef.current = null
      return
    }

    let cancelled = false
    const controller = new AbortController()

    async function poll() {
      try {
        const res = await fetch(endpoint, { signal: controller.signal, headers: { accept: 'application/json' } })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const raw = (await res.json()) as RawPayload
        if (!raw || (!Array.isArray(raw.tags) && (typeof raw.tags !== 'object' || raw.tags === null))) {
          throw new Error('Malformed payload: expected { tags: [...] } or { tags: {...} }')
        }
        if (cancelled) return
        const mapped = mapPayload(raw, stateRef.current)
        stateRef.current = mapped
        setState(mapped)
        setStatus('connected')
        setError(null)
        setLastUpdate(Date.now())
      } catch (e) {
        if (cancelled || (e instanceof DOMException && e.name === 'AbortError')) return
        setStatus('error')
        setError(e instanceof Error ? e.message : 'Connection failed')
      }
    }

    setStatus('connecting')
    poll()
    const iv = setInterval(poll, Math.max(500, intervalMs))
    return () => {
      cancelled = true
      controller.abort()
      clearInterval(iv)
    }
  }, [enabled, endpoint, intervalMs, nonce])

  return { state, status, error, lastUpdate, retry: () => setNonce((n) => n + 1) }
}
