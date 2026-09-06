import { canvasPctToMeters, physicalDistance, type BuildingDimensions, type Point2D } from './geometry'

export type CollectorElementType = 'survey_point' | 'anchor' | 'waypoint' | 'obstacle' | 'exclusion'

export interface SurveyPoint {
  id: string
  label: string
  x: number // percent 0-100
  y: number // percent 0-100
  roomId?: string
  targetSamples: number
  collectedSamples: number
  status: 'pending' | 'collecting' | 'completed'
  heightMeters: number
  motion: 'stationary' | 'approaching' | 'moving_away'
  notes?: string
}

export interface CollectorAnchor {
  id: string
  label: string
  macAddress?: string // Hardware BLE / WiFi MAC (e.g. 24:6F:28:1A:4C:01)
  systemName?: string // Custom friendly system alias (e.g. ESP32-Anchor-Lobby)
  x: number // percent 0-100
  y: number // percent 0-100
  roomId?: string
  txPower: number
  channel: number
  receptionRangeMeters: number // Customizable range in meters (e.g. 1.0 to 25.0)
  port?: string
  status: 'online' | 'offline' | 'calibrating'
}

export interface WalkWaypoint {
  id: string
  label: string
  order: number
  x: number // percent 0-100
  y: number // percent 0-100
  speedMetersPerSec: number
  dwellTimeSec: number
}

export interface CollectorObstacle {
  id: string
  label: string
  x: number // percent 0-100
  y: number // percent 0-100
  w: number // percent 0-100
  h: number // percent 0-100
  obstacleType: 'Drywall' | 'Wood' | 'Metal' | 'Concrete' | 'Human Body' | 'Furniture' | 'WiFi / RF Noise' | 'Machinery'
  attenuationDb: number
  interferenceRadiusMeters?: number // Radius of active RF scattering or noise interference
  description?: string
}

export interface ExclusionZone {
  id: string
  label: string
  x: number
  y: number
  w: number
  h: number
}

export interface SurveySessionPlan {
  id: string
  name: string
  targetMac: string
  buildingDimensions: BuildingDimensions
  gridSpacingMeters: number
  maxAllocatedSpace: { width: number; height: number }
  surveyPoints: SurveyPoint[]
  anchors: CollectorAnchor[]
  waypoints: WalkWaypoint[]
  obstacles: CollectorObstacle[]
  exclusions: ExclusionZone[]
  createdAt: string
}

/**
 * Generates a uniform survey grid within a bounding box (e.g. room or facility bounds).
 * Respects maximum allocated space and metric spacing.
 */
export function generateUniformGrid(
  bounds: { x: number; y: number; w: number; h: number },
  spacingMeters: number,
  dims: BuildingDimensions,
  options?: {
    roomId?: string
    prefix?: string
    marginMeters?: number
    targetSamples?: number
  }
): SurveyPoint[] {
  const marginMeters = options?.marginMeters ?? 0.5
  const targetSamples = options?.targetSamples ?? 200
  const prefix = options?.prefix ?? 'SP'

  // Convert bounding box to metric coordinates
  const minXMetric = (bounds.x / 100) * dims.width
  const maxXMetric = ((bounds.x + bounds.w) / 100) * dims.width
  const minYMetric = (bounds.y / 100) * dims.height
  const maxYMetric = ((bounds.y + bounds.h) / 100) * dims.height

  const startX = minXMetric + marginMeters
  const endX = maxXMetric - marginMeters
  const startY = minYMetric + marginMeters
  const endY = maxYMetric - marginMeters

  if (startX > endX || startY > endY) {
    // Room too small for the specified margin, place a single center point
    const cx = bounds.x + bounds.w / 2
    const cy = bounds.y + bounds.h / 2
    return [
      {
        id: `${prefix}_01`,
        label: `${prefix} 01 (Center)`,
        x: Math.round(cx * 10) / 10,
        y: Math.round(cy * 10) / 10,
        roomId: options?.roomId,
        targetSamples,
        collectedSamples: 0,
        status: 'pending',
        heightMeters: 1.0,
        motion: 'stationary',
      },
    ]
  }

  const points: SurveyPoint[] = []
  let index = 1

  for (let ym = startY; ym <= endY + 1e-4; ym += spacingMeters) {
    for (let xm = startX; xm <= endX + 1e-4; xm += spacingMeters) {
      const xPct = Math.round((xm / dims.width) * 1000) / 10
      const yPct = Math.round((ym / dims.height) * 1000) / 10

      points.push({
        id: `${prefix}_${String(index).padStart(2, '0')}`,
        label: `${prefix} ${String(index).padStart(2, '0')}`,
        x: xPct,
        y: yPct,
        roomId: options?.roomId,
        targetSamples,
        collectedSamples: 0,
        status: 'pending',
        heightMeters: 1.0,
        motion: 'stationary',
      })
      index++
    }
  }

  return points
}

