/**
 * geometry.ts - High-Precision Geometry & Coordinate Transformation Engine
 * 
 * Provides deterministic bidirectional conversions between SVG Canvas Percentage (0..100)
 * and physical real-world Cartesian meters, 3-node interior angle calculation,
 * GDOP / collinearity quality metrics, and schematic schema validation.
 */

export type CoordinateOrigin = 'bottom-left' | 'top-left'

export interface Point2D {
  x: number
  y: number
}

export interface TriangleGeometry {
  sideA: number // meters (between Node2 and Node3)
  sideB: number // meters (between Node1 and Node3)
  sideC: number // meters (between Node1 and Node2)
  angleNode1: number // degrees (interior angle at Node1)
  angleNode2: number // degrees (interior angle at Node2)
  angleApex: number // degrees (interior angle at Apex / Node3)
  areaM2: number // physical triangle area in m²
  collinearityScore: number // 0 (collinear degenerate) to 1.0 (equilateral)
  minSeparationM: number // minimum distance between any 2 nodes
  quality: 'excellent' | 'acceptable' | 'poor'
  warning?: string
}

export interface BuildingDimensions {
  width: number // meters (X dimension)
  height: number // meters (Y dimension)
  depth?: number // meters (Z mount height)
  unit?: string
}

/**
 * Converts SVG Canvas percentage (0..100) to physical Cartesian coordinates in meters.
 * By default uses standard Cartesian origin (Bottom-Left: X East, Y North).
 */
export function canvasPctToMeters(
  pctX: number,
  pctY: number,
  dims: BuildingDimensions,
  origin: CoordinateOrigin = 'bottom-left'
): Point2D {
  const clampedX = Math.max(0, Math.min(100, pctX))
  const clampedY = Math.max(0, Math.min(100, pctY))
  const x = Math.round(((clampedX / 100) * dims.width) * 100) / 100
  const y =
    origin === 'bottom-left'
      ? Math.round(((1 - clampedY / 100) * dims.height) * 100) / 100
      : Math.round(((clampedY / 100) * dims.height) * 100) / 100
  return { x, y }
}

/**
 * Converts physical real-world Cartesian coordinates in meters to SVG Canvas percentage (0..100).
 */
export function metersToCanvasPct(
  meterX: number,
  meterY: number,
  dims: BuildingDimensions,
  origin: CoordinateOrigin = 'bottom-left'
): Point2D {
  const pctX = Math.max(0, Math.min(100, (meterX / dims.width) * 100))
  const pctY =
    origin === 'bottom-left'
      ? Math.max(0, Math.min(100, (1 - meterY / dims.height) * 100))
      : Math.max(0, Math.min(100, (meterY / dims.height) * 100))
  return {
    x: Math.round(pctX * 10) / 10,
    y: Math.round(pctY * 10) / 10,
  }
}

/**
 * Calculates physical Euclidean distance in meters between two points.
 */
export function physicalDistance(p1: Point2D, p2: Point2D): number {
  const dx = p1.x - p2.x
  const dy = p1.y - p2.y
  return Math.sqrt(dx * dx + dy * dy)
}

/**
 * Calculates the interior angle in degrees at vertex B formed by line segments BA and BC.
 * Uses dot product with magnitude clipping to avoid floating point NaN errors.
 */
export function calculateAngle(A: Point2D, B: Point2D, C: Point2D): number {
  const v1x = A.x - B.x
  const v1y = A.y - B.y
  const v2x = C.x - B.x
  const v2y = C.y - B.y

  const dot = v1x * v2x + v1y * v2y
  const m1 = Math.sqrt(v1x * v1x + v1y * v1y)
  const m2 = Math.sqrt(v2x * v2x + v2y * v2y)

  if (m1 < 1e-6 || m2 < 1e-6) return 0.0

  const cosTheta = Math.max(-1.0, Math.min(1.0, dot / (m1 * m2)))
  const angleRad = Math.acos(cosTheta)
  return Math.round((angleRad * (180.0 / Math.PI)) * 10) / 10
}

/**
 * Evaluates the full geometric quality, interior angles, area, and GDOP suitability
 * of 3 triangulation anchor nodes.
 */
