import { useRef, useState, useEffect } from 'react'
import { type MapItem, type MapItemKind, type Geofence } from '../../lib/simulation'

interface Props {
  mapItems: MapItem[]
  onMapItems: (items: MapItem[]) => void
}

export interface SchematicAnchor {
  id: string
  label: string
  x: number // percent 0-100
  y: number // percent 0-100
  roomId?: string
  corner?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'top-center' | 'custom'
  txPower: number
  channel: number
  host: boolean
}

export interface SchematicRoom extends Geofence {
  nodeCount?: 3 | 4
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

const TEMPLATES: Record<string, SchematicData> = {
  hospital: {
    name: 'Hospital 4-Room Ward & ICU',
    dimensions: { width: 10, height: 10, unit: 'meters' },
    blueprint: null,
    blueprintOpacity: 0.35,
    anchors: [
      // Room A: 4 corner nodes
      { id: 'ANCHOR_01', label: 'Room A (BL)', x: 2, y: 52, roomId: 'room_a', corner: 'bottom-left', txPower: -77.8, channel: 37, host: true },
      { id: 'ANCHOR_02', label: 'Room A (BR)', x: 48, y: 52, roomId: 'room_a', corner: 'bottom-right', txPower: -77.8, channel: 38, host: false },
      { id: 'ANCHOR_03', label: 'Room A (TL)', x: 2, y: 98, roomId: 'room_a', corner: 'top-left', txPower: -77.8, channel: 39, host: false },
      { id: 'ANCHOR_04', label: 'Room A (TR)', x: 48, y: 98, roomId: 'room_a', corner: 'top-right', txPower: -77.8, channel: 37, host: false },

      // Room B: 4 corner nodes
      { id: 'ANCHOR_05', label: 'Room B (BL)', x: 52, y: 52, roomId: 'room_b', corner: 'bottom-left', txPower: -77.8, channel: 38, host: false },
      { id: 'ANCHOR_06', label: 'Room B (BR)', x: 98, y: 52, roomId: 'room_b', corner: 'bottom-right', txPower: -77.8, channel: 39, host: false },
      { id: 'ANCHOR_07', label: 'Room B (TL)', x: 52, y: 98, roomId: 'room_b', corner: 'top-left', txPower: -77.8, channel: 37, host: false },
      { id: 'ANCHOR_08', label: 'Room B (TR)', x: 98, y: 98, roomId: 'room_b', corner: 'top-right', txPower: -77.8, channel: 38, host: false },

      // Room C: 4 corner nodes
      { id: 'ANCHOR_09', label: 'Room C (BL)', x: 2, y: 2, roomId: 'room_c', corner: 'bottom-left', txPower: -77.8, channel: 39, host: false },
      { id: 'ANCHOR_10', label: 'Room C (BR)', x: 48, y: 2, roomId: 'room_c', corner: 'bottom-right', txPower: -77.8, channel: 37, host: false },
      { id: 'ANCHOR_11', label: 'Room C (TL)', x: 2, y: 48, roomId: 'room_c', corner: 'top-left', txPower: -77.8, channel: 38, host: false },
      { id: 'ANCHOR_12', label: 'Room C (TR)', x: 48, y: 48, roomId: 'room_c', corner: 'top-right', txPower: -77.8, channel: 39, host: false },
    ],
    rooms: [
      { id: 'room_a', name: 'Room A (ICU Bedroom 1)', x: 0, y: 50, w: 50, h: 50, restricted: false, allow: [], nodeCount: 4 },
      { id: 'room_b', name: 'Room B (Patient Bedroom 2)', x: 50, y: 50, w: 50, h: 50, restricted: false, allow: [], nodeCount: 4 },
      { id: 'room_c', name: 'Room C (Medical Station)', x: 0, y: 0, w: 50, h: 50, restricted: false, allow: [], nodeCount: 4 },
      { id: 'room_d', name: 'Room D (Emergency Ward)', x: 50, y: 0, w: 50, h: 50, restricted: true, allow: ['WC:HR:00:00:00:04'], nodeCount: 4 },
    ],
    walls: [
      { id: 'w1', kind: 'wall', label: 'Central Partition', x: 49, y: 0, w: 2, h: 100, attenuation: 8 },
      { id: 'w2', kind: 'wall', label: 'Horizontal Divider', x: 0, y: 49, w: 100, h: 2, attenuation: 8 },
      { id: 'd1', kind: 'door', label: 'ICU Door', x: 22, y: 48.5, w: 6, h: 3, attenuation: 0 },
      { id: 'd2', kind: 'door', label: 'Ward Door', x: 72, y: 48.5, w: 6, h: 3, attenuation: 0 },
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
      { id: 'ANCHOR_08', label: 'Boardroom (TR)', x: 95, y: 94, roomId: 'boardroom', corner: 'top-right', txPower: -77.8, channel: 38, host: false },
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

type ActiveLayer = 'blueprint' | 'rooms' | 'anchors' | 'walls' | 'settings'

export function FloorEditor({ mapItems, onMapItems }: Props) {
  const svgRef = useRef<SVGSVGElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const jsonInputRef = useRef<HTMLInputElement>(null)

  // Building & schematic dimensions
  const [schematicName, setSchematicName] = useState('Hospital 4-Room Ward')
  const [buildingDims, setBuildingDims] = useState({ width: 10, height: 10, unit: 'meters' })
  const [blueprintImg, setBlueprintImg] = useState<string | null>(() => localStorage.getItem('rtls_blueprint_img'))
  const [blueprintOpacity, setBlueprintOpacity] = useState<number>(() => Number(localStorage.getItem('rtls_blueprint_opacity')) || 0.4)
  const [showBlueprint, setShowBlueprint] = useState(true)

  // Anchors & Rooms state
  const [anchors, setAnchors] = useState<SchematicAnchor[]>(() => {
    const saved = localStorage.getItem('rtls_schematic_anchors')
    return saved ? JSON.parse(saved) : TEMPLATES.hospital.anchors
  })

  const [rooms, setRooms] = useState<SchematicRoom[]>(() => {
    const saved = localStorage.getItem('rtls_schematic_rooms')
    return saved ? JSON.parse(saved) : TEMPLATES.hospital.rooms
  })

  const [activeLayer, setActiveLayer] = useState<ActiveLayer>('rooms')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedType, setSelectedType] = useState<'anchor' | 'room' | 'wall' | null>(null)
  const [cursorPos, setCursorPos] = useState<{ xPct: number; yPct: number; xM: number; yM: number } | null>(null)
  const [deployStatus, setDeployStatus] = useState<string | null>(null)
  const [cornerInsetPct, setCornerInsetPct] = useState(2.0) // 2% inset from corners

  const dragRef = useRef<{
    id: string
    type: 'anchor' | 'room' | 'wall' | 'room-resize'
    handle?: 'tl' | 'tr' | 'bl' | 'br'
    startX: number
    startY: number
    initialRoom?: SchematicRoom
    dx: number
    dy: number
  } | null>(null)

  // Persist
  useEffect(() => {
    if (blueprintImg) localStorage.setItem('rtls_blueprint_img', blueprintImg)
    else localStorage.removeItem('rtls_blueprint_img')
    localStorage.setItem('rtls_blueprint_opacity', String(blueprintOpacity))
    localStorage.setItem('rtls_schematic_anchors', JSON.stringify(anchors))
    localStorage.setItem('rtls_schematic_rooms', JSON.stringify(rooms))
  }, [blueprintImg, blueprintOpacity, anchors, rooms])

  const toPct = (clientX: number, clientY: number) => {
    if (!svgRef.current) return { x: 50, y: 50 }
    const r = svgRef.current.getBoundingClientRect()
    const x = Math.max(0, Math.min(100, ((clientX - r.left) / r.width) * 100))
    const y = Math.max(0, Math.min(100, ((clientY - r.top) / r.height) * 100))
    return { x: Math.round(x * 10) / 10, y: Math.round(y * 10) / 10 }
  }

  // Generate Corner Anchors for a Specific Room
  const generateRoomCornerAnchors = (room: SchematicRoom, count: 3 | 4) => {
    const inset = cornerInsetPct
    const minX = Math.min(100, Math.max(0, room.x + inset))
    const maxX = Math.min(100, Math.max(0, room.x + room.w - inset))
    const minY = Math.min(100, Math.max(0, room.y + inset))
    const maxY = Math.min(100, Math.max(0, room.y + room.h - inset))

    // Remove existing anchors attached to this room
    const filteredAnchors = anchors.filter((a) => a.roomId !== room.id)
    const roomShort = room.name.split('(')[0].trim() || 'Room'

    let newCornerAnchors: SchematicAnchor[] = []

    if (count === 4) {
      newCornerAnchors = [
        {
          id: `A_${room.id.slice(0, 6)}_BL`,
          label: `${roomShort} (BL)`,
          x: Math.round(minX * 10) / 10,
          y: Math.round(minY * 10) / 10,
          roomId: room.id,
          corner: 'bottom-left',
          txPower: -77.8,
          channel: 37,
          host: false,
        },
        {
          id: `A_${room.id.slice(0, 6)}_BR`,
          label: `${roomShort} (BR)`,
          x: Math.round(maxX * 10) / 10,
          y: Math.round(minY * 10) / 10,
          roomId: room.id,
          corner: 'bottom-right',
          txPower: -77.8,
          channel: 38,
          host: false,
        },
        {
          id: `A_${room.id.slice(0, 6)}_TL`,
          label: `${roomShort} (TL)`,
          x: Math.round(minX * 10) / 10,
          y: Math.round(maxY * 10) / 10,
          roomId: room.id,
          corner: 'top-left',
          txPower: -77.8,
          channel: 39,
          host: false,
        },
        {
          id: `A_${room.id.slice(0, 6)}_TR`,
          label: `${roomShort} (TR)`,
          x: Math.round(maxX * 10) / 10,
          y: Math.round(maxY * 10) / 10,
          roomId: room.id,
          corner: 'top-right',
          txPower: -77.8,
          channel: 37,
          host: false,
        },
      ]
    } else {
      // 3 Triangulation Nodes
      newCornerAnchors = [
        {
          id: `A_${room.id.slice(0, 6)}_BL`,
          label: `${roomShort} (BL)`,
          x: Math.round(minX * 10) / 10,
          y: Math.round(minY * 10) / 10,
          roomId: room.id,
          corner: 'bottom-left',
          txPower: -77.8,
          channel: 37,
          host: false,
        },
        {
          id: `A_${room.id.slice(0, 6)}_BR`,
          label: `${roomShort} (BR)`,
          x: Math.round(maxX * 10) / 10,
          y: Math.round(minY * 10) / 10,
          roomId: room.id,
          corner: 'bottom-right',
          txPower: -77.8,
          channel: 38,
          host: false,
        },
        {
          id: `A_${room.id.slice(0, 6)}_TC`,
          label: `${roomShort} (TC)`,
          x: Math.round(((minX + maxX) / 2) * 10) / 10,
          y: Math.round(maxY * 10) / 10,
          roomId: room.id,
          corner: 'top-center',
          txPower: -77.8,
          channel: 39,
          host: false,
        },
      ]
    }

    // Ensure at least one host anchor
    const all = [...filteredAnchors, ...newCornerAnchors]
    if (!all.some((a) => a.host) && all.length > 0) {
      all[0].host = true
    }

    setAnchors(all)
    setRooms(rooms.map((r) => (r.id === room.id ? { ...r, nodeCount: count } : r)))
    setDeployStatus(`Placed ${count} corner nodes in ${room.name}`)
    setTimeout(() => setDeployStatus(null), 3000)
  }

  // Snap all existing room anchors to updated room boundaries
  const resnapAnchorsForRoom = (room: SchematicRoom) => {
    const inset = cornerInsetPct
    const minX = Math.min(100, Math.max(0, room.x + inset))
    const maxX = Math.min(100, Math.max(0, room.x + room.w - inset))
    const minY = Math.min(100, Math.max(0, room.y + inset))
    const maxY = Math.min(100, Math.max(0, room.y + room.h - inset))

    setAnchors((prev) =>
      prev.map((a) => {
        if (a.roomId !== room.id) return a
        if (a.corner === 'bottom-left') return { ...a, x: minX, y: minY }
        if (a.corner === 'bottom-right') return { ...a, x: maxX, y: minY }
        if (a.corner === 'top-left') return { ...a, x: minX, y: maxY }
        if (a.corner === 'top-right') return { ...a, x: maxX, y: maxY }
        if (a.corner === 'top-center') return { ...a, x: (minX + maxX) / 2, y: maxY }
        return a
      })
    )
  }

  // Auto-place 3 or 4 corner nodes for all rooms in one click
  const autoLayoutAllRooms = (count: 3 | 4) => {
    let combinedAnchors: SchematicAnchor[] = []
    rooms.forEach((r) => {
      const inset = cornerInsetPct
      const minX = Math.min(100, Math.max(0, r.x + inset))
      const maxX = Math.min(100, Math.max(0, r.x + r.w - inset))
      const minY = Math.min(100, Math.max(0, r.y + inset))
      const maxY = Math.min(100, Math.max(0, r.y + r.h - inset))
      const roomShort = r.name.split('(')[0].trim() || 'Room'

      if (count === 4) {
        combinedAnchors.push(
          { id: `A_${r.id.slice(0, 5)}_BL`, label: `${roomShort} (BL)`, x: minX, y: minY, roomId: r.id, corner: 'bottom-left', txPower: -77.8, channel: 37, host: combinedAnchors.length === 0 },
          { id: `A_${r.id.slice(0, 5)}_BR`, label: `${roomShort} (BR)`, x: maxX, y: minY, roomId: r.id, corner: 'bottom-right', txPower: -77.8, channel: 38, host: false },
          { id: `A_${r.id.slice(0, 5)}_TL`, label: `${roomShort} (TL)`, x: minX, y: maxY, roomId: r.id, corner: 'top-left', txPower: -77.8, channel: 39, host: false },
          { id: `A_${r.id.slice(0, 5)}_TR`, label: `${roomShort} (TR)`, x: maxX, y: maxY, roomId: r.id, corner: 'top-right', txPower: -77.8, channel: 37, host: false }
        )
      } else {
        combinedAnchors.push(
          { id: `A_${r.id.slice(0, 5)}_BL`, label: `${roomShort} (BL)`, x: minX, y: minY, roomId: r.id, corner: 'bottom-left', txPower: -77.8, channel: 37, host: combinedAnchors.length === 0 },
          { id: `A_${r.id.slice(0, 5)}_BR`, label: `${roomShort} (BR)`, x: maxX, y: minY, roomId: r.id, corner: 'bottom-right', txPower: -77.8, channel: 38, host: false },
          { id: `A_${r.id.slice(0, 5)}_TC`, label: `${roomShort} (TC)`, x: (minX + maxX) / 2, y: maxY, roomId: r.id, corner: 'top-center', txPower: -77.8, channel: 39, host: false }
        )
      }
    })

    setAnchors(combinedAnchors)
    setRooms(rooms.map((r) => ({ ...r, nodeCount: count })))
    setDeployStatus(`Auto-generated ${combinedAnchors.length} corner nodes (${count} nodes per room)!`)
    setTimeout(() => setDeployStatus(null), 3000)
  }

  // Pointer Handlers for Dragging & Resizing
  const handlePointerDown = (
    e: React.PointerEvent,
    id: string,
    type: 'anchor' | 'room' | 'wall' | 'room-resize',
    curX: number,
    curY: number,
    handle?: 'tl' | 'tr' | 'bl' | 'br'
  ) => {
    e.stopPropagation()
    const p = toPct(e.clientX, e.clientY)

    if (type === 'room-resize') {
      const room = rooms.find((r) => r.id === id)
      if (!room) return
      dragRef.current = { id, type: 'room-resize', handle, startX: p.x, startY: p.y, initialRoom: { ...room }, dx: 0, dy: 0 }
    } else {
      setSelectedId(id)
      setSelectedType(type as any)
      dragRef.current = { id, type: type as any, startX: p.x, startY: p.y, dx: p.x - curX, dy: p.y - curY }
    }
    ;(e.target as Element).setPointerCapture?.(e.pointerId)
  }

  const handlePointerMove = (e: React.PointerEvent) => {
    const p = toPct(e.clientX, e.clientY)
    setCursorPos({
      xPct: p.x,
      yPct: p.y,
      xM: Math.round(((p.x / 100) * buildingDims.width) * 100) / 100,
      yM: Math.round(((p.y / 100) * buildingDims.height) * 100) / 100,
    })

    if (!dragRef.current) return
    const { id, type, handle, initialRoom, dx, dy } = dragRef.current

    if (type === 'room-resize' && initialRoom && handle) {
      let newX = initialRoom.x
      let newY = initialRoom.y
      let newW = initialRoom.w
      let newH = initialRoom.h

      if (handle === 'br') {
        newW = Math.max(5, Math.min(100 - newX, p.x - newX))
        newH = Math.max(5, Math.min(100 - newY, p.y - newY))
      } else if (handle === 'tr') {
        newW = Math.max(5, Math.min(100 - newX, p.x - newX))
        newY = Math.max(0, Math.min(initialRoom.y + initialRoom.h - 5, p.y))
        newH = initialRoom.y + initialRoom.h - newY
      } else if (handle === 'bl') {
        newX = Math.max(0, Math.min(initialRoom.x + initialRoom.w - 5, p.x))
        newW = initialRoom.x + initialRoom.w - newX
        newH = Math.max(5, Math.min(100 - newY, p.y - newY))
      } else if (handle === 'tl') {
        newX = Math.max(0, Math.min(initialRoom.x + initialRoom.w - 5, p.x))
        newY = Math.max(0, Math.min(initialRoom.y + initialRoom.h - 5, p.y))
        newW = initialRoom.x + initialRoom.w - newX
        newH = initialRoom.y + initialRoom.h - newY
      }

      const updated = {
        ...initialRoom,
        x: Math.round(newX * 10) / 10,
        y: Math.round(newY * 10) / 10,
        w: Math.round(newW * 10) / 10,
        h: Math.round(newH * 10) / 10,
      }
      setRooms((prev) => prev.map((r) => (r.id === id ? updated : r)))
      resnapAnchorsForRoom(updated)
      return
    }

    const newX = Math.max(0, Math.min(100, Math.round((p.x - dx) * 10) / 10))
    const newY = Math.max(0, Math.min(100, Math.round((p.y - dy) * 10) / 10))

    if (type === 'anchor') {
      setAnchors((prev) => prev.map((a) => (a.id === id ? { ...a, x: newX, y: newY } : a)))
    } else if (type === 'room') {
      setRooms((prev) => {
        const updated = prev.map((r) => {
          if (r.id !== id) return r
          const clampedX = Math.min(100 - r.w, newX)
          const clampedY = Math.min(100 - r.h, newY)
          const roomMoved = { ...r, x: clampedX, y: clampedY }
          resnapAnchorsForRoom(roomMoved)
          return roomMoved
        })
        return updated
      })
    } else if (type === 'wall') {
      onMapItems(mapItems.map((m) => (m.id === id ? { ...m, x: newX, y: newY } : m)))
    }
  }

  const handlePointerUp = () => {
    dragRef.current = null
  }

  // Add Elements
  const addRoom = () => {
    const nextIdx = rooms.length + 1
    const newR: SchematicRoom = {
      id: `room_${Date.now().toString(36)}`,
      name: `Room ${String.fromCharCode(64 + nextIdx)}`,
      x: 20,
      y: 20,
      w: 40,
      h: 40,
      restricted: false,
      allow: [],
      nodeCount: 4,
    }
    setRooms([...rooms, newR])
    setSelectedId(newR.id)
    setSelectedType('room')
    setActiveLayer('rooms')
    generateRoomCornerAnchors(newR, 4)
  }

  const addAnchor = () => {
    const nextIdx = anchors.length + 1
    const pad = nextIdx < 10 ? `0${nextIdx}` : `${nextIdx}`
    const newA: SchematicAnchor = {
      id: `ANCHOR_${pad}`,
      label: `Anchor ${pad}`,
      x: 50,
      y: 50,
      txPower: -77.8,
      channel: 37,
      host: anchors.length === 0,
    }
    setAnchors([...anchors, newA])
    setSelectedId(newA.id)
    setSelectedType('anchor')
    setActiveLayer('anchors')
  }

  const addWall = (kind: MapItemKind) => {
    const newW: MapItem = {
      id: `${kind}_${Date.now().toString(36)}`,
      kind,
      label: kind === 'wall' ? 'Partition Wall' : kind === 'door' ? 'Doorway' : 'Furniture',
      x: 40,
      y: 40,
      w: kind === 'wall' ? 20 : 6,
      h: kind === 'wall' ? 2 : 6,
      attenuation: kind === 'wall' ? 8 : kind === 'furniture' ? 4 : 0,
    }
    onMapItems([...mapItems, newW])
    setSelectedId(newW.id)
    setSelectedType('wall')
    setActiveLayer('walls')
  }

  // Dimension helpers for Rooms in Meters
  const getRoomMeters = (r: SchematicRoom) => ({
    x: Math.round(((r.x / 100) * buildingDims.width) * 10) / 10,
    y: Math.round(((r.y / 100) * buildingDims.height) * 10) / 10,
    w: Math.round(((r.w / 100) * buildingDims.width) * 10) / 10,
    h: Math.round(((r.h / 100) * buildingDims.height) * 10) / 10,
  })

  const updateRoomMeters = (r: SchematicRoom, field: 'x' | 'y' | 'w' | 'h', valMeters: number) => {
    const isXorW = field === 'x' || field === 'w'
    const totalDim = isXorW ? buildingDims.width : buildingDims.height
    const pct = Math.max(1, Math.min(100, (valMeters / totalDim) * 100))
    const updated = { ...r, [field]: Math.round(pct * 10) / 10 }
    setRooms(rooms.map((rm) => (rm.id === r.id ? updated : rm)))
    resnapAnchorsForRoom(updated)
  }

  // Deploy to Backend
  const deployToBackend = async () => {
    setDeployStatus('Deploying to Python Engine (Port 8000)...')
    try {
      const res = await fetch('http://localhost:8000/api/schematic', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: schematicName,
          dimensions: buildingDims,
          anchors: anchors.map((a) => ({
            id: a.id,
            label: a.label,
            x: ((a.x / 100) * buildingDims.width),
            y: ((a.y / 100) * buildingDims.height),
            roomId: a.roomId,
            corner: a.corner,
            txPower: a.txPower,
            channel: a.channel,
            host: a.host,
          })),
          rooms,
          walls: mapItems,
        }),
      })
      if (res.ok) {
        setDeployStatus('✓ Deployed! Live engine updated with corner node positions.')
      } else {
        setDeployStatus('Saved in browser (Backend offline).')
      }
    } catch {
      setDeployStatus('Saved in browser.')
    }
    setTimeout(() => setDeployStatus(null), 3500)
  }

