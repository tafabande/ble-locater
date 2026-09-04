import { useRef, useState, useEffect, type MouseEvent as ReactMouseEvent } from 'react'
import { type MapItem, type Geofence } from '../../lib/simulation'
import {
  calculateAngle,
  canvasPctToMeters,
  metersToCanvasPct,
  type CoordinateOrigin,
  type TriangleGeometry,
} from '../../lib/geometry'
import {
  M3Grid,
  M3Upload,
  M3Download,
  M3Deploy,
  M3Pointer,
  M3CropSquare,
  M3Beacon,
  M3Wall,
  M3Door,
  M3Trash,
  M3Sparkles,
  M3Building,
  M3Business,
  M3Lightbulb,
} from '../common/MaterialIcon'

export { calculateAngle }

export type AnchorPlacement = 'corner' | 'triangulation' | 'proximity_center' | 'free'
export type AnchorCorner = 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'top-center' | 'center' | 'custom'

export interface SchematicAnchor {
  id: string
  label: string
  x: number // percent 0-100
  y: number // percent 0-100
  roomId?: string
  corner?: AnchorCorner
  placement?: AnchorPlacement
  cornerLocked?: boolean
  txPower: number
  channel: number
  host: boolean
}

export interface SchematicRoom extends Geofence {
  nodeCount?: 1 | 3 | 4
  targetTriAngle?: number
  triAngle?: number
  actualTriGeometry?: TriangleGeometry
  cornerLocked?: boolean
}

export interface SchematicData {
  name: string
  dimensions: { width: number; height: number; unit: string }
  blueprint: string | null
  blueprintOpacity: number
  anchors: SchematicAnchor[]
  rooms: SchematicRoom[]
  walls: MapItem[]
}

export const TEMPLATES: Record<string, SchematicData> = {
  facility: {
    name: '4-Room Smart Facility Complex',
    dimensions: { width: 10, height: 10, unit: 'meters' },
    blueprint: null,
    blueprintOpacity: 0.35,
    anchors: [
      // Room A (Executive Suite 1) - North-West: padded corner nodes
      { id: 'ANCHOR_01', label: 'Room A (BL)', x: 6, y: 44, roomId: 'room_a', corner: 'bottom-left', placement: 'corner', cornerLocked: true, txPower: -77.8, channel: 37, host: true },
      { id: 'ANCHOR_02', label: 'Room A (BR)', x: 44, y: 44, roomId: 'room_a', corner: 'bottom-right', placement: 'corner', cornerLocked: true, txPower: -77.8, channel: 38, host: false },
      { id: 'ANCHOR_03', label: 'Room A (TL)', x: 6, y: 6, roomId: 'room_a', corner: 'top-left', placement: 'corner', cornerLocked: true, txPower: -77.8, channel: 39, host: false },
      { id: 'ANCHOR_04', label: 'Room A (TR)', x: 44, y: 6, roomId: 'room_a', corner: 'top-right', placement: 'corner', cornerLocked: true, txPower: -77.8, channel: 37, host: false },

      // Room B (Meeting Room 2) - North-East: padded corner nodes
      { id: 'ANCHOR_05', label: 'Room B (BL)', x: 56, y: 44, roomId: 'room_b', corner: 'bottom-left', placement: 'corner', cornerLocked: true, txPower: -77.8, channel: 38, host: false },
      { id: 'ANCHOR_06', label: 'Room B (BR)', x: 94, y: 44, roomId: 'room_b', corner: 'bottom-right', placement: 'corner', cornerLocked: true, txPower: -77.8, channel: 39, host: false },
      { id: 'ANCHOR_07', label: 'Room B (TL)', x: 56, y: 6, roomId: 'room_b', corner: 'top-left', placement: 'corner', cornerLocked: true, txPower: -77.8, channel: 37, host: false },
      { id: 'ANCHOR_08', label: 'Room B (TR)', x: 94, y: 6, roomId: 'room_b', corner: 'top-right', placement: 'corner', cornerLocked: true, txPower: -77.8, channel: 38, host: false },

      // Room C (Operations Hub) - South-West: padded corner nodes
      { id: 'ANCHOR_09', label: 'Room C (BL)', x: 6, y: 94, roomId: 'room_c', corner: 'bottom-left', placement: 'corner', cornerLocked: true, txPower: -77.8, channel: 39, host: false },
      { id: 'ANCHOR_10', label: 'Room C (BR)', x: 44, y: 94, roomId: 'room_c', corner: 'bottom-right', placement: 'corner', cornerLocked: true, txPower: -77.8, channel: 37, host: false },
      { id: 'ANCHOR_11', label: 'Room C (TL)', x: 6, y: 56, roomId: 'room_c', corner: 'top-left', placement: 'corner', cornerLocked: true, txPower: -77.8, channel: 38, host: false },
      { id: 'ANCHOR_12', label: 'Room C (TR)', x: 44, y: 56, roomId: 'room_c', corner: 'top-right', placement: 'corner', cornerLocked: true, txPower: -77.8, channel: 39, host: false },
    ],
    rooms: [
      // Rooms with clear corridors and 4% outer margin + 8% central corridors
      { id: 'room_a', name: 'Room A (Executive Suite 1)', x: 4, y: 4, w: 42, h: 42, restricted: false, allow: [], nodeCount: 4, cornerLocked: true },
      { id: 'room_b', name: 'Room B (Meeting Room 2)', x: 54, y: 4, w: 42, h: 42, restricted: false, allow: [], nodeCount: 4, cornerLocked: true },
      { id: 'room_c', name: 'Room C (Operations Hub)', x: 4, y: 54, w: 42, h: 42, restricted: false, allow: [], nodeCount: 4, cornerLocked: true },
      { id: 'room_d', name: 'Room D (Main Entrance)', x: 54, y: 54, w: 42, h: 42, restricted: true, allow: ['WC:HR:00:00:00:04'], nodeCount: 4, cornerLocked: true },
    ],
    walls: [
      { id: 'w1', kind: 'wall', label: 'Central Partition (8 dB)', x: 49, y: 4, w: 2, h: 92, attenuation: 8 },
      { id: 'w2', kind: 'wall', label: 'Horizontal Divider (8 dB)', x: 4, y: 49, w: 92, h: 2, attenuation: 8 },
      { id: 'd1', kind: 'door', label: 'Zone A Door', x: 22, y: 48, w: 6, h: 4, attenuation: 0 },
      { id: 'd2', kind: 'door', label: 'Zone D Door', x: 72, y: 48, w: 6, h: 4, attenuation: 0 },
    ],
  },
  office: {
    name: 'Corporate Open-Plan Office',
    dimensions: { width: 20, height: 15, unit: 'meters' },
    blueprint: null,
    blueprintOpacity: 0.35,
    anchors: [
      { id: 'ANCHOR_01', label: 'Workspace (BL)', x: 5, y: 36, roomId: 'open_work', corner: 'bottom-left', txPower: -77.8, channel: 37, host: true },
      { id: 'ANCHOR_02', label: 'Workspace (BR)', x: 58, y: 36, roomId: 'open_work', corner: 'bottom-right', txPower: -77.8, channel: 38, host: false },
      { id: 'ANCHOR_03', label: 'Workspace (TL)', x: 5, y: 94, roomId: 'open_work', corner: 'top-left', txPower: -77.8, channel: 39, host: false },
      { id: 'ANCHOR_04', label: 'Workspace (TR)', x: 58, y: 94, roomId: 'open_work', corner: 'top-right', txPower: -77.8, channel: 37, host: false },
      { id: 'ANCHOR_05', label: 'Boardroom (BL)', x: 63, y: 46, roomId: 'boardroom', corner: 'bottom-left', txPower: -77.8, channel: 38, host: false },
      { id: 'ANCHOR_06', label: 'Boardroom (BR)', x: 95, y: 46, roomId: 'boardroom', corner: 'bottom-right', txPower: -77.8, channel: 39, host: false },
      { id: 'ANCHOR_07', label: 'Boardroom (TL)', x: 63, y: 94, roomId: 'boardroom', corner: 'top-left', txPower: -77.8, channel: 37, host: false },
      { id: 'ANCHOR_08', label: 'Boardroom (TR)', x: 95, y: 94, roomId: 'boardroom', corner: 'top-right', txPower: -77.8, channel: 37, host: false },
    ],
    rooms: [
      { id: 'open_work', name: 'Open Workspace', x: 4, y: 35, w: 55, h: 60, restricted: false, allow: [], nodeCount: 4 },
      { id: 'boardroom', name: 'Executive Boardroom', x: 62, y: 45, w: 34, h: 50, restricted: false, allow: [], nodeCount: 4 },
      { id: 'reception', name: 'Reception & Lobby', x: 4, y: 4, w: 40, h: 28, restricted: false, allow: [], nodeCount: 3 },
      { id: 'server_room', name: 'Server & IT Room', x: 62, y: 4, w: 34, h: 36, restricted: true, allow: [], nodeCount: 4 },
    ],
    walls: [
      { id: 'w1', kind: 'wall', label: 'Glass Partition', x: 60, y: 4, w: 2, h: 92, attenuation: 4 },
      { id: 'w2', kind: 'wall', label: 'Server Shielding', x: 60, y: 40, w: 36, h: 2, attenuation: 12 },
    ],
  },
}

