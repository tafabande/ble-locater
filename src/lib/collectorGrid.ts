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
  obstacleType: 'Drywall' | 'Wood' | 'Metal' | 'Concrete' | 'Human Body' | 'Furniture'
  attenuationDb: number
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
      obstacles: plan.obstacles,
    },
    null,
    2
  )
}