/**
 * Solves an optimized shortest walking route across survey points using a
 * 2D Nearest-Neighbor heuristic to maximize physical survey efficiency.
 */
export function optimizeSurveyPath(
  points: SurveyPoint[],
  dims: BuildingDimensions
): SurveyPoint[] {
  if (points.length <= 2) return [...points]

  const remaining = [...points]
  const ordered: SurveyPoint[] = []

  // Start from the point closest to the origin (0, 0)
  let currentIdx = 0
  let minDistToOrigin = Infinity
  for (let i = 0; i < remaining.length; i++) {
    const pt = canvasPctToMeters(remaining[i].x, remaining[i].y, dims, 'bottom-left')
    const dist = Math.hypot(pt.x, pt.y)
    if (dist < minDistToOrigin) {
      minDistToOrigin = dist
      currentIdx = i
    }
  }

  ordered.push(remaining.splice(currentIdx, 1)[0])

  // Sequentially pick nearest remaining point
  while (remaining.length > 0) {
    const last = ordered[ordered.length - 1]
    const pLast = canvasPctToMeters(last.x, last.y, dims, 'bottom-left')

    let nearestIdx = 0
    let nearestDist = Infinity

    for (let i = 0; i < remaining.length; i++) {
      const pCandidate = canvasPctToMeters(remaining[i].x, remaining[i].y, dims, 'bottom-left')
      const dist = physicalDistance(pLast, pCandidate)
      if (dist < nearestDist) {
        nearestDist = dist
        nearestIdx = i
      }
    }

    ordered.push(remaining.splice(nearestIdx, 1)[0])
  }

  return ordered
}

/**
 * Computes exact Euclidean distance in meters from a survey point to all active anchors.
 */
export function computeAnchorDistances(
  point: { x: number; y: number },
  anchors: CollectorAnchor[],
  dims: BuildingDimensions
): { anchorId: string; label: string; distanceMeters: number; inRange: boolean }[] {
  const pMeters = canvasPctToMeters(point.x, point.y, dims, 'bottom-left')

  return anchors.map((a) => {
    const aMeters = canvasPctToMeters(a.x, a.y, dims, 'bottom-left')
    const dist = Math.round(physicalDistance(pMeters, aMeters) * 1000) / 1000
    const inRange = dist <= a.receptionRangeMeters

    return {
      anchorId: a.id,
      label: a.label,
      distanceMeters: dist,
      inRange,
    }
  })
}

/**
 * Calculates total walking length in meters along a sequence of waypoints or survey points.
 */
export function calculatePathLength(
  points: { x: number; y: number }[],
  dims: BuildingDimensions
): number {
  if (points.length < 2) return 0
  let total = 0

  for (let i = 1; i < points.length; i++) {
    const p1 = canvasPctToMeters(points[i - 1].x, points[i - 1].y, dims, 'bottom-left')
    const p2 = canvasPctToMeters(points[i].x, points[i].y, dims, 'bottom-left')
    total += physicalDistance(p1, p2)
  }

  return Math.round(total * 100) / 100
}

/**
 * Formats a survey session plan into the standard JSON structure required
 * by the physical ESP32 collector script (ble-indoor-positioning/collector/collector.py)
 * and metadata matching datasets/raw/*_info.json.
 */
export function formatCollectorExport(plan: SurveySessionPlan): string {
  return JSON.stringify(
    {
      session_name: plan.name,
      created_at: plan.createdAt,
      target_mac: plan.targetMac,
      facility_dimensions: plan.buildingDimensions,
      grid_spacing_meters: plan.gridSpacingMeters,
      total_points: plan.surveyPoints.length,
      anchors: plan.anchors.map((a) => ({
        id: a.id,
        label: a.label,
        mac_address: a.macAddress || '',
        system_name: a.systemName || a.label,
        x_pct: a.x,
        y_pct: a.y,
        range_m: a.receptionRangeMeters,
        channel: a.channel,
        tx_power: a.txPower,
      })),
      survey_points: plan.surveyPoints.map((p) => ({
        id: p.id,
        label: p.label,
        x_pct: p.x,
        y_pct: p.y,
        room_id: p.roomId,
        target_samples: p.targetSamples,
        height_m: p.heightMeters,
        motion: p.motion,
      })),
      waypoints: plan.waypoints,
      obstacles: plan.obstacles.map((o) => ({
        ...o,
        interference_radius_m: o.interferenceRadiusMeters,
      })),
    },
    null,
    2
  )
}