type ToolMode = 'select' | 'room' | 'anchor' | 'wall' | 'door'

interface Props {
  mapItems: MapItem[]
  onMapItems: (items: MapItem[]) => void
}

export function FloorEditor({ mapItems, onMapItems }: Props) {
  const svgRef = useRef<SVGSVGElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const jsonInputRef = useRef<HTMLInputElement>(null)

  // Facility metadata
  const [facilityName, setFacilityName] = useState('Smart Facility Complex')
  const [buildingDims, setBuildingDims] = useState({ width: 10, height: 10, unit: 'meters' })
  const [blueprintImg, setBlueprintImg] = useState<string | null>(() => localStorage.getItem('rtls_blueprint_img'))
  const [blueprintOpacity, setBlueprintOpacity] = useState<number>(() => Number(localStorage.getItem('rtls_blueprint_opacity')) || 0.35)
  const [showBlueprint, setShowBlueprint] = useState(true)

  // Layout entities
  const [rooms, setRooms] = useState<SchematicRoom[]>(() => {
    try {
      const saved = localStorage.getItem('rtls_schematic_rooms')
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  })

  const [anchors, setAnchors] = useState<SchematicAnchor[]>(() => {
    try {
      const saved = localStorage.getItem('rtls_schematic_anchors')
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  })

  // Editor Interaction State
  const [tool, setTool] = useState<ToolMode>('select')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedType, setSelectedType] = useState<'room' | 'anchor' | 'wall' | null>(null)
  const [snapToGrid, setSnapToGrid] = useState(true)
  const [gridStepMeters, setGridStepMeters] = useState(0.5) // Snap to 0.5m
  const [cursorPos, setCursorPos] = useState<{ xPct: number; yPct: number; xM: number; yM: number } | null>(null)
  const [deployFeedback, setDeployFeedback] = useState<{ msg: string; type: 'success' | 'info' | 'error' } | null>(null)

  // Dragging & Creation state
  const [dragState, setDragState] = useState<{
    type: 'move-room' | 'move-anchor' | 'move-wall' | 'resize-room' | 'drawing'
    id?: string
    handle?: 'tl' | 'tr' | 'bl' | 'br'
    startX: number
    startY: number
    initialX: number
    initialY: number
    initialW?: number
    initialH?: number
  } | null>(null)

  // Persist layout to localStorage
  useEffect(() => {
    if (blueprintImg) localStorage.setItem('rtls_blueprint_img', blueprintImg)
    else localStorage.removeItem('rtls_blueprint_img')
    localStorage.setItem('rtls_blueprint_opacity', String(blueprintOpacity))
    localStorage.setItem('rtls_schematic_anchors', JSON.stringify(anchors))
    localStorage.setItem('rtls_schematic_rooms', JSON.stringify(rooms))
    localStorage.setItem('rtls_schematic_walls', JSON.stringify(mapItems))
  }, [blueprintImg, blueprintOpacity, anchors, rooms, mapItems])

  // Initial fetch from backend if empty locally
  useEffect(() => {
    fetch('/api/schematic')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && Array.isArray(data.rooms) && data.rooms.length > 0) {
          if (rooms.length === 0 && anchors.length === 0) {
            if (data.name) setFacilityName(data.name)
            if (data.dimensions) setBuildingDims(data.dimensions)
            if (data.anchors) setAnchors(data.anchors)
            if (data.rooms) setRooms(data.rooms)
            if (data.walls) onMapItems(data.walls)
          }
        }
      })
      .catch(() => {})
  }, [])

  // Coordinate Conversion Helpers
  const clientToSvgPct = (clientX: number, clientY: number) => {
    if (!svgRef.current) return { x: 50, y: 50 }
    const rect = svgRef.current.getBoundingClientRect()
    let x = ((clientX - rect.left) / rect.width) * 100
    let y = ((clientY - rect.top) / rect.height) * 100

    if (snapToGrid) {
      const snapPctX = (gridStepMeters / buildingDims.width) * 100
      const snapPctY = (gridStepMeters / buildingDims.height) * 100
      x = Math.round(x / snapPctX) * snapPctX
      y = Math.round(y / snapPctY) * snapPctY
    }

    x = Math.max(0, Math.min(100, Math.round(x * 10) / 10))
    y = Math.max(0, Math.min(100, Math.round(y * 10) / 10))
    return { x, y }
  }

  const handleMouseMove = (e: ReactMouseEvent) => {
    const { x, y } = clientToSvgPct(e.clientX, e.clientY)
    const xM = Math.round((x / 100) * buildingDims.width * 100) / 100
    const yM = Math.round((y / 100) * buildingDims.height * 100) / 100
    setCursorPos({ xPct: x, yPct: y, xM, yM })

    if (!dragState) return

    if (dragState.type === 'move-room' && dragState.id) {
      const dx = x - dragState.startX
      const dy = y - dragState.startY
      setRooms((prev) =>
        prev.map((r) => {
          if (r.id !== dragState.id) return r
          const newX = Math.max(0, Math.min(100 - r.w, Math.round((dragState.initialX + dx) * 10) / 10))
          const newY = Math.max(0, Math.min(100 - r.h, Math.round((dragState.initialY + dy) * 10) / 10))
          return { ...r, x: newX, y: newY }
        })
      )
    } else if (
      dragState.type === 'resize-room' &&
      dragState.id &&
      typeof dragState.initialW === 'number' &&
      typeof dragState.initialH === 'number'
    ) {
      const dx = x - dragState.startX
      const dy = y - dragState.startY
      const baseW = dragState.initialW
      const baseH = dragState.initialH
      const baseX = dragState.initialX
      const baseY = dragState.initialY
      const handle = dragState.handle

      setRooms((prev) =>
        prev.map((r) => {
          if (r.id !== dragState.id) return r
          let rx = baseX
          let ry = baseY
          let rw = baseW
          let rh = baseH

          if (handle === 'br') {
            rw = Math.max(5, Math.min(100 - rx, rw + dx))
            rh = Math.max(5, Math.min(100 - ry, rh + dy))
          } else if (handle === 'bl') {
            const nextX = Math.max(0, Math.min(rx + rw - 5, rx + dx))
            rw = rw + (rx - nextX)
            rx = nextX
            rh = Math.max(5, Math.min(100 - ry, rh + dy))
          } else if (handle === 'tr') {
            rw = Math.max(5, Math.min(100 - rx, rw + dx))
            const nextY = Math.max(0, Math.min(ry + rh - 5, ry + dy))
            rh = rh + (ry - nextY)
            ry = nextY
          } else if (handle === 'tl') {
            const nextX = Math.max(0, Math.min(rx + rw - 5, rx + dx))
            const nextY = Math.max(0, Math.min(ry + rh - 5, ry + dy))
            rw = rw + (rx - nextX)
            rh = rh + (ry - nextY)
            rx = nextX
            ry = nextY
          }
          return {
            ...r,
            x: Math.round(rx * 10) / 10,
            y: Math.round(ry * 10) / 10,
            w: Math.round(rw * 10) / 10,
            h: Math.round(rh * 10) / 10,
          }
        })
      )
    } else if (dragState.type === 'move-anchor' && dragState.id) {
      const dx = x - dragState.startX
      const dy = y - dragState.startY
      const newX = Math.max(0, Math.min(100, Math.round((dragState.initialX + dx) * 10) / 10))
      const newY = Math.max(0, Math.min(100, Math.round((dragState.initialY + dy) * 10) / 10))
      setAnchors((prev) => prev.map((a) => (a.id === dragState.id ? { ...a, x: newX, y: newY, corner: 'custom' } : a)))
    } else if (dragState.type === 'move-wall' && dragState.id) {
      const dx = x - dragState.startX
      const dy = y - dragState.startY
      onMapItems(
        mapItems.map((w) => {
          if (w.id !== dragState.id) return w
          const newX = Math.max(0, Math.min(100 - w.w, Math.round((dragState.initialX + dx) * 10) / 10))
          const newY = Math.max(0, Math.min(100 - w.h, Math.round((dragState.initialY + dy) * 10) / 10))
          return { ...w, x: newX, y: newY }
        })
      )
    }
  }

  const handleMouseUp = () => {
    setDragState(null)
  }

  // Canvas Click (for adding items)
  const handleCanvasClick = (e: ReactMouseEvent) => {
    if (dragState) return
    const { x, y } = clientToSvgPct(e.clientX, e.clientY)

    if (tool === 'room') {
      const newRoomId = `room_${Date.now().toString(36)}`
      const roomNumber = rooms.length + 1
      const newRoom: SchematicRoom = {
        id: newRoomId,
        name: `Zone ${roomNumber}`,
        x: Math.min(75, x),
        y: Math.min(75, y),
        w: 25,
        h: 25,
        restricted: false,
        allow: [],
        nodeCount: 4,
      }
      setRooms((prev) => [...prev, newRoom])
      setSelectedId(newRoomId)
      setSelectedType('room')
      setTool('select')
      showFeedback(`Created ${newRoom.name}. Click "4-Corners" to plant nodes.`, 'info')
    } else if (tool === 'anchor') {
      const nextNum = anchors.length + 1
      const id = `ANCHOR_${nextNum.toString().padStart(2, '0')}`
      // Check if dropped inside any room
      const containingRoom = rooms.find((r) => x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h)
      const newAnchor: SchematicAnchor = {
        id,
        label: containingRoom ? `${containingRoom.name} Node` : `Anchor ${nextNum}`,
        x,
        y,
        roomId: containingRoom?.id,
        placement: 'free',
        txPower: -77.8,
        channel: 37,
        host: anchors.length === 0,
      }
      setAnchors((prev) => [...prev, newAnchor])
      setSelectedId(id)
      setSelectedType('anchor')
      setTool('select')
      showFeedback(`Planted ${newAnchor.id}`, 'info')
    } else if (tool === 'wall') {
      const newWall: MapItem = {
        id: `wall_${Date.now().toString(36)}`,
        kind: 'wall',
        label: `Partition (${mapItems.filter((m) => m.kind === 'wall').length + 1})`,
        x: Math.min(85, x),
        y: Math.min(95, y),
        w: 15,
        h: 2,
        attenuation: 8,
      }
      onMapItems([...mapItems, newWall])
      setSelectedId(newWall.id)
      setSelectedType('wall')
      setTool('select')
    } else if (tool === 'door') {
      const newDoor: MapItem = {
        id: `door_${Date.now().toString(36)}`,
        kind: 'door',
        label: `Access Door (${mapItems.filter((m) => m.kind === 'door').length + 1})`,
        x: Math.min(92, x),
        y: Math.min(97, y),
        w: 6,
        h: 2.5,
        attenuation: 0,
      }
      onMapItems([...mapItems, newDoor])
      setSelectedId(newDoor.id)
      setSelectedType('wall')
      setTool('select')
    } else if (tool === 'select') {
      setSelectedId(null)
      setSelectedType(null)
    }
  }

  // Smart Anchor Placement Algorithms
  const plantAnchorsForRoom = (room: SchematicRoom, count: 1 | 3 | 4) => {
    const inset = 2 // 2% inset
    const minX = Math.min(100, Math.max(0, room.x + inset))
    const maxX = Math.min(100, Math.max(0, room.x + room.w - inset))
    const minY = Math.min(100, Math.max(0, room.y + inset))
    const maxY = Math.min(100, Math.max(0, room.y + room.h - inset))
    const cx = Math.round(((minX + maxX) / 2) * 10) / 10
    const cy = Math.round(((minY + maxY) / 2) * 10) / 10

    // Purge existing anchors for this room
    const filtered = anchors.filter((a) => a.roomId !== room.id)
    const cleanId = room.id.replace(/[^a-zA-Z0-9_]/g, '_')
    const shortName = room.name.split('(')[0].trim() || 'Room'

    let newNodes: SchematicAnchor[] = []
    if (count === 4) {
      newNodes = [
        { id: `${cleanId}_TL`, label: `${shortName} (TL)`, x: minX, y: minY, roomId: room.id, corner: 'top-left', placement: 'corner', cornerLocked: true, txPower: -77.8, channel: 37, host: false },
        { id: `${cleanId}_TR`, label: `${shortName} (TR)`, x: maxX, y: minY, roomId: room.id, corner: 'top-right', placement: 'corner', cornerLocked: true, txPower: -77.8, channel: 38, host: false },
        { id: `${cleanId}_BL`, label: `${shortName} (BL)`, x: minX, y: maxY, roomId: room.id, corner: 'bottom-left', placement: 'corner', cornerLocked: true, txPower: -77.8, channel: 39, host: false },
        { id: `${cleanId}_BR`, label: `${shortName} (BR)`, x: maxX, y: maxY, roomId: room.id, corner: 'bottom-right', placement: 'corner', cornerLocked: true, txPower: -77.8, channel: 37, host: false },
      ]
    } else if (count === 3) {
      newNodes = [
        { id: `${cleanId}_APEX`, label: `${shortName} (Apex)`, x: cx, y: minY, roomId: room.id, corner: 'top-center', placement: 'triangulation', cornerLocked: true, txPower: -77.8, channel: 37, host: false },
        { id: `${cleanId}_B1`, label: `${shortName} (Base 1)`, x: minX, y: maxY, roomId: room.id, corner: 'bottom-left', placement: 'triangulation', cornerLocked: true, txPower: -77.8, channel: 38, host: false },
        { id: `${cleanId}_B2`, label: `${shortName} (Base 2)`, x: maxX, y: maxY, roomId: room.id, corner: 'bottom-right', placement: 'triangulation', cornerLocked: true, txPower: -77.8, channel: 39, host: false },
      ]
    } else {
      newNodes = [
        { id: `${cleanId}_CTR`, label: `${shortName} (Center)`, x: cx, y: cy, roomId: room.id, corner: 'center', placement: 'proximity_center', cornerLocked: true, txPower: -77.8, channel: 37, host: false },
      ]
    }

    // Ensure at least one host exists
    const all = [...filtered, ...newNodes]
    if (!all.some((a) => a.host) && all.length > 0) {
      all[0].host = true
    }

    setAnchors(all)
    setRooms((prev) => prev.map((r) => (r.id === room.id ? { ...r, nodeCount: count, cornerLocked: true } : r)))
    showFeedback(`Planted ${count} nodes in ${room.name}`, 'success')
  }

  const deleteSelected = () => {
    if (!selectedId) return
    if (selectedType === 'room') {
      setRooms((prev) => prev.filter((r) => r.id !== selectedId))
      setAnchors((prev) => prev.filter((a) => a.roomId !== selectedId))
      setSelectedId(null)
      setSelectedType(null)
      showFeedback('Room and associated anchors deleted', 'info')
    } else if (selectedType === 'anchor') {
      setAnchors((prev) => prev.filter((a) => a.id !== selectedId))
      setSelectedId(null)
      setSelectedType(null)
      showFeedback('Anchor node deleted', 'info')
    } else if (selectedType === 'wall') {
      onMapItems(mapItems.filter((w) => w.id !== selectedId))
      setSelectedId(null)
      setSelectedType(null)
      showFeedback('Wall / partition deleted', 'info')
    }
  }

  const loadTemplate = (key: 'facility' | 'office') => {
    const tmpl = TEMPLATES[key]
    if (!tmpl) return
    setFacilityName(tmpl.name)
    setBuildingDims(tmpl.dimensions)
    setRooms(tmpl.rooms)
    setAnchors(tmpl.anchors)
    onMapItems(tmpl.walls)
    setSelectedId(null)
    setSelectedType(null)
    showFeedback(`Loaded "${tmpl.name}" preset`, 'success')
  }

  const clearAll = () => {
    setRooms([])
    setAnchors([])
    onMapItems([])
    setSelectedId(null)
    setSelectedType(null)
    localStorage.removeItem('rtls_schematic_rooms')
    localStorage.removeItem('rtls_schematic_anchors')
    localStorage.removeItem('rtls_schematic_walls')
    showFeedback('Canvas cleared to blank slate', 'info')
  }

  const deployToBackend = async () => {
    const payload: SchematicData = {
      name: facilityName,
      dimensions: buildingDims,
      blueprint: blueprintImg,
      blueprintOpacity,
      anchors,
      rooms,
      walls: mapItems,
    }

    try {
      const res = await fetch('/api/schematic', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (res.ok) {
        showFeedback('Successfully deployed to Live RTLS positioning engine!', 'success')
      } else {
        showFeedback('Saved locally (Backend API returned error or unreachable)', 'info')
      }
    } catch {
      showFeedback('Saved to local storage (Offline demo mode)', 'info')
    }
  }

  const showFeedback = (msg: string, type: 'success' | 'info' | 'error' = 'info') => {
    setDeployFeedback({ msg, type })
    setTimeout(() => setDeployFeedback(null), 4000)
  }

  const handleExportJson = () => {
    const data: SchematicData = {
      name: facilityName,
      dimensions: buildingDims,
      blueprint: blueprintImg,
      blueprintOpacity,
      anchors,
      rooms,
      walls: mapItems,
    }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${facilityName.toLowerCase().replace(/\s+/g, '_')}_schematic.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleImportJson = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      try {
        const parsed = JSON.parse(ev.target?.result as string)
        if (parsed.rooms && Array.isArray(parsed.rooms)) setRooms(parsed.rooms)
        if (parsed.anchors && Array.isArray(parsed.anchors)) setAnchors(parsed.anchors)
        if (parsed.walls && Array.isArray(parsed.walls)) onMapItems(parsed.walls)
        if (parsed.name) setFacilityName(parsed.name)
        if (parsed.dimensions) setBuildingDims(parsed.dimensions)
        showFeedback('Schematic imported successfully!', 'success')
      } catch {
        showFeedback('Invalid schematic JSON file', 'error')
      }
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  const handleBlueprintUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      const dataUrl = ev.target?.result as string
      setBlueprintImg(dataUrl)
      setShowBlueprint(true)
      showFeedback('Blueprint background loaded', 'success')
    }
    reader.readAsDataURL(file)
    e.target.value = ''
  }

  // Selected item references
  const selectedRoom = selectedType === 'room' ? rooms.find((r) => r.id === selectedId) : null
  const selectedAnchor = selectedType === 'anchor' ? anchors.find((a) => a.id === selectedId) : null
  const selectedWall = selectedType === 'wall' ? mapItems.find((w) => w.id === selectedId) : null

  return (
    <div className="space-y-4">
      {/* Hidden file inputs */}
      <input type="file" ref={fileInputRef} onChange={handleBlueprintUpload} accept="image/*" className="hidden" />
      <input type="file" ref={jsonInputRef} onChange={handleImportJson} accept=".json" className="hidden" />

      {/* Main Studio Control Header */}
      <div className="rounded-2xl bg-card p-5 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h2 className="text-base font-bold tracking-tight text-foreground">Facility & Floor Plan Studio</h2>
              <span className="rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-400">
                {anchors.length} Anchors • {rooms.length} Rooms
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Draw physical boundaries, plant BLE receiver anchors, set partition attenuation, and deploy to live RTLS.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Template Presets Dropdown */}
            <div className="flex items-center gap-1 bg-muted/40 rounded-xl p-1 text-xs">
              <span className="text-muted-foreground px-2 font-medium">Presets:</span>
              <button
                onClick={() => loadTemplate('facility')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-card hover:bg-accent/10 hover:text-accent font-semibold text-foreground shadow-xs transition-colors cursor-pointer"
                title="Load 4-room reference complex with 12 calibrated anchors"
              >
                <M3Building size={14} className="text-accent" />
                <span>4-Room Complex</span>
              </button>
              <button
                onClick={() => loadTemplate('office')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-card hover:bg-accent/10 hover:text-accent font-semibold text-foreground shadow-xs transition-colors cursor-pointer"
                title="Load Corporate Office floorplan"
              >
                <M3Business size={14} className="text-accent" />
                <span>Corporate Office</span>
              </button>
              <button
                onClick={clearAll}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-card hover:bg-rose-500/10 hover:text-rose-400 font-semibold text-muted-foreground shadow-xs transition-colors cursor-pointer"
                title="Clear canvas to start from scratch"
              >
                <M3Sparkles size={14} />
                <span>Blank Slate</span>
              </button>
            </div>

            {/* Utility actions */}
            <button
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-muted/40 hover:bg-muted text-xs font-semibold text-foreground transition-colors cursor-pointer"
              title="Upload CAD or floor blueprint image underlay"
            >
              <M3Upload size={14} />
              Blueprint
            </button>
            <button
              onClick={() => jsonInputRef.current?.click()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-muted/40 hover:bg-muted text-xs font-semibold text-foreground transition-colors cursor-pointer"
            >
              <M3Upload size={14} />
              Import
            </button>
            <button
              onClick={handleExportJson}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-muted/40 hover:bg-muted text-xs font-semibold text-foreground transition-colors cursor-pointer"
            >
              <M3Download size={14} />
              Export
            </button>
            <button
              onClick={deployToBackend}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-accent hover:bg-accent/90 text-primary-foreground text-xs font-bold transition-all shadow-sm cursor-pointer"
            >
              <M3Deploy size={14} />
              Deploy to Live RTLS
            </button>
          </div>
        </div>

        {/* Feedback Alert Toast */}
        {deployFeedback && (
          <div
            className={`rounded-xl px-4 py-2.5 text-xs font-semibold shadow-xs transition-all ${
              deployFeedback.type === 'success'
                ? 'bg-emerald-500/10 text-emerald-400'
                : deployFeedback.type === 'error'
                ? 'bg-rose-500/10 text-rose-400'
                : 'bg-teal-500/10 text-teal-400'
            }`}
          >
            {deployFeedback.msg}
          </div>
        )}
      </div>

      {/* Workspace: Left Tool Ribbon + Center Canvas + Right Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-[auto_1fr_320px] gap-4">
        {/* Left Tool Ribbon */}
        <div className="flex lg:flex-col gap-1.5 p-2 rounded-2xl bg-card shadow-sm self-start">
          <button
            onClick={() => setTool('select')}
            title="Select & Move (V)"
            className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              tool === 'select'
                ? 'bg-accent text-primary-foreground shadow-xs'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
            }`}
          >
            <M3Pointer size={16} />
            <span className="hidden sm:inline">Select</span>
          </button>

          <button
            onClick={() => setTool('room')}
            title="Add Room Polygon (R)"
            className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              tool === 'room'
                ? 'bg-accent text-primary-foreground shadow-xs'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
            }`}
          >
            <M3CropSquare size={16} />
            <span className="hidden sm:inline">Add Room</span>
          </button>

          <button
            onClick={() => setTool('anchor')}
            title="Add BLE Receiver Anchor (A)"
            className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              tool === 'anchor'
                ? 'bg-accent text-primary-foreground shadow-xs'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
            }`}
          >
            <M3Beacon size={16} />
            <span className="hidden sm:inline">Add Anchor</span>
          </button>

          <button
            onClick={() => setTool('wall')}
            title="Add Attenuating Partition Wall (W)"
            className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              tool === 'wall'
                ? 'bg-accent text-primary-foreground shadow-xs'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
            }`}
          >
            <M3Wall size={16} />
            <span className="hidden sm:inline">Add Wall</span>
          </button>

          <button
            onClick={() => setTool('door')}
            title="Add Access Door (D)"
            className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              tool === 'door'
                ? 'bg-accent text-primary-foreground shadow-xs'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
            }`}
          >
            <M3Door size={16} />
            <span className="hidden sm:inline">Add Door</span>
          </button>

          <div className="h-px bg-muted/80 my-1 hidden lg:block" />

          {selectedId && (
            <button
              onClick={deleteSelected}
              title="Delete selected item"
              className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold text-rose-400 hover:bg-rose-500/10 transition-all cursor-pointer"
            >
              <M3Trash size={16} />
              <span className="hidden sm:inline">Delete</span>
            </button>
          )}
        </div>

        {/* Center Canvas Studio */}
        <div className="space-y-3">
          <div className="relative rounded-2xl bg-card overflow-hidden shadow-sm select-none">
            {/* Dimension Rulers HUD */}
            <div className="absolute top-3 left-3 z-10 flex items-center gap-2 rounded-xl bg-card/90 backdrop-blur-md px-3 py-1.5 text-[11px] font-mono text-muted-foreground shadow-xs">
              <span className="text-foreground font-semibold">Width: {buildingDims.width}m</span>
              <span>×</span>
              <span className="text-foreground font-semibold">Height: {buildingDims.height}m</span>
              {cursorPos && (
                <>
                  <span className="text-muted-foreground/30">|</span>
                  <span className="text-accent font-semibold">X: {cursorPos.xM}m</span>
                  <span className="text-accent font-semibold">Y: {cursorPos.yM}m</span>
                </>
              )}
            </div>

            {/* Grid & Origin Status Badge */}
            <div className="absolute top-3 right-3 z-10 flex items-center gap-2">
              <button
                onClick={() => setSnapToGrid(!snapToGrid)}
                className={`rounded-lg px-2.5 py-1 text-[11px] font-semibold transition-colors cursor-pointer shadow-xs ${
                  snapToGrid
                    ? 'bg-accent/15 text-accent'
                    : 'bg-card/90 backdrop-blur text-muted-foreground hover:text-foreground'
                }`}
              >
                Snap: {snapToGrid ? `${gridStepMeters}m` : 'Off'}
              </button>
              {blueprintImg && (
                <button
                  onClick={() => setShowBlueprint(!showBlueprint)}
                  className={`rounded-lg px-2.5 py-1 text-[11px] font-semibold transition-colors cursor-pointer shadow-xs ${
                    showBlueprint
                      ? 'bg-amber-500/15 text-amber-400'
                      : 'bg-card/90 backdrop-blur text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Blueprint: {showBlueprint ? 'On' : 'Off'}
                </button>
              )}
            </div>

            {/* SVG Interactive Canvas */}
            <svg
              ref={svgRef}
              viewBox="0 0 100 100"
              className="w-full aspect-square bg-[#0b0f19] cursor-crosshair"
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onClick={handleCanvasClick}
            >
              <defs>
                {/* Architectural Metric Grid Pattern (10% = 1m in 10x10m default) */}
                <pattern id="metricGridFine" width="2" height="2" patternUnits="userSpaceOnUse">
                  <path d="M 2 0 L 0 0 0 2" fill="none" stroke="rgba(255, 255, 255, 0.04)" strokeWidth="0.2" />
                </pattern>
                <pattern id="metricGridMajor" width="10" height="10" patternUnits="userSpaceOnUse">
                  <rect width="10" height="10" fill="url(#metricGridFine)" />
                  <path d="M 10 0 L 0 0 0 10" fill="none" stroke="rgba(255, 255, 255, 0.09)" strokeWidth="0.4" />
                </pattern>
              </defs>

              {/* Background Metric Grid */}
              <rect width="100" height="100" fill="url(#metricGridMajor)" />

              {/* Blueprint Image Underlay */}
              {blueprintImg && showBlueprint && (
                <image
                  href={blueprintImg}
                  x="0"
                  y="0"
                  width="100"
                  height="100"
                  preserveAspectRatio="none"
                  opacity={blueprintOpacity}
                />
              )}

              {/* Facility Boundary Border */}
              <rect
                x="0.2"
                y="0.2"
                width="99.6"
                height="99.6"
                fill="none"
                stroke="rgba(255, 255, 255, 0.2)"
                strokeWidth="0.4"
                strokeDasharray="1, 1"
              />

              {/* Layer 1: Rooms */}
              {rooms.map((room) => {
                const isSelected = selectedId === room.id
                return (
                  <g key={room.id}>
                    <rect
                      x={room.x}
                      y={room.y}
                      width={room.w}
                      height={room.h}
                      rx="1"
                      className="cursor-move transition-colors"
                      fill={
                        isSelected
                          ? 'rgba(13, 148, 136, 0.22)'
                          : room.restricted
                          ? 'rgba(239, 68, 68, 0.12)'
                          : 'rgba(13, 148, 136, 0.08)'
                      }
                      stroke={
                        isSelected
                          ? '#0d9488'
                          : room.restricted
                          ? '#ef4444'
                          : 'rgba(13, 148, 136, 0.4)'
                      }
                      strokeWidth={isSelected ? '0.8' : '0.4'}
                      onMouseDown={(e) => {
                        e.stopPropagation()
                        setSelectedId(room.id)
                        setSelectedType('room')
                        setDragState({
                          type: 'move-room',
                          id: room.id,
                          startX: clientToSvgPct(e.clientX, e.clientY).x,
                          startY: clientToSvgPct(e.clientX, e.clientY).y,
                          initialX: room.x,
                          initialY: room.y,
                        })
                      }}
                    />

                    {/* Room Label */}
                    <text
                      x={room.x + room.w / 2}
                      y={room.y + room.h / 2}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      className="fill-slate-200 text-[3.2px] font-sans font-bold pointer-events-none select-none tracking-wide"
                    >
                      {room.name}
                    </text>
                    <text
                      x={room.x + room.w / 2}
                      y={room.y + room.h / 2 + 4}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      className="fill-slate-400 text-[2.2px] font-mono pointer-events-none select-none"
                    >
                      {Math.round((room.w / 100) * buildingDims.width * 10) / 10}m ×{' '}
                      {Math.round((room.h / 100) * buildingDims.height * 10) / 10}m
                    </text>

                    {/* Resize Handles (Only on selected room) */}
                    {isSelected && (
                      <>
                        {(['tl', 'tr', 'bl', 'br'] as const).map((handle) => {
                          const hx = handle.includes('r') ? room.x + room.w : room.x
                          const hy = handle.includes('b') ? room.y + room.h : room.y
                          return (
                            <circle
                              key={handle}
                              cx={hx}
                              cy={hy}
                              r="1.4"
                              fill="#0d9488"
                              stroke="#0b0f19"
                              strokeWidth="0.4"
                              className="cursor-nwse-resize"
                              onMouseDown={(e) => {
                                e.stopPropagation()
                                setDragState({
                                  type: 'resize-room',
                                  id: room.id,
                                  handle,
                                  startX: clientToSvgPct(e.clientX, e.clientY).x,
                                  startY: clientToSvgPct(e.clientX, e.clientY).y,
                                  initialX: room.x,
                                  initialY: room.y,
                                  initialW: room.w,
                                  initialH: room.h,
                                })
                              }}
                            />
                          )
                        })}
                      </>
                    )}
                  </g>
                )
              })}

              {/* Layer 2: Walls and Obstacles */}
              {mapItems.map((wall) => {
                const isSelected = selectedId === wall.id
                const isDoor = wall.kind === 'door'
                return (
                  <g key={wall.id}>
                    <rect
                      x={wall.x}
                      y={wall.y}
                      width={wall.w}
                      height={wall.h}
                      rx={isDoor ? '0' : '0.4'}
                      fill={isDoor ? 'rgba(245, 158, 11, 0.25)' : 'rgba(148, 163, 184, 0.4)'}
                      stroke={isSelected ? '#0d9488' : isDoor ? '#f59e0b' : '#94a3b8'}
                      strokeWidth={isSelected ? '0.7' : '0.4'}
                      strokeDasharray={isDoor ? '1.5, 1' : undefined}
                      className="cursor-move"
                      onMouseDown={(e) => {
                        e.stopPropagation()
                        setSelectedId(wall.id)
                        setSelectedType('wall')
                        setDragState({
                          type: 'move-wall',
                          id: wall.id,
                          startX: clientToSvgPct(e.clientX, e.clientY).x,
                          startY: clientToSvgPct(e.clientX, e.clientY).y,
                          initialX: wall.x,
                          initialY: wall.y,
                        })
                      }}
                    />
                    {wall.attenuation > 0 && wall.w > 6 && (
                      <text
                        x={wall.x + wall.w / 2}
                        y={wall.y + wall.h / 2}
                        textAnchor="middle"
                        dominantBaseline="middle"
                        className="fill-slate-300 text-[1.8px] font-mono pointer-events-none select-none"
                      >
                        {wall.attenuation}dB
                      </text>
                    )}
                  </g>
                )
              })}

              {/* Layer 3: BLE Anchors */}
              {anchors.map((anchor) => {
                const isSelected = selectedId === anchor.id
                return (
                  <g
                    key={anchor.id}
                    className="cursor-move"
                    onMouseDown={(e) => {
                      e.stopPropagation()
                      setSelectedId(anchor.id)
                      setSelectedType('anchor')
                      setDragState({
                        type: 'move-anchor',
                        id: anchor.id,
                        startX: clientToSvgPct(e.clientX, e.clientY).x,
                        startY: clientToSvgPct(e.clientX, e.clientY).y,
                        initialX: anchor.x,
                        initialY: anchor.y,
                      })
                    }}
                  >
                    {/* Anchor Pulse Ring */}
                    <circle
                      cx={anchor.x}
                      cy={anchor.y}
                      r={isSelected ? '3.5' : '2.5'}
                      fill={anchor.host ? 'rgba(245, 158, 11, 0.18)' : 'rgba(13, 148, 136, 0.18)'}
                      stroke={anchor.host ? '#f59e0b' : '#0d9488'}
                      strokeWidth={isSelected ? '0.5' : '0.3'}
                      strokeDasharray={isSelected ? '1, 1' : undefined}
                    />

                    {/* Anchor Center Dot */}
                    <circle
                      cx={anchor.x}
                      cy={anchor.y}
                      r="1.2"
                      fill={anchor.host ? '#f59e0b' : '#0d9488'}
                      stroke="#ffffff"
                      strokeWidth="0.3"
                    />

                    {/* Anchor ID Badge */}
                    <text
                      x={anchor.x}
                      y={anchor.y - 3.2}
                      textAnchor="middle"
                      className="fill-white text-[2.2px] font-mono font-bold pointer-events-none select-none"
                    >
                      {anchor.id.replace('ANCHOR_', 'A')}
                    </text>
                  </g>
                )
              })}
            </svg>
          </div>

          {/* Bottom Canvas Footer / Summary Bar */}
          <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 rounded-2xl bg-card text-xs text-muted-foreground shadow-sm">
            <div className="flex items-center gap-3">
              <span>Facility: <strong className="text-foreground">{facilityName}</strong></span>
              <span>Dimensions: <strong className="text-foreground">{buildingDims.width}m × {buildingDims.height}m</strong></span>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-400" />
              <span>{anchors.filter((a) => a.host).length > 0 ? 'Coordinator Host Active' : 'No Host Set'}</span>
            </div>
          </div>
        </div>

        {/* Right Contextual Inspector Panel */}
        <div className="rounded-2xl bg-card p-5 shadow-sm space-y-5 self-start">
          <div>
            <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground">Properties Inspector</div>
            <h3 className="text-base font-bold text-foreground mt-0.5">
              {selectedRoom
                ? 'Room Inspector'
                : selectedAnchor
                ? 'Anchor Inspector'
                : selectedWall
                ? 'Partition Inspector'
                : 'Facility Overview'}
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              {selectedRoom
                ? 'Configure room bounds & plant nodes'
                : selectedAnchor
                ? 'BLE radio coordinates & parameters'
                : selectedWall
                ? 'Structural attenuation settings'
                : 'Facility global setup & dimensions'}
            </p>
          </div>

          {/* ROOM INSPECTOR */}
          {selectedRoom && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Room Name</label>
                <input
                  type="text"
                  value={selectedRoom.name}
                  onChange={(e) => {
                    const val = e.target.value
                    setRooms((prev) => prev.map((r) => (r.id === selectedRoom.id ? { ...r, name: val } : r)))
                  }}
                  className="w-full rounded-xl bg-muted/40 px-3 py-2 text-xs font-medium text-foreground focus:bg-card focus:ring-2 focus:ring-accent transition-all"
                />
              </div>

              {/* Dimensions in Meters */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-semibold text-muted-foreground mb-1">Width (m)</label>
                  <input
                    type="number"
                    step="0.5"
                    min="1"
                    max={buildingDims.width}
                    value={Math.round((selectedRoom.w / 100) * buildingDims.width * 10) / 10}
                    onChange={(e) => {
                      const m = Number(e.target.value)
                      const pct = Math.min(100 - selectedRoom.x, Math.max(5, (m / buildingDims.width) * 100))
                      setRooms((prev) => prev.map((r) => (r.id === selectedRoom.id ? { ...r, w: Math.round(pct * 10) / 10 } : r)))
                    }}
                    className="w-full rounded-xl bg-muted/40 px-3 py-2 text-xs font-medium text-foreground focus:bg-card focus:ring-2 focus:ring-accent transition-all"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-muted-foreground mb-1">Height (m)</label>
                  <input
                    type="number"
                    step="0.5"
                    min="1"
                    max={buildingDims.height}
                    value={Math.round((selectedRoom.h / 100) * buildingDims.height * 10) / 10}
                    onChange={(e) => {
                      const m = Number(e.target.value)
                      const pct = Math.min(100 - selectedRoom.y, Math.max(5, (m / buildingDims.height) * 100))
                      setRooms((prev) => prev.map((r) => (r.id === selectedRoom.id ? { ...r, h: Math.round(pct * 10) / 10 } : r)))
                    }}
                    className="w-full rounded-xl bg-muted/40 px-3 py-2 text-xs font-medium text-foreground focus:bg-card focus:ring-2 focus:ring-accent transition-all"
                  />
                </div>
              </div>

              {/* Security Geofence Toggle */}
              <div className="flex items-center justify-between rounded-xl bg-muted/40 p-3">
                <div>
                  <div className="text-xs font-semibold text-foreground">Restricted Zone</div>
                  <div className="text-[10px] text-muted-foreground">Alert when unassigned tags enter</div>
                </div>
                <input
                  type="checkbox"
                  checked={selectedRoom.restricted}
                  onChange={(e) => {
                    const checked = e.target.checked
                    setRooms((prev) => prev.map((r) => (r.id === selectedRoom.id ? { ...r, restricted: checked } : r)))
                  }}
                  className="rounded accent-accent cursor-pointer size-4"
                />
              </div>

              {/* Smart Anchor Auto-Planting Buttons */}
              <div className="space-y-2 pt-1">
                <label className="block text-xs font-bold text-foreground">Smart Anchor Auto-Planting</label>
                <div className="grid grid-cols-3 gap-1.5">
                  <button
                    onClick={() => plantAnchorsForRoom(selectedRoom, 4)}
                    className="px-2 py-2 rounded-xl bg-teal-500/15 hover:bg-teal-500/25 text-teal-300 text-[11px] font-semibold transition-all cursor-pointer text-center shadow-xs"
                  >
                    4 Corners
                  </button>
                  <button
                    onClick={() => plantAnchorsForRoom(selectedRoom, 3)}
                    className="px-2 py-2 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 text-[11px] font-semibold transition-all cursor-pointer text-center shadow-xs"
                  >
                    3 Nodes
                  </button>
                  <button
                    onClick={() => plantAnchorsForRoom(selectedRoom, 1)}
                    className="px-2 py-2 rounded-xl bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 text-[11px] font-semibold transition-all cursor-pointer text-center shadow-xs"
                  >
                    1 Center
                  </button>
                </div>
              </div>

              <button
                onClick={deleteSelected}
                className="w-full py-2.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 text-xs font-semibold transition-colors cursor-pointer shadow-xs"
              >
                Delete Room
              </button>
            </div>
          )}

          {/* ANCHOR INSPECTOR */}
          {selectedAnchor && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Node Identifier</label>
                <input
                  type="text"
                  value={selectedAnchor.id}
                  onChange={(e) => {
                    const val = e.target.value
                    setAnchors((prev) => prev.map((a) => (a.id === selectedAnchor.id ? { ...a, id: val } : a)))
                    setSelectedId(val)
                  }}
                  className="w-full rounded-xl bg-muted/40 px-3 py-2 text-xs font-mono font-medium text-foreground focus:bg-card focus:ring-2 focus:ring-accent transition-all"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Node Label</label>
                <input
                  type="text"
                  value={selectedAnchor.label}
                  onChange={(e) => {
                    const val = e.target.value
                    setAnchors((prev) => prev.map((a) => (a.id === selectedAnchor.id ? { ...a, label: val } : a)))
                  }}
                  className="w-full rounded-xl bg-muted/40 px-3 py-2 text-xs font-medium text-foreground focus:bg-card focus:ring-2 focus:ring-accent transition-all"
                />
              </div>

              {/* Coordinates in Meters */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-semibold text-muted-foreground mb-1">Pos X (m)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max={buildingDims.width}
                    value={Math.round((selectedAnchor.x / 100) * buildingDims.width * 10) / 10}
                    onChange={(e) => {
                      const m = Number(e.target.value)
                      const pct = Math.max(0, Math.min(100, (m / buildingDims.width) * 100))
                      setAnchors((prev) => prev.map((a) => (a.id === selectedAnchor.id ? { ...a, x: Math.round(pct * 10) / 10 } : a)))
                    }}
                    className="w-full rounded-xl bg-muted/40 px-3 py-2 text-xs font-medium text-foreground focus:bg-card focus:ring-2 focus:ring-accent transition-all"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-muted-foreground mb-1">Pos Y (m)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max={buildingDims.height}
                    value={Math.round((selectedAnchor.y / 100) * buildingDims.height * 10) / 10}
                    onChange={(e) => {
                      const m = Number(e.target.value)
                      const pct = Math.max(0, Math.min(100, (m / buildingDims.height) * 100))
                      setAnchors((prev) => prev.map((a) => (a.id === selectedAnchor.id ? { ...a, y: Math.round(pct * 10) / 10 } : a)))
                    }}
                    className="w-full rounded-xl bg-muted/40 px-3 py-2 text-xs font-medium text-foreground focus:bg-card focus:ring-2 focus:ring-accent transition-all"
                  />
                </div>
              </div>

              {/* RF Parameters */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-semibold text-muted-foreground mb-1">TX Power (dBm)</label>
                  <input
                    type="number"
                    step="0.5"
                    value={selectedAnchor.txPower}
                    onChange={(e) => {
                      const val = Number(e.target.value)
                      setAnchors((prev) => prev.map((a) => (a.id === selectedAnchor.id ? { ...a, txPower: val } : a)))
                    }}
                    className="w-full rounded-xl bg-muted/40 px-3 py-2 text-xs font-mono font-medium text-foreground focus:bg-card focus:ring-2 focus:ring-accent transition-all"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-muted-foreground mb-1">BLE Channel</label>
                  <select
                    value={selectedAnchor.channel}
                    onChange={(e) => {
                      const val = Number(e.target.value)
                      setAnchors((prev) => prev.map((a) => (a.id === selectedAnchor.id ? { ...a, channel: val } : a)))
                    }}
                    className="w-full rounded-xl bg-muted/40 px-3 py-2 text-xs font-medium text-foreground focus:bg-card focus:ring-2 focus:ring-accent transition-all"
                  >
                    <option value={37}>CH 37 (2402 MHz)</option>
                    <option value={38}>CH 38 (2426 MHz)</option>
                    <option value={39}>CH 39 (2480 MHz)</option>
                  </select>
                </div>
              </div>

              {/* Host Toggle */}
              <div className="flex items-center justify-between rounded-xl bg-muted/40 p-3">
                <div>
                  <div className="text-xs font-semibold text-foreground">Coordinator Host</div>
                  <div className="text-[10px] text-muted-foreground">Primary gateway receiver node</div>
                </div>
                <input
                  type="checkbox"
                  checked={selectedAnchor.host}
                  onChange={(e) => {
                    const isHost = e.target.checked
                    setAnchors((prev) =>
                      prev.map((a) => ({
                        ...a,
                        host: a.id === selectedAnchor.id ? isHost : isHost ? false : a.host,
                      }))
                    )
                  }}
                  className="rounded accent-accent cursor-pointer size-4"
                />
              </div>

              <button
                onClick={deleteSelected}
                className="w-full py-2.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 text-xs font-semibold transition-colors cursor-pointer shadow-xs"
              >
                Delete Anchor
              </button>
            </div>
          )}

          {/* PARTITION WALL / DOOR INSPECTOR */}
          {selectedWall && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Partition Label</label>
                <input
                  type="text"
                  value={selectedWall.label || ''}
                  onChange={(e) => {
                    const val = e.target.value
                    onMapItems(mapItems.map((w) => (w.id === selectedWall.id ? { ...w, label: val } : w)))
                  }}
                  className="w-full rounded-xl bg-muted/40 px-3 py-2 text-xs font-medium text-foreground focus:bg-card focus:ring-2 focus:ring-accent transition-all"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Partition Type</label>
                <select
                  value={selectedWall.kind}
                  onChange={(e) => {
                    const kind = e.target.value as 'wall' | 'door'
                    onMapItems(
                      mapItems.map((w) =>
                        w.id === selectedWall.id ? { ...w, kind, attenuation: kind === 'door' ? 0 : 8 } : w
                      )
                    )
                  }}
                  className="w-full rounded-xl bg-muted/40 px-3 py-2 text-xs font-medium text-foreground focus:bg-card focus:ring-2 focus:ring-accent transition-all"
                >
                  <option value="wall">Structural Partition Wall</option>
                  <option value="door">Passage Doorway</option>
                </select>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1.5 font-semibold">
                  <span>RF Attenuation</span>
                  <span className="text-accent font-mono">{selectedWall.attenuation} dB</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="24"
                  step="1"
                  value={selectedWall.attenuation}
                  onChange={(e) => {
                    const att = Number(e.target.value)
                    onMapItems(mapItems.map((w) => (w.id === selectedWall.id ? { ...w, attenuation: att } : w)))
                  }}
                  className="w-full accent-accent cursor-pointer"
                />
              </div>

              <button
                onClick={deleteSelected}
                className="w-full py-2.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 text-xs font-semibold transition-colors cursor-pointer shadow-xs"
              >
                Delete Partition
              </button>
            </div>
          )}

          {/* FACILITY GLOBAL OVERVIEW (When nothing selected) */}
          {!selectedRoom && !selectedAnchor && !selectedWall && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Facility Complex Name</label>
                <input
                  type="text"
                  value={facilityName}
                  onChange={(e) => setFacilityName(e.target.value)}
                  className="w-full rounded-xl bg-muted/40 px-3 py-2 text-xs font-medium text-foreground focus:bg-card focus:ring-2 focus:ring-accent transition-all"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-semibold text-muted-foreground mb-1">Building Width (m)</label>
                  <input
                    type="number"
                    min="5"
                    max="100"
                    value={buildingDims.width}
                    onChange={(e) => setBuildingDims({ ...buildingDims, width: Math.max(5, Number(e.target.value)) })}
                    className="w-full rounded-xl bg-muted/40 px-3 py-2 text-xs font-medium text-foreground focus:bg-card focus:ring-2 focus:ring-accent transition-all"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-muted-foreground mb-1">Building Height (m)</label>
                  <input
                    type="number"
                    min="5"
                    max="100"
                    value={buildingDims.height}
                    onChange={(e) => setBuildingDims({ ...buildingDims, height: Math.max(5, Number(e.target.value)) })}
                    className="w-full rounded-xl bg-muted/40 px-3 py-2 text-xs font-medium text-foreground focus:bg-card focus:ring-2 focus:ring-accent transition-all"
                  />
                </div>
              </div>

              {/* Blueprint Opacity */}
              {blueprintImg && (
                <div>
                  <div className="flex justify-between text-xs mb-1.5 font-semibold">
                    <span>Blueprint Opacity</span>
                    <span className="text-accent font-mono">{Math.round(blueprintOpacity * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0.05"
                    max="1"
                    step="0.05"
                    value={blueprintOpacity}
                    onChange={(e) => setBlueprintOpacity(Number(e.target.value))}
                    className="w-full accent-accent cursor-pointer"
                  />
                </div>
              )}

              {/* Quick Instructions */}
              <div className="rounded-xl bg-muted/40 p-3.5 space-y-2 text-xs text-muted-foreground">
                <div className="flex items-center gap-1.5 font-semibold text-foreground">
                  <M3Lightbulb size={15} className="text-accent" />
                  <span>Studio Quick Guide</span>
                </div>
                <div>• Click <strong>Add Room</strong> and place rooms anywhere on canvas.</div>
                <div>• Select a room and click <strong>4 Corners</strong> to instantly plant receiver nodes.</div>
                <div>• Click <strong>Deploy to Live RTLS</strong> to publish updates to the tracking engine.</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