  // File Handlers
  const handleImageUpload = (file: File) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      setBlueprintImg(e.target?.result as string)
      setShowBlueprint(true)
    }
    reader.readAsDataURL(file)
  }

  const handleExportJson = () => {
    const payload: SchematicData = {
      name: schematicName,
      dimensions: buildingDims,
      blueprint: blueprintImg,
      blueprintOpacity,
      anchors,
      rooms,
      walls: mapItems,
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${schematicName.toLowerCase().replace(/[^a-z0-9]+/g, '_')}_schematic.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleJsonImport = (file: File) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const parsed: SchematicData = JSON.parse(e.target?.result as string)
        if (parsed.name) setSchematicName(parsed.name)
        if (parsed.dimensions) setBuildingDims(parsed.dimensions)
        if (parsed.blueprint) setBlueprintImg(parsed.blueprint)
        if (parsed.anchors) setAnchors(parsed.anchors)
        if (parsed.rooms) setRooms(parsed.rooms)
        if (parsed.walls) onMapItems(parsed.walls)
        setDeployStatus('Schematic imported!')
        setTimeout(() => setDeployStatus(null), 3000)
      } catch {
        alert('Invalid schematic JSON format')
      }
    }
    reader.readAsText(file)
  }

  const selectedAnchor = selectedType === 'anchor' ? anchors.find((a) => a.id === selectedId) : null
  const selectedRoom = selectedType === 'room' ? rooms.find((r) => r.id === selectedId) : null
  const selectedWall = selectedType === 'wall' ? mapItems.find((w) => w.id === selectedId) : null

  return (
    <div className="space-y-4">
      {/* Top Header Controls */}
      <div className="rounded-xl border border-border bg-card p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={schematicName}
                onChange={(e) => setSchematicName(e.target.value)}
                className="text-base font-bold text-foreground bg-transparent border-b border-transparent hover:border-border focus:border-accent outline-none px-1"
              />
              <span className="rounded-full bg-accent/10 px-2.5 py-0.5 font-mono text-[11px] font-semibold text-accent uppercase">
                {buildingDims.width}m × {buildingDims.height}m ({(buildingDims.width * buildingDims.height).toFixed(0)} m²)
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              3-4 Corner Node Architecture · Real-World Dimension Editor · Dynamic Blueprint Tracing
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <input type="file" ref={fileInputRef} accept="image/*" className="hidden" onChange={(e) => e.target.files?.[0] && handleImageUpload(e.target.files[0])} />
            <input type="file" ref={jsonInputRef} accept=".json,.schematic" className="hidden" onChange={(e) => e.target.files?.[0] && handleJsonImport(e.target.files[0])} />

            {/* Quick Auto-Layout Buttons */}
            <button
              onClick={() => autoLayoutAllRooms(4)}
              title="Place 4 corner anchor nodes in every room automatically"
              className="rounded-lg border border-purple-500/30 bg-purple-500/10 hover:bg-purple-500/20 px-3 py-1.5 text-xs font-semibold text-purple-300 transition-colors flex items-center gap-1.5"
            >
              🔲 Auto 4-Corners (All Rooms)
            </button>

            <button
              onClick={() => autoLayoutAllRooms(3)}
              title="Place 3 triangulation anchor nodes in every room automatically"
              className="rounded-lg border border-sky-500/30 bg-sky-500/10 hover:bg-sky-500/20 px-3 py-1.5 text-xs font-semibold text-sky-300 transition-colors flex items-center gap-1.5"
            >
              🔺 Auto 3-Nodes (All Rooms)
            </button>

            <button
              onClick={() => fileInputRef.current?.click()}
              className="rounded-lg border border-border bg-panel hover:bg-muted px-3 py-1.5 text-xs font-semibold text-foreground transition-colors"
            >
              🖼️ Upload Blueprint
            </button>

            <button
              onClick={() => jsonInputRef.current?.click()}
              className="rounded-lg border border-border bg-panel hover:bg-muted px-3 py-1.5 text-xs font-semibold text-foreground transition-colors"
            >
              📥 Import JSON
            </button>

            <button
              onClick={handleExportJson}
              className="rounded-lg border border-border bg-panel hover:bg-muted px-3 py-1.5 text-xs font-semibold text-foreground transition-colors"
            >
              📤 Export JSON
            </button>

            <button
              onClick={deployToBackend}
              className="rounded-lg bg-accent hover:bg-accent/90 px-4 py-1.5 text-xs font-bold text-primary-foreground transition-all shadow-sm flex items-center gap-1.5"
            >
              🚀 Deploy to Live RTLS
            </button>
          </div>
        </div>

        {deployStatus && (
          <div className="rounded-lg border border-accent/30 bg-accent/10 px-3 py-2 text-xs font-semibold text-accent animate-pulse">
            {deployStatus}
          </div>
        )}
      </div>

      {/* Layer Tabs */}
      <div className="flex gap-1 border-b border-border text-xs">
        {[
          { id: 'rooms', label: `🏢 Rooms & Dimensions (${rooms.length})` },
          { id: 'anchors', label: `📍 Corner Nodes (${anchors.length})` },
          { id: 'walls', label: `🧱 RF Walls & Doors (${mapItems.length})` },
          { id: 'blueprint', label: `🖼️ Blueprint Image ${blueprintImg ? '✓' : ''}` },
          { id: 'settings', label: `📐 Building Dimensions` },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveLayer(tab.id as ActiveLayer)}
            className={`px-4 py-2 font-medium transition-colors border-b-2 -mb-px ${
              activeLayer === tab.id
                ? 'border-accent text-accent font-bold'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Main Studio Workspace */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_340px]">
        {/* Left: Interactive Canvas */}
        <div className="rounded-xl border border-border bg-card p-4 space-y-3">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-3">
              <span className="font-semibold text-foreground">Interactive Room & Corner Node Canvas</span>
              {cursorPos && (
                <span className="font-mono text-[11px] text-muted-foreground bg-panel px-2 py-0.5 rounded border border-border">
                  Cursor: {cursorPos.xM}m, {cursorPos.yM}m ({cursorPos.xPct}%, {cursorPos.yPct}%)
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={addRoom}
                className="rounded-lg bg-purple-600 hover:bg-purple-500 px-3 py-1 text-xs font-semibold text-white transition-colors"
              >
                + Add Room & 4 Nodes
              </button>
              <button
                onClick={addAnchor}
                className="rounded-lg bg-sky-600 hover:bg-sky-500 px-3 py-1 text-xs font-semibold text-white transition-colors"
              >
                + Custom Anchor
              </button>
            </div>
          </div>

          <div className="relative overflow-hidden rounded-xl border border-border bg-panel select-none">
            <svg
              ref={svgRef}
              viewBox="0 0 100 100"
              className="block w-full touch-none"
              onClick={() => {
                setSelectedId(null)
                setSelectedType(null)
              }}
              onPointerMove={handlePointerMove}
              onPointerUp={handlePointerUp}
              onPointerLeave={handlePointerUp}
            >
              <defs>
                <pattern id="grid_major" width="10" height="10" patternUnits="userSpaceOnUse">
                  <path d="M 10 0 L 0 0 0 10" fill="none" stroke="var(--border)" strokeWidth="0.25" opacity="0.8" />
                </pattern>
                <pattern id="grid_minor" width="2" height="2" patternUnits="userSpaceOnUse">
                  <path d="M 2 0 L 0 0 0 2" fill="none" stroke="var(--border)" strokeWidth="0.08" opacity="0.4" />
                </pattern>
                <pattern id="restricted_hatch" width="3" height="3" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                  <line x1="0" y1="0" x2="0" y2="3" stroke="#ef4444" strokeWidth="0.4" opacity="0.3" />
                </pattern>
              </defs>

              {/* Grid Background */}
              <rect x="0" y="0" width="100" height="100" fill="url(#grid_minor)" />
              <rect x="0" y="0" width="100" height="100" fill="url(#grid_major)" />

              {/* Blueprint Image Overlay */}
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

              {/* Layer 1: Rooms / Geofences */}
              {rooms.map((r) => {
                const isSel = selectedId === r.id && selectedType === 'room'
                const rM = getRoomMeters(r)
                const roomAnchors = anchors.filter((a) => a.roomId === r.id)

                return (
                  <g
                    key={r.id}
                    onPointerDown={(e) => handlePointerDown(e, r.id, 'room', r.x, r.y)}
                    className="cursor-move"
                  >
                    <rect
                      x={r.x}
                      y={r.y}
                      width={r.w}
                      height={r.h}
                      rx="1"
                      fill={r.restricted ? 'url(#restricted_hatch)' : 'var(--muted)'}
                      fillOpacity={isSel ? 0.55 : 0.25}
                      stroke={isSel ? '#a855f7' : r.restricted ? '#ef4444' : 'var(--border)'}
                      strokeWidth={isSel ? 0.7 : 0.35}
                      strokeDasharray={r.restricted ? '1.5 1' : undefined}
                    />

                    {/* Room Dimension Label */}
                    <text
                      x={r.x + 2}
                      y={r.y + 4.5}
                      fontSize="2.2"
                      fill={r.restricted ? '#ef4444' : 'var(--foreground)'}
                      fontWeight="700"
                      fontFamily="var(--font-mono)"
                    >
                      {r.restricted ? '⚠️ ' : ''}{r.name}
                    </text>
                    <text
                      x={r.x + 2}
                      y={r.y + 7.5}
                      fontSize="1.6"
                      fill="var(--muted-foreground)"
                      fontFamily="var(--font-mono)"
                    >
                      {rM.w}m × {rM.h}m ({roomAnchors.length} corner nodes)
                    </text>

                    {/* Corner Guides connecting anchors to room corners */}
                    {isSel && (
                      <>
                        {/* Resize Handles on 4 corners */}
                        <rect
                          x={r.x + r.w - 1.5}
                          y={r.y + r.h - 1.5}
                          width="3"
                          height="3"
                          fill="#a855f7"
                          stroke="#ffffff"
                          strokeWidth="0.3"
                          className="cursor-se-resize"
                          onPointerDown={(e) => handlePointerDown(e, r.id, 'room-resize', r.x, r.y, 'br')}
                        />
                        <rect
                          x={r.x - 1.5}
                          y={r.y + r.h - 1.5}
                          width="3"
                          height="3"
                          fill="#a855f7"
                          stroke="#ffffff"
                          strokeWidth="0.3"
                          className="cursor-sw-resize"
                          onPointerDown={(e) => handlePointerDown(e, r.id, 'room-resize', r.x, r.y, 'bl')}
                        />
                        <rect
                          x={r.x + r.w - 1.5}
                          y={r.y - 1.5}
                          width="3"
                          height="3"
                          fill="#a855f7"
                          stroke="#ffffff"
                          strokeWidth="0.3"
                          className="cursor-ne-resize"
                          onPointerDown={(e) => handlePointerDown(e, r.id, 'room-resize', r.x, r.y, 'tr')}
                        />
                        <rect
                          x={r.x - 1.5}
                          y={r.y - 1.5}
                          width="3"
                          height="3"
                          fill="#a855f7"
                          stroke="#ffffff"
                          strokeWidth="0.3"
                          className="cursor-nw-resize"
                          onPointerDown={(e) => handlePointerDown(e, r.id, 'room-resize', r.x, r.y, 'tl')}
                        />
                      </>
                    )}
                  </g>
                )
              })}

              {/* Layer 2: Walls & Obstacles */}
              {mapItems.map((m) => {
                const isSel = selectedId === m.id && selectedType === 'wall'
                return (
                  <g
                    key={m.id}
                    onPointerDown={(e) => handlePointerDown(e, m.id, 'wall', m.x, m.y)}
                    className="cursor-move"
                  >
                    <rect
                      x={m.x}
                      y={m.y}
                      width={m.w}
                      height={m.h}
                      rx="0.4"
                      fill={m.kind === 'wall' ? 'var(--foreground)' : m.kind === 'door' ? 'transparent' : 'var(--muted)'}
                      fillOpacity={m.kind === 'wall' ? 0.8 : 0.6}
                      stroke={isSel ? '#10b981' : m.kind === 'door' ? 'var(--accent)' : 'var(--muted-foreground)'}
                      strokeWidth={isSel ? 0.6 : 0.25}
                      strokeDasharray={m.kind === 'door' ? '0.8 0.6' : undefined}
                    />
                    {m.w > 6 && (
                      <text
                        x={m.x + m.w / 2}
                        y={m.y + m.h / 2 + 0.6}
                        fontSize="1.6"
                        textAnchor="middle"
                        fill="var(--muted-foreground)"
                        fontFamily="var(--font-mono)"
                        pointerEvents="none"
                      >
                        {m.label}
                      </text>
                    )}
                  </g>
                )
              })}

              {/* Layer 3: ESP32 Corner Anchor Nodes */}
              {anchors.map((a) => {
                const isSel = selectedId === a.id && selectedType === 'anchor'
                const isHost = a.host

                return (
                  <g
                    key={a.id}
                    onPointerDown={(e) => handlePointerDown(e, a.id, 'anchor', a.x, a.y)}
                    className="cursor-pointer"
                  >
                    {/* Outer Glow / Halo */}
                    <circle
                      cx={a.x}
                      cy={a.y}
                      r={isSel ? 3.0 : 2.0}
                      fill={isHost ? '#10b981' : '#0284c7'}
                      fillOpacity={isSel ? 0.4 : 0.2}
                    />
                    {/* Main Node Point */}
                    <circle
                      cx={a.x}
                      cy={a.y}
                      r={isSel ? 2.2 : 1.6}
                      fill={isHost ? '#10b981' : isSel ? '#38bdf8' : '#0284c7'}
                      stroke="#ffffff"
                      strokeWidth="0.4"
                    />
                    <circle cx={a.x} cy={a.y} r="0.5" fill="#ffffff" />

                    {/* Node Badge Text */}
                    <text
                      x={a.x + 2.2}
                      y={a.y + 0.8}
                      fontSize="1.8"
                      fill="var(--foreground)"
                      fontFamily="var(--font-mono)"
                      fontWeight="700"
                    >
                      {a.label}
                    </text>
                  </g>
                )
              })}
            </svg>
          </div>
        </div>

        {/* Right: Inspector & Dimension Panel */}
        <div className="rounded-xl border border-border bg-card p-4 space-y-4">
          {/* Room Inspector with Live Dimensions & Corner Placement */}
          {selectedRoom && (
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-2">
                <div>
                  <h4 className="text-sm font-semibold text-purple-400">🏢 Room Configuration</h4>
                  <span className="text-[10px] font-mono text-muted-foreground">{selectedRoom.id}</span>
                </div>
                <button
                  onClick={() => {
                    setRooms(rooms.filter((r) => r.id !== selectedRoom.id))
                    setAnchors(anchors.filter((a) => a.roomId !== selectedRoom.id))
                    setSelectedId(null)
                  }}
                  className="text-xs text-rose-400 hover:text-rose-300 transition-colors font-medium"
                >
                  Delete Room
                </button>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Room Name</label>
                <input
                  type="text"
                  value={selectedRoom.name}
                  onChange={(e) => setRooms(rooms.map((r) => (r.id === selectedRoom.id ? { ...r, name: e.target.value } : r)))}
                  className="w-full rounded-lg border border-border bg-panel px-3 py-1.5 text-xs text-foreground outline-none font-medium"
                />
              </div>

              {/* Editable Dimensions in Meters */}
              <div className="rounded-lg border border-border bg-panel p-3 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-foreground">📏 Room Dimensions (Meters)</span>
                  <span className="text-[11px] font-mono text-muted-foreground">
                    {(getRoomMeters(selectedRoom).w * getRoomMeters(selectedRoom).h).toFixed(1)} m²
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <label className="text-[11px] text-muted-foreground">Width (m)</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0.5"
                      max={buildingDims.width}
                      value={getRoomMeters(selectedRoom).w}
                      onChange={(e) => updateRoomMeters(selectedRoom, 'w', parseFloat(e.target.value) || 1)}
                      className="w-full rounded-md border border-border bg-card px-2.5 py-1.5 text-xs font-mono outline-none"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[11px] text-muted-foreground">Height (m)</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0.5"
                      max={buildingDims.height}
                      value={getRoomMeters(selectedRoom).h}
                      onChange={(e) => updateRoomMeters(selectedRoom, 'h', parseFloat(e.target.value) || 1)}
                      className="w-full rounded-md border border-border bg-card px-2.5 py-1.5 text-xs font-mono outline-none"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 pt-1 border-t border-border/50">
                  <div className="space-y-1">
                    <label className="text-[11px] text-muted-foreground">X Offset (m)</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      max={buildingDims.width}
                      value={getRoomMeters(selectedRoom).x}
                      onChange={(e) => updateRoomMeters(selectedRoom, 'x', parseFloat(e.target.value) || 0)}
                      className="w-full rounded-md border border-border bg-card px-2.5 py-1.5 text-xs font-mono outline-none"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[11px] text-muted-foreground">Y Offset (m)</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      max={buildingDims.height}
                      value={getRoomMeters(selectedRoom).y}
                      onChange={(e) => updateRoomMeters(selectedRoom, 'y', parseFloat(e.target.value) || 0)}
                      className="w-full rounded-md border border-border bg-card px-2.5 py-1.5 text-xs font-mono outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* Corner Node Generator for this Room */}
              <div className="rounded-lg border border-purple-500/20 bg-purple-500/5 p-3 space-y-2.5">
                <span className="text-xs font-bold text-purple-300 block">📍 Corner Nodes ({anchors.filter((a) => a.roomId === selectedRoom.id).length} Active)</span>
                <p className="text-[11px] text-muted-foreground">
                  Snap 3 or 4 anchor nodes directly into the corners of this room.
                </p>

                <div className="grid grid-cols-2 gap-2 pt-1">
                  <button
                    onClick={() => generateRoomCornerAnchors(selectedRoom, 4)}
                    className="rounded-lg bg-purple-600 hover:bg-purple-500 px-3 py-2 text-xs font-bold text-white transition-colors flex items-center justify-center gap-1 shadow-sm"
                  >
                    🔲 4 Corner Nodes
                  </button>
                  <button
                    onClick={() => generateRoomCornerAnchors(selectedRoom, 3)}
                    className="rounded-lg bg-sky-600 hover:bg-sky-500 px-3 py-2 text-xs font-bold text-white transition-colors flex items-center justify-center gap-1 shadow-sm"
                  >
                    🔺 3 Corner Nodes
                  </button>
                </div>

                <button
                  onClick={() => resnapAnchorsForRoom(selectedRoom)}
                  className="w-full rounded-md border border-purple-500/30 text-purple-300 hover:bg-purple-500/10 py-1 text-xs font-medium transition-colors"
                >
                  🔄 Re-align Nodes to Current Corners
                </button>
              </div>

              {/* Restricted Geofence Toggle */}
              <label className="flex items-center gap-2 pt-1 cursor-pointer text-xs">
                <input
                  type="checkbox"
                  checked={selectedRoom.restricted}
                  onChange={(e) => setRooms(rooms.map((r) => (r.id === selectedRoom.id ? { ...r, restricted: e.target.checked } : r)))}
                  className="rounded accent-rose-500"
                />
                <span className="font-semibold text-rose-400">Restricted Zone (Triggers Alarms)</span>
              </label>
            </div>
          )}

          {/* Anchor Inspector */}
          {selectedAnchor && (
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-2">
                <div>
                  <h4 className="text-sm font-semibold text-sky-400">📍 Anchor Node Inspector</h4>
                  <span className="text-[10px] font-mono text-muted-foreground">{selectedAnchor.id}</span>
                </div>
                <button
                  onClick={() => {
                    setAnchors(anchors.filter((a) => a.id !== selectedAnchor.id))
                    setSelectedId(null)
                  }}
                  className="text-xs text-rose-400 hover:text-rose-300 transition-colors font-medium"
                >
                  Delete Anchor
                </button>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Anchor Label</label>
                <input
                  type="text"
                  value={selectedAnchor.label}
                  onChange={(e) => setAnchors(anchors.map((a) => (a.id === selectedAnchor.id ? { ...a, label: e.target.value } : a)))}
                  className="w-full rounded-lg border border-border bg-panel px-3 py-1.5 text-xs text-foreground outline-none font-medium"
                />
              </div>

              {/* Associated Room & Corner Placement */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Assigned Room</label>
                <select
                  value={selectedAnchor.roomId || ''}
                  onChange={(e) => setAnchors(anchors.map((a) => (a.id === selectedAnchor.id ? { ...a, roomId: e.target.value || undefined } : a)))}
                  className="w-full rounded-lg border border-border bg-panel px-3 py-1.5 text-xs text-foreground outline-none"
                >
                  <option value="">(None - Independent Anchor)</option>
                  {rooms.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Coordinates in Meters */}
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <label className="text-[11px] text-muted-foreground">
                    X Position ({Math.round(((selectedAnchor.x / 100) * buildingDims.width) * 10) / 10}m)
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    value={selectedAnchor.x}
                    onChange={(e) => setAnchors(anchors.map((a) => (a.id === selectedAnchor.id ? { ...a, x: parseFloat(e.target.value) || 0 } : a)))}
                    className="w-full rounded-lg border border-border bg-panel px-2.5 py-1.5 text-xs font-mono outline-none"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[11px] text-muted-foreground">
                    Y Position ({Math.round(((selectedAnchor.y / 100) * buildingDims.height) * 10) / 10}m)
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    value={selectedAnchor.y}
                    onChange={(e) => setAnchors(anchors.map((a) => (a.id === selectedAnchor.id ? { ...a, y: parseFloat(e.target.value) || 0 } : a)))}
                    className="w-full rounded-lg border border-border bg-panel px-2.5 py-1.5 text-xs font-mono outline-none"
                  />
                </div>
              </div>

              {/* RF Properties */}
              <div className="grid grid-cols-2 gap-2 pt-1 border-t border-border">
                <div className="space-y-1">
                  <label className="text-[11px] text-muted-foreground">TX @ 1m (dBm)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={selectedAnchor.txPower}
                    onChange={(e) => setAnchors(anchors.map((a) => (a.id === selectedAnchor.id ? { ...a, txPower: parseFloat(e.target.value) || -77.8 } : a)))}
                    className="w-full rounded-lg border border-border bg-panel px-2.5 py-1.5 text-xs font-mono outline-none"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[11px] text-muted-foreground">BLE Channel</label>
                  <select
                    value={selectedAnchor.channel}
                    onChange={(e) => setAnchors(anchors.map((a) => (a.id === selectedAnchor.id ? { ...a, channel: parseInt(e.target.value) || 37 } : a)))}
                    className="w-full rounded-lg border border-border bg-panel px-2.5 py-1.5 text-xs font-mono outline-none"
                  >
                    <option value={37}>37 (2402 MHz)</option>
                    <option value={38}>38 (2426 MHz)</option>
                    <option value={39}>39 (2480 MHz)</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Building Settings Tab */}
          {activeLayer === 'settings' && (
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-foreground">📐 Building Dimensions</h4>
              <p className="text-xs text-muted-foreground">
                Set total building boundaries. All room sizes, anchor offsets, and live trilateration positions scale to this bounding box.
              </p>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">Total Width (m)</label>
                  <input
                    type="number"
                    min="2"
                    max="200"
                    step="0.5"
                    value={buildingDims.width}
                    onChange={(e) => setBuildingDims({ ...buildingDims, width: parseFloat(e.target.value) || 10 })}
                    className="w-full rounded-lg border border-border bg-panel px-3 py-2 text-xs font-mono outline-none"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">Total Height (m)</label>
                  <input
                    type="number"
                    min="2"
                    max="200"
                    step="0.5"
                    value={buildingDims.height}
                    onChange={(e) => setBuildingDims({ ...buildingDims, height: parseFloat(e.target.value) || 10 })}
                    className="w-full rounded-lg border border-border bg-panel px-3 py-2 text-xs font-mono outline-none"
                  />
                </div>
              </div>

              <div className="space-y-1 pt-2">
                <label className="text-xs font-medium text-muted-foreground">Corner Inset Margin (%)</label>
                <input
                  type="number"
                  min="0.5"
                  max="10"
                  step="0.5"
                  value={cornerInsetPct}
                  onChange={(e) => setCornerInsetPct(parseFloat(e.target.value) || 2.0)}
                  className="w-full rounded-lg border border-border bg-panel px-3 py-1.5 text-xs font-mono outline-none"
                />
                <span className="text-[10px] text-muted-foreground block">Offset distance from room wall corners when snapping nodes.</span>
              </div>
            </div>
          )}

          {/* Blueprint Layer Tab */}
          {activeLayer === 'blueprint' && (
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-foreground">🖼️ Blueprint Layer</h4>
              <p className="text-xs text-muted-foreground">
                Upload CAD blueprints or floorplan images to trace rooms and snap corner nodes accurately.
              </p>

              <div
                onClick={() => fileInputRef.current?.click()}
                className="rounded-xl border-2 border-dashed border-border hover:border-accent bg-panel p-6 text-center cursor-pointer transition-colors"
              >
                <span className="text-2xl block mb-1">📂</span>
                <span className="text-xs font-semibold text-foreground block">Click to Upload Blueprint</span>
                <span className="text-[11px] text-muted-foreground">PNG, JPG, SVG supported</span>
              </div>

              {blueprintImg && (
                <div className="space-y-3 pt-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Layer Opacity</span>
                    <span className="font-mono">{Math.round(blueprintOpacity * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0.05"
                    max="1"
                    step="0.05"
                    value={blueprintOpacity}
                    onChange={(e) => setBlueprintOpacity(parseFloat(e.target.value))}
                    className="w-full accent-accent"
                  />
                  <div className="flex items-center justify-between pt-1">
                    <label className="text-xs text-muted-foreground flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" checked={showBlueprint} onChange={(e) => setShowBlueprint(e.target.checked)} className="rounded accent-accent" />
                      <span>Visible</span>
                    </label>
                    <button onClick={() => setBlueprintImg(null)} className="text-xs text-rose-400 font-medium">
                      Remove
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Default Help Text when nothing selected */}
          {!selectedRoom && !selectedAnchor && !selectedWall && activeLayer !== 'settings' && activeLayer !== 'blueprint' && (
            <div className="py-8 text-center space-y-2 text-muted-foreground">
              <span className="text-2xl block">🏢</span>
              <p className="text-xs font-medium">Click on any Room or Anchor on the canvas to edit its dimensions, or click <strong>"🔲 Auto 4-Corners"</strong> above to populate corner nodes.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