export function evaluateTriangulationGeometry(
  n1Pct: Point2D,
  n2Pct: Point2D,
  apexPct: Point2D,
  dims: BuildingDimensions,
  origin: CoordinateOrigin = 'bottom-left'
): TriangleGeometry {
  const p1 = canvasPctToMeters(n1Pct.x, n1Pct.y, dims, origin)
  const p2 = canvasPctToMeters(n2Pct.x, n2Pct.y, dims, origin)
  const pApex = canvasPctToMeters(apexPct.x, apexPct.y, dims, origin)

  const a = physicalDistance(p2, pApex) // side opposite n1
  const b = physicalDistance(p1, pApex) // side opposite n2
  const c = physicalDistance(p1, p2) // side opposite apex (base)

  const angle1 = calculateAngle(p2, p1, pApex)
  const angle2 = calculateAngle(p1, p2, pApex)
  const angleApex = calculateAngle(p1, pApex, p2)

  // Heron's formula for physical triangle area
  const s = (a + b + c) / 2.0
  const areaSq = Math.max(0, s * (s - a) * (s - b) * (s - c))
  const areaM2 = Math.round(Math.sqrt(areaSq) * 100) / 100

  // Equilateral conditioning ratio Q = 4 * sqrt(3) * Area / (a² + b² + c²)
  // Q = 1.0 for equilateral triangle, Q = 0.0 for collinear degenerate triangle
  const denom = a * a + b * b + c * c
  const collinearityScore = denom > 1e-6 ? Math.round(((4.0 * Math.sqrt(3.0) * areaM2) / denom) * 100) / 100 : 0.0

  const minSeparationM = Math.round(Math.min(a, b, c) * 100) / 100

  let quality: 'excellent' | 'acceptable' | 'poor' = 'excellent'
  let warning: string | undefined

  if (minSeparationM < 0.5) {
    quality = 'poor'
    warning = `Nodes are too close (${minSeparationM}m < 0.5m). High positioning dilution.`
  } else if (areaM2 < 0.5 || collinearityScore < 0.35 || angleApex < 20 || angleApex > 140) {
    quality = 'poor'
    warning = `Near-collinear layout (Collinearity: ${collinearityScore}). Poor GDOP geometry.`
  } else if (collinearityScore < 0.65 || angleApex < 35 || angleApex > 115) {
    quality = 'acceptable'
    warning = `Sub-optimal spread (Collinearity: ${collinearityScore}). Acceptable for localized coverage.`
  }

  return {
    sideA: Math.round(a * 100) / 100,
    sideB: Math.round(b * 100) / 100,
    sideC: Math.round(c * 100) / 100,
    angleNode1: angle1,
    angleNode2: angle2,
    angleApex,
    areaM2,
    collinearityScore,
    minSeparationM,
    quality,
    warning,
  }
}

/**
 * Validates schematic import payload at runtime to prevent malformed or NaN corruptions.
 */
