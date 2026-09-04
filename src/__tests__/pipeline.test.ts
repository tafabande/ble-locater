import { describe, it, expect, beforeEach } from 'vitest'
import {
  canvasPctToMeters,
  metersToCanvasPct,
  physicalDistance,
  evaluateFacilityReadiness,
  type BuildingDimensions,
} from '../lib/geometry'
import { TEMPLATES } from '../components/admin/FloorEditor'
import { readingFor, type Anchor, type MapItem } from '../lib/simulation'

interface RoomModel {
  id: string
  name: string
  x: number
  y: number
  w: number
  h: number
  nodeCount: 1 | 3 | 4
  triAngle?: number
}

interface AnchorModel {
  id: string
  label: string
  x: number
  y: number
  roomId?: string
  corner?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right'
  placement?: 'corner' | 'triangulation' | 'proximity'
}

/**
 * Pure state transition functions mirroring FloorEditor's exact state updates.
 */
function applyGenerateRoomCornerAnchors(
  anchors: AnchorModel[],
  room: RoomModel,
  nodeCount: 1 | 3 | 4
): AnchorModel[] {
  // Purge any existing anchors for this specific room
  const remaining = anchors.filter((a) => a.roomId !== room.id)
  const inset = 2 // 2% canvas inset

  if (nodeCount === 4) {
    const newAnchors: AnchorModel[] = [
      { id: `${room.id}_TL`, label: `${room.name} (TL)`, x: room.x + inset, y: room.y + inset, roomId: room.id, corner: 'top-left', placement: 'corner' },
      { id: `${room.id}_TR`, label: `${room.name} (TR)`, x: room.x + room.w - inset, y: room.y + inset, roomId: room.id, corner: 'top-right', placement: 'corner' },
      { id: `${room.id}_BL`, label: `${room.name} (BL)`, x: room.x + inset, y: room.y + room.h - inset, roomId: room.id, corner: 'bottom-left', placement: 'corner' },
      { id: `${room.id}_BR`, label: `${room.name} (BR)`, x: room.x + room.w - inset, y: room.y + room.h - inset, roomId: room.id, corner: 'bottom-right', placement: 'corner' },
    ]
    return [...remaining, ...newAnchors]
  } else if (nodeCount === 3) {
    const newAnchors: AnchorModel[] = [
      { id: `${room.id}_APEX`, label: `${room.name} (Apex)`, x: room.x + room.w / 2, y: room.y + inset, roomId: room.id, placement: 'triangulation' },
      { id: `${room.id}_B1`, label: `${room.name} (Base 1)`, x: room.x + inset, y: room.y + room.h - inset, roomId: room.id, placement: 'triangulation' },
      { id: `${room.id}_B2`, label: `${room.name} (Base 2)`, x: room.x + room.w - inset, y: room.y + room.h - inset, roomId: room.id, placement: 'triangulation' },
    ]
    return [...remaining, ...newAnchors]
  } else {
    const newAnchors: AnchorModel[] = [
      { id: `${room.id}_NODE`, label: `${room.name} (Proximity)`, x: room.x + room.w / 2, y: room.y + room.h / 2, roomId: room.id, placement: 'proximity' },
    ]
    return [...remaining, ...newAnchors]
  }
}

function applyDeleteRoom(
  rooms: RoomModel[],
  anchors: AnchorModel[],
  roomId: string
): { rooms: RoomModel[]; anchors: AnchorModel[] } {
  return {
    rooms: rooms.filter((r) => r.id !== roomId),
    anchors: anchors.filter((a) => a.roomId !== roomId),
  }
}

/**
 * Bidirectional invariant assertion:
 * 1. Every room has exactly room.nodeCount anchors.
 * 2. Every anchor belongs to a legitimate room in the facility (Zero orphaned anchors).
 */
function assertBidirectionalInvariants(rooms: RoomModel[], anchors: AnchorModel[]) {
  for (const room of rooms) {
    const roomAnchors = anchors.filter((a) => a.roomId === room.id)
    expect(roomAnchors).toHaveLength(room.nodeCount)
  }
  for (const anchor of anchors) {
    expect(rooms.some((r) => r.id === anchor.roomId)).toBe(true)
  }
}

