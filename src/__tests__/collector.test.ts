import { describe, it, expect } from 'vitest'
import {
  generateUniformGrid,
  optimizeSurveyPath,
  computeAnchorDistances,
  calculatePathLength,
  formatCollectorExport,
  calculateObstructionLineOfSight,
  getNodesInInterferenceRange,
  getFourEspAnchorPreset,
  formatDataSheetCsv,
  formatPlainTextLog,
  type CollectorAnchor,
  type CollectorObstacle,
  type SurveyPoint,
  type SurveySessionPlan,
  type RawDataRecord,
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
          {
            id: 'A1',
            label: 'Anchor 1',
            systemName: 'ESP-01 (South-West)',
            macAddress: '24:6F:28:1A:4C:01',
            x: 5,
            y: 95,
            txPower: -60,
            channel: 37,
            receptionRangeMeters: 8.0,
            status: 'online',
          },
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
      expect(parsed.anchors[0].mac_address).toBe('24:6F:28:1A:4C:01')
      expect(parsed.anchors[0].system_name).toBe('ESP-01 (South-West)')
      expect(parsed.obstacles[0].obstacleType).toBe('Concrete')
    })
  })

  describe('5. Line-of-Sight Ray-Tracing & Obstacle Attenuation', () => {
    it('detects when an obstacle intersects line-of-sight and calculates cumulative dB penalty', () => {
      // In bottom-left coordinates:
      // Node A at bottom-left: (x: 10%, y: 90%) -> (1m, 1m)
      // Node B at bottom-right: (x: 90%, y: 90%) -> (9m, 1m)
      // Obstacle directly in the middle: x: 45%, y: 85%, w: 10%, h: 10% (from 4.5m to 5.5m horizontally, 0.5m to 1.5m vertically)
      const nodeA = { x: 10, y: 90 }
      const nodeB = { x: 90, y: 90 }
      const concretePillar: CollectorObstacle = {
        id: 'OBS_PILLAR',
        label: 'Concrete Pillar',
        x: 45,
        y: 85,
        w: 10,
        h: 10,
        obstacleType: 'Concrete',
        attenuationDb: 14.0,
      }

      const result = calculateObstructionLineOfSight(nodeA, nodeB, [concretePillar], dims)
      expect(result.isObstructed).toBe(true)
      expect(result.totalAttenuationDb).toBe(14.0)
      expect(result.obstructingObstacles).toHaveLength(1)
      expect(result.obstructingObstacles[0].id).toBe('OBS_PILLAR')
    })

    it('returns unobstructed when ray path is clear', () => {
      const nodeA = { x: 10, y: 90 }
      const nodeB = { x: 90, y: 90 }
      // Obstacle far away at top (x: 10%, y: 10%)
      const farObstacle: CollectorObstacle = {
        id: 'OBS_FAR',
        label: 'Drywall Partition',
        x: 10,
        y: 10,
        w: 10,
        h: 10,
        obstacleType: 'Drywall',
        attenuationDb: 3.5,
      }

      const result = calculateObstructionLineOfSight(nodeA, nodeB, [farObstacle], dims)
      expect(result.isObstructed).toBe(false)
      expect(result.totalAttenuationDb).toBe(0)
      expect(result.obstructingObstacles).toHaveLength(0)
    })
  })

  describe('6. Barrier Interference Range Detection', () => {
    it('identifies nodes within the active RF interference radius of an obstacle', () => {
      // Barrier centered at canvas (50%, 50%) -> metric (5m, 5m)
      // w: 10%, h: 10% -> 1m x 1m. Interference radius = 3.0m
      const noiseSource: CollectorObstacle = {
        id: 'OBS_NOISE',
        label: 'Industrial Microwave / RF Noise',
        x: 45,
        y: 45,
        w: 10,
        h: 10,
        obstacleType: 'WiFi / RF Noise',
        attenuationDb: 18.0,
        interferenceRadiusMeters: 3.0,
      }

      const nodes = [
        // Node 1 at (50%, 50%) -> metric (5m, 5m) -> dist 0m (In range)
        { id: 'N1', label: 'Center Point', x: 50, y: 50, type: 'survey_point' as const },
        // Node 2 at (65%, 50%) -> metric (6.5m, 5m) -> dist 1.5m (In range)
        { id: 'N2', label: 'Near Point', x: 65, y: 50, type: 'survey_point' as const },
        // Node 3 at (90%, 90%) -> metric (9m, 1m) -> dist ~ sqrt(16 + 16) = 5.65m (Out of range)
        { id: 'N3', label: 'Far Anchor', x: 90, y: 90, type: 'anchor' as const },
      ]

      const impacted = getNodesInInterferenceRange(noiseSource, nodes, dims)
      expect(impacted).toHaveLength(2)
      expect(impacted[0].node.id).toBe('N1')
      expect(impacted[0].distanceMeters).toBe(0)
      expect(impacted[1].node.id).toBe('N2')
      expect(impacted[1].distanceMeters).toBe(1.5)
    })
  })

  describe('7. 4-ESP32 Corner Node Placement Preset', () => {
    it('generates 4 corner anchors with assigned MACs and system names', () => {
      const anchors = getFourEspAnchorPreset(dims, 10)
      expect(anchors).toHaveLength(4)

      // Ensure distinct IDs, MAC addresses, and system names
      const ids = new Set(anchors.map((a) => a.id))
      const macs = new Set(anchors.map((a) => a.macAddress))
      const names = new Set(anchors.map((a) => a.systemName))

      expect(ids.size).toBe(4)
      expect(macs.size).toBe(4)
      expect(names.size).toBe(4)

      // Validate MAC address format
      const macRegex = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/
      for (const a of anchors) {
        expect(a.macAddress).toMatch(macRegex)
        expect(a.systemName).toBeTruthy()
        expect(a.status).toBe('online')
      }

      // Check corner coordinates (margin 10%)
      expect(anchors[0].x).toBe(10) // SW: (10, 90)
      expect(anchors[0].y).toBe(90)
      expect(anchors[1].x).toBe(90) // SE: (90, 90)
      expect(anchors[1].y).toBe(90)
      expect(anchors[2].x).toBe(10) // NW: (10, 10)
      expect(anchors[2].y).toBe(10)
      expect(anchors[3].x).toBe(90) // NE: (90, 10)
      expect(anchors[3].y).toBe(10)
    })
  })

  describe('8. Zero-Transformation Data Sheet & Verbatim Plain Text Log', () => {
    it('formats raw CSV data sheet preserving date, time, raw RSSI, and raw payload without cleaning', () => {
      const sampleRecords: RawDataRecord[] = [
        {
          id: 'rec_1',
          date: '2026-09-05',
          time: '16:45:10.123',
          timestamp: 1693800000,
          anchorId: 'ESP32_01',
          deviceMac: '52:06:26:03:01:DA',
          rssi: -64,
          rawPayload: '1693800000,ESP32_01,52:06:26:03:01:DA,-64,ESP_TAG',
        },
        {
          id: 'rec_2',
          date: '2026-09-05',
          time: '16:45:11.456',
          timestamp: 1693800001,
          anchorId: 'ESP32_02',
          deviceMac: '52:06:26:03:01:DA',
          rssi: -72,
          rawPayload: '{"type":"raw","timestamp":1693800001,"mac":"52:06:26:03:01:DA","rssi":-72}',
        },
      ]

      const csvOut = formatDataSheetCsv(sampleRecords)
      const lines = csvOut.split('\n')

      // Header row
      expect(lines[0]).toBe('date,time,timestamp,anchor_id,device_mac,rssi,raw_payload')
      expect(lines).toHaveLength(3)

      // Row 1
      expect(lines[1]).toContain('2026-09-05')
      expect(lines[1]).toContain('16:45:10.123')
      expect(lines[1]).toContain('ESP32_01')
      expect(lines[1]).toContain('52:06:26:03:01:DA')
      expect(lines[1]).toContain('-64')

      // Row 2
      expect(lines[2]).toContain('2026-09-05')
      expect(lines[2]).toContain('16:45:11.456')
      expect(lines[2]).toContain('ESP32_02')
      expect(lines[2]).toContain('-72')
      expect(lines[2]).toContain('""type"":""raw""') // escaped JSON payload in CSV
    })

    it('formats verbatim plain text stream copying and passing node lines as-is', () => {
      const rawLines = [
        'timestamp,anchor,mac,rssi,name',
        '1693800000,ESP32_01,52:06:26:03:01:DA,-64,ESP_TAG',
        '{"type":"raw","timestamp":1693800001,"mac":"52:06:26:03:01:DA","rssi":-72}',
        'DEBUG: Channel 37 scan cycle completed',
      ]

      const logText = formatPlainTextLog(rawLines)
      expect(logText).toBe(rawLines.join('\n'))
      // Verifies no line was skipped, altered, trimmed, or smoothed
      const parsedLines = logText.split('\n')
      expect(parsedLines).toHaveLength(4)
      expect(parsedLines[0]).toBe('timestamp,anchor,mac,rssi,name')
      expect(parsedLines[3]).toBe('DEBUG: Channel 37 scan cycle completed')
    })
  })
})