export function validateSchematicPayload(data: any): { valid: boolean; errors: string[] } {
  const errors: string[] = []

  if (!data || typeof data !== 'object') {
    return { valid: false, errors: ['Schematic payload must be a valid JSON object.'] }
  }

  if (data.dimensions) {
    if (typeof data.dimensions.width !== 'number' || data.dimensions.width <= 0) {
      errors.push('Building dimensions width must be a positive number.')
    }
    if (typeof data.dimensions.height !== 'number' || data.dimensions.height <= 0) {
      errors.push('Building dimensions height must be a positive number.')
    }
  }

  if (data.anchors) {
    if (!Array.isArray(data.anchors)) {
      errors.push('Anchors must be an array.')
    } else {
      data.anchors.forEach((a: any, idx: number) => {
        if (!a.id || typeof a.id !== 'string') {
          errors.push(`Anchor #${idx + 1} is missing a valid 'id' string.`)
        }
        if (typeof a.x !== 'number' || isNaN(a.x) || a.x < 0 || a.x > 100) {
          errors.push(`Anchor #${idx + 1} (${a.id ?? 'unknown'}) has invalid x coordinate: ${a.x}`)
        }
        if (typeof a.y !== 'number' || isNaN(a.y) || a.y < 0 || a.y > 100) {
          errors.push(`Anchor #${idx + 1} (${a.id ?? 'unknown'}) has invalid y coordinate: ${a.y}`)
        }
      })
    }
  }

  if (data.rooms) {
    if (!Array.isArray(data.rooms)) {
      errors.push('Rooms must be an array.')
    } else {
      data.rooms.forEach((r: any, idx: number) => {
        if (!r.id || typeof r.id !== 'string') {
          errors.push(`Room #${idx + 1} is missing a valid 'id' string.`)
        }
        if (typeof r.w !== 'number' || r.w <= 0 || typeof r.h !== 'number' || r.h <= 0) {
          errors.push(`Room #${idx + 1} (${r.id ?? 'unknown'}) has invalid dimensions: ${r.w}x${r.h}`)
        }
      })
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  }
}

export interface FacilityReadiness {
  hasRooms: boolean
  hasAnchors: boolean
  layoutValid: boolean
  positioningReady: boolean
  status: 'no_rooms' | 'no_anchors' | 'invalid_geometry' | 'ready'
  issues: string[]
  roomCount: number
  anchorCount: number
}

/**
 * Rigorous evaluation of facility layout completeness and mathematical positioning readiness.
 * Moves beyond simple anchor counts to verify physical solvability.
 */
export function evaluateFacilityReadiness(
  rooms: { id: string; name?: string; x: number; y: number; w: number; h: number }[],
  anchors: { id: string; x: number; y: number; roomId?: string }[],
  dims: { width: number; height: number },
  origin: CoordinateOrigin = 'bottom-left'
): FacilityReadiness {
  const issues: string[] = []
  const hasRooms = Array.isArray(rooms) && rooms.length > 0
  const hasAnchors = Array.isArray(anchors) && anchors.length > 0

  if (!hasRooms) {
    return {
      hasRooms: false,
      hasAnchors,
      layoutValid: false,
      positioningReady: false,
      status: 'no_rooms',
      issues: ['No rooms configured in facility.'],
      roomCount: 0,
      anchorCount: anchors?.length ?? 0,
    }
  }

  if (!hasAnchors) {
    return {
      hasRooms: true,
      hasAnchors: false,
      layoutValid: false,
      positioningReady: false,
      status: 'no_anchors',
      issues: ['Rooms exist but no BLE anchor nodes have been placed.'],
      roomCount: rooms.length,
      anchorCount: 0,
    }
  }

  // Check coordinate bounds and finite numbers
  for (const a of anchors) {
    if (isNaN(a.x) || isNaN(a.y) || a.x < 0 || a.x > 100 || a.y < 0 || a.y > 100) {
      issues.push(`Anchor ${a.id} has invalid coordinates (${a.x}, ${a.y}).`)
    }
  }

  // Minimum anchor threshold for 2D trilateration
  if (anchors.length < 3) {
    issues.push(`At least 3 non-collinear anchors are required for 2D positioning (currently ${anchors.length}).`)
  }

  // Convert anchors to physical meters for geometric conditioning check
  const physicalAnchors = anchors.map((a) => ({
    id: a.id,
    p: canvasPctToMeters(a.x, a.y, dims, origin),
  }))

  // Pairwise separation check
  for (let i = 0; i < physicalAnchors.length; i++) {
    for (let j = i + 1; j < physicalAnchors.length; j++) {
      const sep = physicalDistance(physicalAnchors[i].p, physicalAnchors[j].p)
      if (sep < 0.5) {
        issues.push(
          `Anchors ${physicalAnchors[i].id} and ${physicalAnchors[j].id} are separated by only ${sep.toFixed(2)}m (< 0.5m minimum).`
        )
      }
    }
  }

  // Collinearity check if exactly 3 anchors
  if (physicalAnchors.length === 3) {
    const [p1, p2, p3] = physicalAnchors.map((pa) => pa.p)
    const a = physicalDistance(p2, p3)
    const b = physicalDistance(p1, p3)
    const c = physicalDistance(p1, p2)
    const s = (a + b + c) / 2
    const areaSq = s * (s - a) * (s - b) * (s - c)
    const area = areaSq > 0 ? Math.sqrt(areaSq) : 0
    if (area < 0.1) {
      issues.push('Anchors are collinear (area < 0.1 m²); multilateration cannot resolve unique (x, y) coordinates.')
    }
  }

  const layoutValid = issues.length === 0
  const positioningReady = layoutValid && anchors.length >= 3

  return {
    hasRooms: true,
    hasAnchors: true,
    layoutValid,
    positioningReady,
    status: layoutValid ? 'ready' : 'invalid_geometry',
    issues,
    roomCount: rooms.length,
    anchorCount: anchors.length,
  }
}