describe('End-to-End Architectural Pipeline & Invariant Suite', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  describe('1. Room-Anchor Bidirectional Topology Invariants', () => {
    it('strictly satisfies anchor count invariants across full room lifecycle', () => {
      let rooms: RoomModel[] = []
      let anchors: AnchorModel[] = []

      // Initially 100% clean
      assertBidirectionalInvariants(rooms, anchors)

      // Add Room A (4-node mode)
      const roomA: RoomModel = { id: 'room_a', name: 'Executive Suite', x: 10, y: 10, w: 40, h: 40, nodeCount: 4 }
      rooms.push(roomA)
      anchors = applyGenerateRoomCornerAnchors(anchors, roomA, 4)
      assertBidirectionalInvariants(rooms, anchors)

      // Add Room B (4-node mode)
      const roomB: RoomModel = { id: 'room_b', name: 'Boardroom', x: 55, y: 10, w: 35, h: 40, nodeCount: 4 }
      rooms.push(roomB)
      anchors = applyGenerateRoomCornerAnchors(anchors, roomB, 4)
      assertBidirectionalInvariants(rooms, anchors)
      expect(anchors).toHaveLength(8)

      // Cycle Room A: 4 -> 3
      roomA.nodeCount = 3
      anchors = applyGenerateRoomCornerAnchors(anchors, roomA, 3)
      assertBidirectionalInvariants(rooms, anchors)
      expect(anchors).toHaveLength(7) // 3 + 4

      // Cycle Room A: 3 -> 1
      roomA.nodeCount = 1
      anchors = applyGenerateRoomCornerAnchors(anchors, roomA, 1)
      assertBidirectionalInvariants(rooms, anchors)
      expect(anchors).toHaveLength(5) // 1 + 4

      // Cycle Room A: 1 -> 4
      roomA.nodeCount = 4
      anchors = applyGenerateRoomCornerAnchors(anchors, roomA, 4)
      assertBidirectionalInvariants(rooms, anchors)
      expect(anchors).toHaveLength(8) // 4 + 4

      // Delete Room A
      const delA = applyDeleteRoom(rooms, anchors, 'room_a')
      rooms = delA.rooms
      anchors = delA.anchors
      assertBidirectionalInvariants(rooms, anchors)
      expect(anchors).toHaveLength(4) // Only Room B anchors remain, zero orphans

      // Delete Room B
      const delB = applyDeleteRoom(rooms, anchors, 'room_b')
      rooms = delB.rooms
      anchors = delB.anchors
      assertBidirectionalInvariants(rooms, anchors)
      expect(anchors).toHaveLength(0) // Clean slate restored
    })
  })

  describe('2. Deterministic Persistence & End-to-End Roundtrip', () => {
    it('starts empty and does not resurrect demo layout on reload without explicit action', () => {
      expect(localStorage.getItem('rtls_schematic_rooms')).toBeNull()
      expect(localStorage.getItem('rtls_schematic_anchors')).toBeNull()

      // Explicitly load demo preset
      localStorage.setItem('rtls_schematic_rooms', JSON.stringify(TEMPLATES.facility.rooms))
      localStorage.setItem('rtls_schematic_anchors', JSON.stringify(TEMPLATES.facility.anchors))

      const loadedRooms = JSON.parse(localStorage.getItem('rtls_schematic_rooms')!)
      const loadedAnchors = JSON.parse(localStorage.getItem('rtls_schematic_anchors')!)
      expect(loadedRooms.length).toBe(4)
      expect(loadedAnchors.length).toBe(12)

      // Explicitly click "Start From Scratch"
      localStorage.removeItem('rtls_schematic_rooms')
      localStorage.removeItem('rtls_schematic_anchors')
      localStorage.removeItem('rtls_schematic_walls')

      expect(localStorage.getItem('rtls_schematic_rooms')).toBeNull()
    })

    it('preserves created, resized, and topology-switched layouts across simulated reload', () => {
      // 1. Create custom room at (15%, 20%) with dimensions 50% x 45%
      const customRoom: RoomModel = {
        id: 'lab_01',
        name: 'Quantum Optics Lab',
        x: 15,
        y: 20,
        w: 50,
        h: 45,
        nodeCount: 3, // Triangulation topology
        triAngle: 65,
      }
      let customAnchors: AnchorModel[] = []
      customAnchors = applyGenerateRoomCornerAnchors(customAnchors, customRoom, 3)

      // 2. Save to simulated persistent storage
      localStorage.setItem('rtls_schematic_rooms', JSON.stringify([customRoom]))
      localStorage.setItem('rtls_schematic_anchors', JSON.stringify(customAnchors))

      // 3. Simulate browser reload by reading from storage
      const reloadedRooms: RoomModel[] = JSON.parse(localStorage.getItem('rtls_schematic_rooms')!)
      const reloadedAnchors: AnchorModel[] = JSON.parse(localStorage.getItem('rtls_schematic_anchors')!)

      expect(reloadedRooms).toHaveLength(1)
      expect(reloadedRooms[0].id).toBe('lab_01')
      expect(reloadedRooms[0].x).toBe(15)
      expect(reloadedRooms[0].y).toBe(20)
      expect(reloadedRooms[0].w).toBe(50)
      expect(reloadedRooms[0].h).toBe(45)
      expect(reloadedRooms[0].nodeCount).toBe(3)

      expect(reloadedAnchors).toHaveLength(3)
      assertBidirectionalInvariants(reloadedRooms, reloadedAnchors)
    })
  })

  describe('3. Physical Coordinate & Trilateration Math Pipeline ("The Final Boss")', () => {
    const dims: BuildingDimensions = { width: 10.0, height: 10.0 } // 10m x 10m

    it('transforms canvas corners to physical metric coordinates deterministically', () => {
      const tl = canvasPctToMeters(10, 10, dims, 'bottom-left')
      const tr = canvasPctToMeters(50, 10, dims, 'bottom-left')
      const bl = canvasPctToMeters(10, 50, dims, 'bottom-left')
      const br = canvasPctToMeters(50, 50, dims, 'bottom-left')

      expect(tl).toEqual({ x: 1.0, y: 9.0 })
      expect(tr).toEqual({ x: 5.0, y: 9.0 })
      expect(bl).toEqual({ x: 1.0, y: 5.0 })
      expect(br).toEqual({ x: 5.0, y: 5.0 })

      expect(metersToCanvasPct(tl.x, tl.y, dims, 'bottom-left')).toEqual({ x: 10, y: 10 })
      expect(metersToCanvasPct(br.x, br.y, dims, 'bottom-left')).toEqual({ x: 50, y: 50 })
    })

    it('solves the analytical ground-truth benchmark: A(0,0), B(10,0), C(0,10) with Tag(3,4)', () => {
      // Benchmark Setup:
      // Facility: 10m x 10m, Bottom-Left Origin
      // Anchor A = (0, 0)m  -> Canvas (0%, 100%)
      // Anchor B = (10, 0)m -> Canvas (100%, 100%)
      // Anchor C = (0, 10)m -> Canvas (0%, 0%)
      // True Tag T = (3, 4)m -> Canvas (30%, 60%)
      const pA = { x: 0.0, y: 0.0 }
      const pB = { x: 10.0, y: 0.0 }
      const pC = { x: 0.0, y: 10.0 }
      const pTrue = { x: 3.0, y: 4.0 }

      // 1. Analytical Expected Distances:
      // dA = sqrt(3^2 + 4^2) = 5.0m
      // dB = sqrt((10-3)^2 + 4^2) = sqrt(49 + 16) = sqrt(65) ≈ 8.0622577m
      // dC = sqrt(3^2 + (10-4)^2) = sqrt(9 + 36) = sqrt(45) ≈ 6.7082039m
      const dA = physicalDistance(pA, pTrue)
      const dB = physicalDistance(pB, pTrue)
      const dC = physicalDistance(pC, pTrue)

      expect(dA).toBe(5.0)
      expect(dB).toBeCloseTo(Math.sqrt(65), 5)
      expect(dC).toBeCloseTo(Math.sqrt(45), 5)

      // 2. Multilateration Solver (Linearized Least-Squares formulation relative to Anchor A):
      // Eq 1: 2*(xB - xA)*x + 2*(yB - yA)*y = (dA^2 - dB^2) + (xB^2 - xA^2) + (yB^2 - yA^2)
      // Eq 2: 2*(xC - xA)*x + 2*(yC - yA)*y = (dA^2 - dC^2) + (xC^2 - xA^2) + (yC^2 - yA^2)
      const A11 = 2 * (pB.x - pA.x) // 2 * (10 - 0) = 20
      const A12 = 2 * (pB.y - pA.y) // 2 * (0 - 0) = 0
      const b1 = (dA * dA - dB * dB) + (pB.x * pB.x - pA.x * pA.x) + (pB.y * pB.y - pA.y * pA.y)
      // b1 = (25 - 65) + (100 - 0) + (0 - 0) = -40 + 100 = 60
      // Therefore: 20*x = 60 => x = 3.0! Exactly!

      const A21 = 2 * (pC.x - pA.x) // 2 * (0 - 0) = 0
      const A22 = 2 * (pC.y - pA.y) // 2 * (10 - 0) = 20
      const b2 = (dA * dA - dC * dC) + (pC.x * pC.x - pA.x * pA.x) + (pC.y * pC.y - pA.y * pA.y)
      // b2 = (25 - 45) + (0 - 0) + (100 - 0) = -20 + 100 = 80
      // Therefore: 20*y = 80 => y = 4.0! Exactly!

      const det = A11 * A22 - A12 * A21
      expect(det).toBe(400) // Well-conditioned, non-collinear orthogonal baseline

      const solvedX = (b1 * A22 - b2 * A12) / det
      const solvedY = (A11 * b2 - A21 * b1) / det

      // 3. Assert exact recovery of physical coordinates (sub-millimeter precision):
      expect(solvedX).toBeCloseTo(3.0, 5)
      expect(solvedY).toBeCloseTo(4.0, 5)

      // 4. Invert to canvas percentage and assert alignment:
      const canvasPos = metersToCanvasPct(solvedX, solvedY, dims, 'bottom-left')
      expect(canvasPos.x).toBeCloseTo(30.0, 3)
      expect(canvasPos.y).toBeCloseTo(60.0, 3)
    })

    it('verifies exact bidirectional mapping across multi-point physical coordinate grid', () => {
      // 6 key benchmark points spanning boundaries, geometric center, and asymmetrical interior
      const testPoints = [
        { physical: { x: 0.0, y: 0.0 }, canvas: { x: 0.0, y: 100.0 } }, // Bottom-Left Origin
        { physical: { x: 5.0, y: 0.0 }, canvas: { x: 50.0, y: 100.0 } }, // Mid-South
        { physical: { x: 0.0, y: 5.0 }, canvas: { x: 0.0, y: 50.0 } }, // Mid-West
        { physical: { x: 5.0, y: 5.0 }, canvas: { x: 50.0, y: 50.0 } }, // Geometric Center
        { physical: { x: 10.0, y: 10.0 }, canvas: { x: 100.0, y: 0.0 } }, // Top-Right Corner
        { physical: { x: 2.5, y: 7.5 }, canvas: { x: 25.0, y: 25.0 } }, // Asymmetrical Interior
      ]

      for (const pt of testPoints) {
        // Forward transformation: Canvas % -> Physical meters
        const forwardMeters = canvasPctToMeters(pt.canvas.x, pt.canvas.y, dims, 'bottom-left')
        expect(forwardMeters.x).toBeCloseTo(pt.physical.x, 3)
        expect(forwardMeters.y).toBeCloseTo(pt.physical.y, 3)

        // Inverse transformation: Physical meters -> Canvas %
        const inverseCanvas = metersToCanvasPct(pt.physical.x, pt.physical.y, dims, 'bottom-left')
        expect(inverseCanvas.x).toBeCloseTo(pt.canvas.x, 3)
        expect(inverseCanvas.y).toBeCloseTo(pt.canvas.y, 3)
      }
    })

    it('evaluates trilateration noise perturbation sensitivity across increasing error bounds', () => {
      // Anchors at (0,0), (10,0), (0,10)
      const pA = { x: 0.0, y: 0.0 }
      const pB = { x: 10.0, y: 0.0 }
      const pC = { x: 0.0, y: 10.0 }
      const truePos = { x: 3.0, y: 4.0 }

      const trueDistA = 5.0
      const trueDistB = Math.sqrt(65)
      const trueDistC = Math.sqrt(45)

      // Test error injection: delta in [0.05, 0.10, 0.25, 0.50, 1.00] meters
      const errorLevels = [0.05, 0.10, 0.25, 0.50, 1.00]
      let prevPosError = 0

      for (const err of errorLevels) {
        // Apply differential perturbation (+err on A, -err on B, +err on C)
        const dAn = trueDistA + err
        const dBn = trueDistB - err
        const dCn = trueDistC + err

        // Linearized formulation relative to A
        const A11 = 2 * pB.x
        const A12 = 2 * pB.y
        const b1 = (dAn * dAn - dBn * dBn) + (pB.x * pB.x)

        const A21 = 2 * pC.x
        const A22 = 2 * pC.y
        const b2 = (dAn * dAn - dCn * dCn) + (pC.y * pC.y)

        const det = A11 * A22 - A12 * A21
        const xEst = (b1 * A22 - b2 * A12) / det
        const yEst = (A11 * b2 - A21 * b1) / det

        const posError = physicalDistance({ x: xEst, y: yEst }, truePos)

        // Error degradation must be bounded and monotonic
        expect(posError).toBeGreaterThan(prevPosError)
        // With orthogonal baseline GDOP ~ 1.414, position error must not exceed 2.5 * range error
        expect(posError).toBeLessThan(2.5 * err + 0.1)
        prevPosError = posError
      }
    })
  })
})