/**
 * Checks if two line segments intersect in 2D space.
 */
function doSegmentsIntersect(
  p1: Point2D,
  p2: Point2D,
  q1: Point2D,
  q2: Point2D
): boolean {
  const ccw = (a: Point2D, b: Point2D, c: Point2D) =>
    (c.y - a.y) * (b.x - a.x) > (b.y - a.y) * (c.x - a.x)

  return (
    ccw(p1, q1, q2) !== ccw(p2, q1, q2) &&
    ccw(p1, p2, q1) !== ccw(p1, p2, q2)
  )
}

/**
 * Checks if a point lies inside a rectangle.
 */
function isPointInRect(pt: Point2D, rx: number, ry: number, rw: number, rh: number): boolean {
  return pt.x >= rx && pt.x <= rx + rw && pt.y >= ry && pt.y <= ry + rh
}

/**
 * Tests whether the radio line-of-sight ray between two points is obstructed by obstacles,
 * and calculates the total cumulative RF attenuation (dB) penalty.
 */
export function calculateObstructionLineOfSight(
  nodeA: { x: number; y: number },
  nodeB: { x: number; y: number },
  obstacles: CollectorObstacle[],
  dims: BuildingDimensions
): {
  isObstructed: boolean
  totalAttenuationDb: number
  obstructingObstacles: CollectorObstacle[]
} {
  const p1 = canvasPctToMeters(nodeA.x, nodeA.y, dims, 'bottom-left')
  const p2 = canvasPctToMeters(nodeB.x, nodeB.y, dims, 'bottom-left')

  const obstructingObstacles: CollectorObstacle[] = []
  let totalAttenuationDb = 0

  for (const obs of obstacles) {
    // Convert obstacle bounding box to meters
    const obsMin = canvasPctToMeters(obs.x, obs.y + obs.h, dims, 'bottom-left')
    const obsMax = canvasPctToMeters(obs.x + obs.w, obs.y, dims, 'bottom-left')
    const rx = Math.min(obsMin.x, obsMax.x)
    const ry = Math.min(obsMin.y, obsMax.y)
    const rw = Math.abs(obsMax.x - obsMin.x)
    const rh = Math.abs(obsMax.y - obsMin.y)

    // Check if either endpoint is inside the obstacle
    const p1Inside = isPointInRect(p1, rx, ry, rw, rh)
    const p2Inside = isPointInRect(p2, rx, ry, rw, rh)

    // Check if segment intersects any of the 4 bounding box edges
    const tl: Point2D = { x: rx, y: ry + rh }
    const tr: Point2D = { x: rx + rw, y: ry + rh }
    const bl: Point2D = { x: rx, y: ry }
    const br: Point2D = { x: rx + rw, y: ry }

    const intersects =
      p1Inside ||
      p2Inside ||
      doSegmentsIntersect(p1, p2, tl, tr) ||
      doSegmentsIntersect(p1, p2, tr, br) ||
      doSegmentsIntersect(p1, p2, br, bl) ||
      doSegmentsIntersect(p1, p2, bl, tl)

    if (intersects) {
      obstructingObstacles.push(obs)
      totalAttenuationDb += obs.attenuationDb
    }
  }

  return {
    isObstructed: obstructingObstacles.length > 0,
    totalAttenuationDb: Math.round(totalAttenuationDb * 10) / 10,
    obstructingObstacles,
  }
}

/**
 * Finds all nodes (anchors and survey points) that fall within the RF interference or scattering
 * radius of a given obstacle or barrier.
 */
