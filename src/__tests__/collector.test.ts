import { describe, it, expect } from 'vitest'
import {
  generateUniformGrid,
  optimizeSurveyPath,
  computeAnchorDistances,
  calculatePathLength,
  formatCollectorExport,
  type CollectorAnchor,
  type SurveyPoint,
  type SurveySessionPlan,
} from '../lib/collectorGrid'
import { type BuildingDimensions } from '../lib/geometry'

describe('Visual Data Collector & Grid Survey Studio Suite', () => {
  const dims: BuildingDimensions = { width: 10.0, height: 10.0 } // 10m x 10m facility

  describe('1. Uniform Survey Grid Generation & Bounds Customization', () => {
    it('generates uniform survey grid respecting metric spacing and margins', () => {
      // Bounding box from (0%, 0%) to (100%, 100%) on a 10m x 10m facility
      // Margin = 1.0m, Spacing = 2.0m
      // In metric space: X from 1.0m to 9.0m in steps of 2.0m -> [1, 3, 5, 7, 9] (5 values)
      // Y from 1.0m to 9.0m in steps of 2.0m -> [1, 3, 5, 7, 9] (5 values)
      // Expected total: 5 x 5 = 25 points
      const bounds = { x: 0, y: 0, w: 100, h: 100 }
      const points = generateUniformGrid(bounds, 2.0, dims, {
        marginMeters: 1.0,
        prefix: 'CALIB',
        targetSamples: 500,
      })

      expect(points).toHaveLength(25)
      expect(points[0].id).toBe('CALIB_01')
      expect(points[0].targetSamples).toBe(500)
      expect(points[0].status).toBe('pending')

      // Verify all points fall within canvas percentage bounds
      for (const pt of points) {
        expect(pt.x).toBeGreaterThanOrEqual(10)
        expect(pt.x).toBeLessThanOrEqual(90)
        expect(pt.y).toBeGreaterThanOrEqual(10)
        expect(pt.y).toBeLessThanOrEqual(90)
      }
    })

    it('falls back safely to center point if room is smaller than margin', () => {
      // Extremely small room 2% x 2% (0.2m x 0.2m) with margin 0.5m
      const smallBounds = { x: 40, y: 40, w: 2, h: 2 }
      const points = generateUniformGrid(smallBounds, 1.0, dims, { marginMeters: 0.5 })

      expect(points).toHaveLength(1)
      expect(points[0].x).toBe(41) // Center of 40 to 42
      expect(points[0].y).toBe(41)
      expect(points[0].label).toContain('Center')
    })
  })

  describe('2. Shortest Walking Path Optimization (Nearest-Neighbor Heuristic)', () => {
    it('optimizes survey route and shortens physical walking trajectory', () => {
      // Deliberately zigzagged un-optimized survey points:
      // P1 (1m, 1m) -> P2 (9m, 9m) -> P3 (1m, 3m) -> P4 (9m, 7m)
      const points: SurveyPoint[] = [
        { id: 'P1', label: 'P1', x: 10, y: 90, targetSamples: 100, collectedSamples: 0, status: 'pending', heightMeters: 1, motion: 'stationary' },
        { id: 'P2', label: 'P2', x: 90, y: 10, targetSamples: 100, collectedSamples: 0, status: 'pending', heightMeters: 1, motion: 'stationary' },
        { id: 'P3', label: 'P3', x: 10, y: 70, targetSamples: 100, collectedSamples: 0, status: 'pending', heightMeters: 1, motion: 'stationary' },
        { id: 'P4', label: 'P4', x: 90, y: 30, targetSamples: 100, collectedSamples: 0, status: 'pending', heightMeters: 1, motion: 'stationary' },
      ]

      const unoptimizedDist = calculatePathLength(points, dims)
      const optimizedPoints = optimizeSurveyPath(points, dims)
      const optimizedDist = calculatePathLength(optimizedPoints, dims)

      // Verified: Optimized path must be shorter than zigzag order
      expect(optimizedPoints).toHaveLength(4)
      expect(optimizedDist).toBeLessThan(unoptimizedDist)
      // Set of IDs must be completely preserved (no drops or duplication)
      expect(new Set(optimizedPoints.map((p) => p.id))).toEqual(new Set(['P1', 'P2', 'P3', 'P4']))
    })
  })

  describe('3. Anchor Distance Matrix & Range Customization', () => {
    it('computes exact Euclidean distance from survey point to receiver anchors', () => {
      // Anchors at (0, 0)m and (10, 0)m
      const anchors: CollectorAnchor[] = [
        { id: 'A1', label: 'Anchor 1', x: 0, y: 100, txPower: -60, channel: 37, receptionRangeMeters: 6.0, status: 'online' },
        { id: 'A2', label: 'Anchor 2', x: 100, y: 100, txPower: -60, channel: 38, receptionRangeMeters: 8.0, status: 'online' },
      ]

      // Target survey point at (3, 4)m -> Canvas (30%, 60%)
      const targetPoint = { x: 30, y: 60 }
      const matrix = computeAnchorDistances(targetPoint, anchors, dims)

      // Distance from (3, 4) to (0, 0) = sqrt(9 + 16) = 5.0m
      // Anchor 1 has range 6.0m -> In Range!
      expect(matrix[0].anchorId).toBe('A1')
      expect(matrix[0].distanceMeters).toBe(5.0)
      expect(matrix[0].inRange).toBe(true)

      // Distance from (3, 4) to (10, 0) = sqrt(49 + 16) = sqrt(65) ≈ 8.062m
      // Anchor 2 has range 8.0m -> Out of range (8.062 > 8.0)!
      expect(matrix[1].anchorId).toBe('A2')
      expect(matrix[1].distanceMeters).toBeCloseTo(Math.sqrt(65), 2)
      expect(matrix[1].inRange).toBe(false)
    })
  })

  describe('4. Survey Plan Export Serialization', () => {
    it('formats compliant JSON matching collector.py and datasets/raw schema', () => {
      const plan: SurveySessionPlan = {
        id: 'SURVEY_EXP_01',
        name: 'Floor 1 BLE Baseline',
        targetMac: '52:06:26:03:01:DA',
        buildingDimensions: dims,
        gridSpacingMeters: 1.0,
        maxAllocatedSpace: { width: 10, height: 10 },
        surveyPoints: [
          { id: 'SP_01', label: 'Center Point', x: 50, y: 50, targetSamples: 300, collectedSamples: 300, status: 'completed', heightMeters: 1.0, motion: 'stationary' },
        ],
        anchors: [
          { id: 'A1', label: 'Anchor 1', x: 5, y: 95, txPower: -60, channel: 37, receptionRangeMeters: 8.0, status: 'online' },
        ],
        waypoints: [],
        obstacles: [
          { id: 'OBS_01', label: 'Concrete Pillar', x: 20, y: 20, w: 5, h: 5, obstacleType: 'Concrete', attenuationDb: 14.0 },
        ],
        exclusions: [],
        createdAt: '2026-09-03T18:00:00Z',
      }

      const exportedJson = formatCollectorExport(plan)
      const parsed = JSON.parse(exportedJson)

      expect(parsed.session_name).toBe('Floor 1 BLE Baseline')
      expect(parsed.target_mac).toBe('52:06:26:03:01:DA')
      expect(parsed.total_points).toBe(1)
      expect(parsed.survey_points[0].target_samples).toBe(300)
      expect(parsed.anchors[0].range_m).toBe(8.0)
      expect(parsed.obstacles[0].obstacleType).toBe('Concrete')
    })
  })
})
