import { describe, it, expect } from 'vitest'
import {
  calculateAngle,
  canvasPctToMeters,
  metersToCanvasPct,
  physicalDistance,
  evaluateTriangulationGeometry,
  validateSchematicPayload,
  evaluateFacilityReadiness,
  type BuildingDimensions,
} from '../lib/geometry'

describe('Indoor Positioning Geometry Engine', () => {
  const dims: BuildingDimensions = { width: 10.0, height: 10.0 }

  describe('1. Physical Coordinate Transformations & Inversions', () => {
    it('accurately maps SVG canvas percentage to Cartesian meters (BL origin)', () => {
      // (0%, 100%) in SVG is the Bottom-Left corner -> (0m, 0m) Cartesian
      const bl = canvasPctToMeters(0, 100, dims, 'bottom-left')
      expect(bl.x).toBe(0)
      expect(bl.y).toBe(0)

      // (100%, 0%) in SVG is the Top-Right corner -> (10m, 10m) Cartesian
      const tr = canvasPctToMeters(100, 0, dims, 'bottom-left')
      expect(tr.x).toBe(10)
      expect(tr.y).toBe(10)

      // (50%, 50%) in SVG is the center -> (5m, 5m) Cartesian
      const center = canvasPctToMeters(50, 50, dims, 'bottom-left')
      expect(center.x).toBe(5)
      expect(center.y).toBe(5)
    })

    it('performs round-trip bidirectional conversion with zero drift', () => {
      const originalM = { x: 7.25, y: 3.4 }
      const canvas = metersToCanvasPct(originalM.x, originalM.y, dims, 'bottom-left')
      const roundTripM = canvasPctToMeters(canvas.x, canvas.y, dims, 'bottom-left')

      expect(roundTripM.x).toBeCloseTo(originalM.x, 1)
      expect(roundTripM.y).toBeCloseTo(originalM.y, 1)
    })

    it('supports top-down architectural convention when requested', () => {
      // (0%, 0%) in SVG with top-left origin -> (0m, 0m)
      const tl = canvasPctToMeters(0, 0, dims, 'top-left')
      expect(tl.x).toBe(0)
      expect(tl.y).toBe(0)
    })
  })

  describe('2. calculateAngle (Interior Angles via Vector Dot Products)', () => {
    it('computes 90-degree right angle exactly', () => {
      const A = { x: 0, y: 5 }
      const B = { x: 0, y: 0 }
      const C = { x: 5, y: 0 }
      const angle = calculateAngle(A, B, C)
      expect(angle).toBe(90.0)
    })

    it('computes 60-degree equilateral triangle angle', () => {
      // Equilateral triangle with base length 2, apex height sqrt(3)
      const A = { x: 0, y: 0 }
      const B = { x: 1, y: Math.sqrt(3) }
      const C = { x: 2, y: 0 }
      const angle = calculateAngle(A, B, C)
      expect(angle).toBeCloseTo(60.0, 1)
    })

    it('computes 45-degree angle in right isosceles triangle', () => {
      const A = { x: 0, y: 5 }
      const B = { x: 5, y: 0 }
      const C = { x: 0, y: 0 }
      const angle = calculateAngle(A, B, C)
      expect(angle).toBe(45.0)
    })

    it('handles collinear 180-degree flat angle gracefully', () => {
      const A = { x: 0, y: 0 }
      const B = { x: 5, y: 0 }
      const C = { x: 10, y: 0 }
      const angle = calculateAngle(A, B, C)
      expect(angle).toBe(180.0)
    })

    it('returns 0 for overlapping identical points without NaN crash', () => {
      const A = { x: 5, y: 5 }
      const B = { x: 5, y: 5 }
      const C = { x: 5, y: 5 }
      const angle = calculateAngle(A, B, C)
      expect(angle).toBe(0.0)
    })
  })

  describe('3. physicalDistance (Physical Metric Distance)', () => {
    it('computes Euclidean distance in meters', () => {
      const p1 = { x: 2.0, y: 1.0 }
      const p2 = { x: 5.0, y: 5.0 }
      // sqrt(3² + 4²) = 5.0m
      expect(physicalDistance(p1, p2)).toBe(5.0)
    })
  })

  describe('4. evaluateTriangulationGeometry (Quality & Collinearity Conditioning)', () => {
    it('rates equilateral triangle as excellent geometry (high GDOP quality)', () => {
      // Triangle spanning center of 10m room
      const n1 = { x: 20, y: 70 }
      const n2 = { x: 80, y: 70 }
      const apex = { x: 50, y: 20 }

      const geom = evaluateTriangulationGeometry(n1, n2, apex, dims, 'bottom-left')
      expect(geom.areaM2).toBeGreaterThan(5.0)
      expect(geom.quality).toBe('excellent')
      expect(geom.collinearityScore).toBeGreaterThanOrEqual(0.65)
    })

    it('rates nearly collinear layout as poor geometry', () => {
      // 3 nodes almost in a straight horizontal line
      const n1 = { x: 10, y: 50 }
      const n2 = { x: 50, y: 50.5 }
      const apex = { x: 90, y: 51 }

      const geom = evaluateTriangulationGeometry(n1, n2, apex, dims, 'bottom-left')
      expect(geom.quality).toBe('poor')
      expect(geom.warning).toBeDefined()
      expect(geom.areaM2).toBeLessThan(1.0)
    })

    it('detects nodes violating minimum 0.5m separation distance', () => {
      // Node 1 and Node 2 placed 0.2m apart (2% on 10m room = 0.2m)
      const n1 = { x: 50, y: 50 }
      const n2 = { x: 52, y: 50 }
      const apex = { x: 51, y: 30 }

      const geom = evaluateTriangulationGeometry(n1, n2, apex, dims, 'bottom-left')
      expect(geom.minSeparationM).toBeLessThan(0.5)
      expect(geom.quality).toBe('poor')
    })
  })

  describe('5. validateSchematicPayload (Runtime Schema Integrity)', () => {
    it('passes valid schematic payloads', () => {
      const valid = {
        name: 'Test Facility',
        dimensions: { width: 12.0, height: 8.0 },
        anchors: [
          { id: 'A_01', x: 10, y: 10, txPower: -77 },
          { id: 'A_02', x: 90, y: 10, txPower: -77 },
        ],
        rooms: [{ id: 'R1', w: 40, h: 40 }],
      }
      const res = validateSchematicPayload(valid)
      expect(res.valid).toBe(true)
      expect(res.errors.length).toBe(0)
    })

    it('catches and rejects malformed coordinates and missing IDs', () => {
      const invalid = {
        name: 'Corrupted Facility',
        dimensions: { width: -5.0, height: 0 },
        anchors: [
          { id: '', x: NaN, y: 150 }, // Empty ID, NaN x, out of bounds y
        ],
        rooms: [{ id: 'R1', w: 0, h: -10 }],
      }
      const res = validateSchematicPayload(invalid)
      expect(res.valid).toBe(false)
      expect(res.errors.length).toBeGreaterThanOrEqual(3)
    })
  })

  describe('6. evaluateFacilityReadiness (System Readiness Evaluation)', () => {
    it('returns status no_rooms when rooms array is empty', () => {
      const res = evaluateFacilityReadiness([], [], dims)
      expect(res.status).toBe('no_rooms')
      expect(res.hasRooms).toBe(false)
      expect(res.positioningReady).toBe(false)
    })

    it('returns status no_anchors when rooms exist but anchors are empty', () => {
      const rooms = [{ id: 'r1', name: 'Office', x: 10, y: 10, w: 40, h: 40 }]
      const res = evaluateFacilityReadiness(rooms, [], dims)
      expect(res.status).toBe('no_anchors')
      expect(res.hasRooms).toBe(true)
      expect(res.hasAnchors).toBe(false)
      expect(res.positioningReady).toBe(false)
    })

    it('returns status invalid_geometry when fewer than 3 anchors exist', () => {
      const rooms = [{ id: 'r1', name: 'Office', x: 10, y: 10, w: 40, h: 40 }]
      const anchors = [
        { id: 'a1', x: 10, y: 10 },
        { id: 'a2', x: 50, y: 10 },
      ]
      const res = evaluateFacilityReadiness(rooms, anchors, dims)
      expect(res.status).toBe('invalid_geometry')
      expect(res.issues.some((i) => i.includes('At least 3'))).toBe(true)
      expect(res.positioningReady).toBe(false)
    })

    it('returns status invalid_geometry when anchors are collinear', () => {
      const rooms = [{ id: 'r1', name: 'Hallway', x: 10, y: 10, w: 80, h: 20 }]
      // 3 anchors in a straight horizontal line
      const anchors = [
        { id: 'a1', x: 10, y: 50 },
        { id: 'a2', x: 50, y: 50 },
        { id: 'a3', x: 90, y: 50 },
      ]
      const res = evaluateFacilityReadiness(rooms, anchors, dims)
      expect(res.status).toBe('invalid_geometry')
      expect(res.issues.some((i) => i.includes('collinear'))).toBe(true)
      expect(res.positioningReady).toBe(false)
    })

    it('returns status ready when rooms and well-spaced non-collinear anchors exist', () => {
      const rooms = [{ id: 'r1', name: 'Main Lab', x: 10, y: 10, w: 60, h: 60 }]
      const anchors = [
        { id: 'a1', x: 12, y: 12 },
        { id: 'a2', x: 68, y: 12 },
        { id: 'a3', x: 40, y: 68 },
      ]
      const res = evaluateFacilityReadiness(rooms, anchors, dims)
      expect(res.status).toBe('ready')
      expect(res.layoutValid).toBe(true)
      expect(res.positioningReady).toBe(true)
      expect(res.issues.length).toBe(0)
    })
  })
})