export function getNodesInInterferenceRange(
  obstacle: CollectorObstacle,
  nodes: { id: string; label: string; x: number; y: number; type: CollectorElementType }[],
  dims: BuildingDimensions
): { node: (typeof nodes)[0]; distanceMeters: number }[] {
  // Center of obstacle in meters
  const obsCenterPctX = obstacle.x + obstacle.w / 2
  const obsCenterPctY = obstacle.y + obstacle.h / 2
  const obsCenterM = canvasPctToMeters(obsCenterPctX, obsCenterPctY, dims, 'bottom-left')

  // Calculate default interference radius if not specified
  const obsWidthM = (obstacle.w / 100) * dims.width
  const obsHeightM = (obstacle.h / 100) * dims.height
  const radiusMeters =
    obstacle.interferenceRadiusMeters ?? Math.max(obsWidthM, obsHeightM, 1.5) * 1.5

  const impacted: { node: (typeof nodes)[0]; distanceMeters: number }[] = []

  for (const node of nodes) {
    const nodeM = canvasPctToMeters(node.x, node.y, dims, 'bottom-left')
    const dist = physicalDistance(obsCenterM, nodeM)
    if (dist <= radiusMeters) {
      impacted.push({
        node,
        distanceMeters: Math.round(dist * 100) / 100,
      })
    }
  }

  return impacted.sort((a, b) => a.distanceMeters - b.distanceMeters)
}

/**
 * Generates a clean 4-ESP32 anchor setup with distinct MAC addresses and system names,
 * placed near the 4 corners of the room or grid.
 */
export function getFourEspAnchorPreset(
  dims: BuildingDimensions,
  marginPct = 8
): CollectorAnchor[] {
  return [
    {
      id: 'ESP32_01',
      label: 'ESP32 Node 1',
      systemName: 'ESP-01 (South-West)',
      macAddress: '24:6F:28:1A:4C:01',
      x: marginPct,
      y: 100 - marginPct,
      txPower: -60.0,
      channel: 37,
      receptionRangeMeters: Math.max(dims.width, dims.height) * 0.85,
      port: 'COM3',
      status: 'online',
    },
    {
      id: 'ESP32_02',
      label: 'ESP32 Node 2',
      systemName: 'ESP-02 (South-East)',
      macAddress: '24:6F:28:1A:4C:02',
      x: 100 - marginPct,
      y: 100 - marginPct,
      txPower: -60.0,
      channel: 38,
      receptionRangeMeters: Math.max(dims.width, dims.height) * 0.85,
      port: 'COM4',
      status: 'online',
    },
    {
      id: 'ESP32_03',
      label: 'ESP32 Node 3',
      systemName: 'ESP-03 (North-West)',
      macAddress: '24:6F:28:1A:4C:03',
      x: marginPct,
      y: marginPct,
      txPower: -60.0,
      channel: 39,
      receptionRangeMeters: Math.max(dims.width, dims.height) * 0.85,
      port: 'COM5',
      status: 'online',
    },
    {
      id: 'ESP32_04',
      label: 'ESP32 Node 4',
      systemName: 'ESP-04 (North-East)',
      macAddress: '24:6F:28:1A:4C:04',
      x: 100 - marginPct,
      y: marginPct,
      txPower: -60.0,
      channel: 37,
      receptionRangeMeters: Math.max(dims.width, dims.height) * 0.85,
      port: 'COM6',
      status: 'online',
    },
  ]
}

export interface RawDataRecord {
  id: string
  date: string // YYYY-MM-DD
  time: string // HH:MM:SS.mmm
  timestamp: number
  anchorId: string
  deviceMac: string
  rssi: number | string
  rawPayload: string
}

/**
 * Serializes raw telemetry records to an uncleaned, zero-transformation CSV data sheet.
 * Date is date, time is time, RSSI is raw RSSI.
 */
export function formatDataSheetCsv(records: RawDataRecord[]): string {
  const headers = ['date', 'time', 'timestamp', 'anchor_id', 'device_mac', 'rssi', 'raw_payload']
  const escapeCsvCell = (val: any) => {
    const s = String(val ?? '')
    if (s.includes(',') || s.includes('"') || s.includes('\n') || s.includes('\r')) {
      return `"${s.replace(/"/g, '""')}"`
    }
    return s
  }

  const rows = records.map((r) => [
    escapeCsvCell(r.date),
    escapeCsvCell(r.time),
    escapeCsvCell(r.timestamp),
    escapeCsvCell(r.anchorId),
    escapeCsvCell(r.deviceMac),
    escapeCsvCell(r.rssi),
    escapeCsvCell(r.rawPayload),
  ])

  return [headers.join(','), ...rows.map((row) => row.join(','))].join('\n')
}

/**
 * Formats verbatim plain text lines copying and passing incoming node lines untouched.
 */
export function formatPlainTextLog(lines: string[]): string {
  return lines.join('\n')
}


