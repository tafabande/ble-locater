import { describe, expect, it } from 'vitest'
import {
  pointInRect,
  segIntersectsRect,
  isSolid,
  readingFor,
  uncertaintyFor,
  statusFromLastSeen,
  buildPipeline,
  ANCHORS,
  DEFAULT_MAP,
  type MapItem,
  type Anchor,
} from '../lib/simulation'

describe('Simulation Logic & Geometry Helpers', () => {
  it('pointInRect correctly identifies point containment', () => {
    const rect = { x: 10, y: 10, w: 20, h: 20 }
    expect(pointInRect(15, 15, rect)).toBe(true)
    expect(pointInRect(10, 10, rect)).toBe(true)
    expect(pointInRect(30, 30, rect)).toBe(true)
    expect(pointInRect(5, 15, rect)).toBe(false)
    expect(pointInRect(35, 15, rect)).toBe(false)
  })

  it('segIntersectsRect detects segment-rectangle intersections', () => {
    const rect = { x: 10, y: 10, w: 20, h: 20 }
    // Segment passing straight through the box
    expect(segIntersectsRect(0, 20, 40, 20, rect)).toBe(true)
    // Segment completely outside
    expect(segIntersectsRect(0, 0, 5, 5, rect)).toBe(false)
  })

  it('isSolid returns true for wall and furniture, false for door', () => {
    const wall: MapItem = { id: 'w1', kind: 'wall', label: 'W', x: 0, y: 0, w: 1, h: 1, attenuation: 8 }
    const furn: MapItem = { id: 'f1', kind: 'furniture', label: 'F', x: 0, y: 0, w: 1, h: 1, attenuation: 4 }
    const door: MapItem = { id: 'd1', kind: 'door', label: 'D', x: 0, y: 0, w: 1, h: 1, attenuation: 0 }

    expect(isSolid(wall)).toBe(true)
    expect(isSolid(furn)).toBe(true)
    expect(isSolid(door)).toBe(false)
  })

  it('readingFor calculates distance and path loss RSSI', () => {
    const anchor: Anchor = ANCHORS[0]
    const tag = { x: 20, y: 20 }
    const reading = readingFor(anchor, tag, DEFAULT_MAP)

    expect(reading.anchorId).toBe(anchor.id)
    expect(reading.distance).toBeGreaterThan(0)
    expect(reading.rssi).toBeLessThan(0)
  })

  it('uncertaintyFor provides realistic Kalman uncertainty bounds', () => {
    const strongReadings = [
      { anchorId: 'N1', rssi: -60, distance: 2, used: true },
      { anchorId: 'N2', rssi: -65, distance: 3, used: true },
      { anchorId: 'N3', rssi: -70, distance: 4, used: true },
      { anchorId: 'N4', rssi: -72, distance: 5, used: true },
    ]
    const unc = uncertaintyFor(strongReadings)
    expect(unc).toBeGreaterThan(0)
    expect(unc).toBeLessThan(2.0)
  })

  it('statusFromLastSeen maps ms deltas to tag statuses', () => {
    expect(statusFromLastSeen(500)).toBe('online')
    expect(statusFromLastSeen(3900)).toBe('online')
    expect(statusFromLastSeen(5000)).toBe('stale')
    expect(statusFromLastSeen(11900)).toBe('stale')
    expect(statusFromLastSeen(15000)).toBe('lost')
  })

  it('buildPipeline aggregates node and service status', () => {
    const pipeline = buildPipeline([], [], 0)
    expect(pipeline).toBeInstanceOf(Array)
    expect(pipeline.length).toBeGreaterThan(0)
    const bleStage = pipeline.find((p) => p.id === 'ble')
    expect(bleStage).toBeDefined()
  })
})
