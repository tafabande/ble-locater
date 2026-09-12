import { useRef, useState, useEffect } from 'react'
import {
  type SurveyPoint,
  type CollectorAnchor,
  type WalkWaypoint,
  type CollectorObstacle,
  type ExclusionZone,
  type CollectorElementType,
  type SurveySessionPlan,
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
  type RawDataRecord,
} from '../../lib/collectorGrid'
import {
  canvasPctToMeters,
  metersToCanvasPct,
  type BuildingDimensions,
} from '../../lib/geometry'
import { type MapItem } from '../../lib/simulation'
import { type UserRole } from '../../lib/rbac'
import {
  M3Monitor,
  M3Collector,
  M3Grid,
  M3Download,
  M3Upload,
  M3Operations,
  M3Check,
  M3Trash,
  M3Info,
  M3Tag,
  M3Beacon,
  M3Walk,
  M3Wall,
  M3Bolt,
  M3Deploy,
  M3Reports,
} from '../common/MaterialIcon'

import { CollectorCollapsible } from './CollectorCollapsible'
import { CollectorDropdown } from './CollectorDropdown'

interface Props {
  buildingDims: BuildingDimensions
  schematicRooms: any[]
  schematicAnchors: any[]
  mapItems: MapItem[]
  role: UserRole
}

interface DragState {
  id: string
  type: CollectorElementType
  startX: number
  startY: number
  initialX: number
  initialY: number
}

export function CollectorView({
  buildingDims = { width: 10, height: 10, unit: 'meters' },
  schematicRooms = [],
  schematicAnchors = [],
  mapItems = [],
  role,
}: Props) {
  const svgRef = useRef<SVGSVGElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const dragRef = useRef<DragState | null>(null)

  // Session metadata
  const [sessionName, setSessionName] = useState('Calibration Survey Alpha')
  const [targetMac, setTargetMac] = useState('52:06:26:03:01:DA')
  const [dims, setDims] = useState<BuildingDimensions>(buildingDims)

  // Grid Configuration
  const [gridSpacingMeters, setGridSpacingMeters] = useState(1.0)
  const [snapToGrid, setSnapToGrid] = useState(true)
  const [showGrid, setShowGrid] = useState(true)
  const [showRulers, setShowRulers] = useState(true)
  const [showRangeRings, setShowRangeRings] = useState(true)
  const [showInterferenceZones, setShowInterferenceZones] = useState(true)
  const [showObstructionRays, setShowObstructionRays] = useState(true)
  const [showDimensions, setShowDimensions] = useState(true)
  const [showRooms, setShowRooms] = useState(true)
  const [showPath, setShowPath] = useState(true)

  // Multi-node highlights (e.g. within interference range)
  const [highlightedNodeIds, setHighlightedNodeIds] = useState<string[]>([])

  // Interactive Elements State (initialized with saved state or sensible initial setup)
  const [surveyPoints, setSurveyPoints] = useState<SurveyPoint[]>(() => {
    try {
      const saved = localStorage.getItem('rtls_collector_points')
      if (saved) return JSON.parse(saved)
    } catch {}
    // Default initial grid of 4 calibration points
    return [
      { id: 'SP_01', label: 'Point A (1.0m, 1.0m)', x: 10, y: 90, targetSamples: 300, collectedSamples: 300, status: 'completed', heightMeters: 1.0, motion: 'stationary' },
      { id: 'SP_02', label: 'Point B (3.0m, 1.0m)', x: 30, y: 90, targetSamples: 300, collectedSamples: 180, status: 'collecting', heightMeters: 1.0, motion: 'stationary' },
      { id: 'SP_03', label: 'Point C (5.0m, 5.0m)', x: 50, y: 50, targetSamples: 300, collectedSamples: 0, status: 'pending', heightMeters: 1.0, motion: 'stationary' },
      { id: 'SP_04', label: 'Point D (7.0m, 7.0m)', x: 70, y: 30, targetSamples: 300, collectedSamples: 0, status: 'pending', heightMeters: 1.0, motion: 'stationary' },
    ]
  })

  const [anchors, setAnchors] = useState<CollectorAnchor[]>(() => {
    try {
      const saved = localStorage.getItem('rtls_collector_anchors')
      if (saved) return JSON.parse(saved)
    } catch {}
    if (schematicAnchors && schematicAnchors.length > 0) {
      return schematicAnchors.map((a, idx) => ({
        id: a.id || `ANCHOR_${idx + 1}`,
        label: a.label || `Anchor ${idx + 1}`,
        systemName: a.systemName || a.label || `ESP32-Node-${idx + 1}`,
        macAddress: a.macAddress || `24:6F:28:1A:4C:0${(idx % 9) + 1}`,
        x: a.x,
        y: a.y,
        roomId: a.roomId,
        txPower: a.txPower || -60.0,
        channel: a.channel || 37 + (idx % 3),
        receptionRangeMeters: 8.0,
        port: `COM${3 + (idx % 4)}`,
        status: 'online',
      }))
    }
    return [
      { id: 'ANCHOR_01', label: 'ESP32 Anchor 1 (SW)', systemName: 'ESP-01 (South-West)', macAddress: '24:6F:28:1A:4C:01', x: 8, y: 92, txPower: -60.0, channel: 37, receptionRangeMeters: 8.0, port: 'COM3', status: 'online' },
      { id: 'ANCHOR_02', label: 'ESP32 Anchor 2 (SE)', systemName: 'ESP-02 (South-East)', macAddress: '24:6F:28:1A:4C:02', x: 92, y: 92, txPower: -60.0, channel: 38, receptionRangeMeters: 8.0, port: 'COM4', status: 'online' },
      { id: 'ANCHOR_03', label: 'ESP32 Anchor 3 (NW)', systemName: 'ESP-03 (North-West)', macAddress: '24:6F:28:1A:4C:03', x: 8, y: 8, txPower: -60.0, channel: 39, receptionRangeMeters: 8.0, port: 'COM5', status: 'online' },
      { id: 'ANCHOR_04', label: 'ESP32 Anchor 4 (NE)', systemName: 'ESP-04 (North-East)', macAddress: '24:6F:28:1A:4C:04', x: 92, y: 8, txPower: -60.0, channel: 37, receptionRangeMeters: 8.0, port: 'COM6', status: 'online' },
    ]
  })

  const [waypoints, setWaypoints] = useState<WalkWaypoint[]>(() => {
    try {
      const saved = localStorage.getItem('rtls_collector_waypoints')
      if (saved) return JSON.parse(saved)
    } catch {}
    return [
      { id: 'WP_01', label: 'Start (Lobby)', order: 1, x: 10, y: 90, speedMetersPerSec: 0.8, dwellTimeSec: 5 },
      { id: 'WP_02', label: 'Midway (Hub)', order: 2, x: 50, y: 50, speedMetersPerSec: 0.8, dwellTimeSec: 5 },
      { id: 'WP_03', label: 'Destination', order: 3, x: 90, y: 10, speedMetersPerSec: 0.8, dwellTimeSec: 10 },
    ]
  })

  const [obstacles, setObstacles] = useState<CollectorObstacle[]>(() => {
    try {
      const saved = localStorage.getItem('rtls_collector_obstacles')
      if (saved) return JSON.parse(saved)
    } catch {}
    return [
      { id: 'OBS_01', label: 'Drywall Partition', x: 48, y: 20, w: 4, h: 60, obstacleType: 'Drywall', attenuationDb: 4.8, interferenceRadiusMeters: 3.0 },
      { id: 'OBS_02', label: 'Metal Filing Cabinet', x: 20, y: 10, w: 10, h: 8, obstacleType: 'Metal', attenuationDb: 12.0, interferenceRadiusMeters: 4.5 },
    ]
  })

  // Selection and UI state
  const [selectedId, setSelectedId] = useState<string | null>('SP_01')
  const [selectedType, setSelectedType] = useState<CollectorElementType>('survey_point')
  const [cursorPos, setCursorPos] = useState<{ xPct: number; yPct: number; xM: number; yM: number } | null>(null)
  const [collectorDaemonStatus, setCollectorDaemonStatus] = useState<'ACTIVE' | 'OFFLINE'>('OFFLINE')
  const [isSimulating, setIsSimulating] = useState(false)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)

  // View Mode: DIY Survey Grid Planner vs. Raw Data Ingestion & Live Logger
  const [activeViewTab, setActiveViewTab] = useState<'planner' | 'logger'>('planner')

  // Zero-Transformation Raw Data Ingestion & Plain Text Log State
  const [rawRecords, setRawRecords] = useState<RawDataRecord[]>(() => {
    try {
      const saved = localStorage.getItem('rtls_raw_collector_records')
      if (saved) return JSON.parse(saved)
    } catch {}
    const now = new Date()
    const dStr = now.toISOString().split('T')[0]
    const tStr = now.toTimeString().split(' ')[0] + '.' + String(now.getMilliseconds()).padStart(3, '0')
    return [
      {
        id: 'rec_init_1',
        date: dStr,
        time: tStr,
        timestamp: Date.now() - 3200,
        anchorId: 'ESP32_01',
        deviceMac: '52:06:26:03:01:DA',
        rssi: -65,
        rawPayload: '1693800000,ESP32_01,52:06:26:03:01:DA,-65,ESP32_TAG',
      },
      {
        id: 'rec_init_2',
        date: dStr,
        time: tStr,
        timestamp: Date.now() - 2100,
        anchorId: 'ESP32_02',
        deviceMac: '52:06:26:03:01:DA',
        rssi: -71,
        rawPayload: '{"type":"raw","timestamp":1693800001,"mac":"52:06:26:03:01:DA","rssi":-71}',
      },
      {
        id: 'rec_init_3',
        date: dStr,
        time: tStr,
        timestamp: Date.now() - 1100,
        anchorId: 'ESP32_03',
        deviceMac: '52:06:26:03:01:DA',
        rssi: -58,
        rawPayload: '1693800002,ESP32_03,52:06:26:03:01:DA,-58,ESP32_TAG',
      },
      {
        id: 'rec_init_4',
        date: dStr,
        time: tStr,
        timestamp: Date.now(),
        anchorId: 'ESP32_04',
        deviceMac: '52:06:26:03:01:DA',
        rssi: -77,
        rawPayload: '{"type":"raw","timestamp":1693800003,"mac":"52:06:26:03:01:DA","rssi":-77}',
      },
    ]
  })

  const [rawLines, setRawLines] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem('rtls_raw_collector_lines')
      if (saved) return JSON.parse(saved)
    } catch {}
    return [
      '1693800000,ESP32_01,52:06:26:03:01:DA,-65,ESP32_TAG',
      '{"type":"raw","timestamp":1693800001,"mac":"52:06:26:03:01:DA","rssi":-71}',
      '1693800002,ESP32_03,52:06:26:03:01:DA,-58,ESP32_TAG',
      '{"type":"raw","timestamp":1693800003,"mac":"52:06:26:03:01:DA","rssi":-77}',
    ]
  })

  const [isLiveStreaming, setIsLiveStreaming] = useState(true)
  const [anchorFilter, setAnchorFilter] = useState<string>('ALL')
  const [autoScrollConsole, setAutoScrollConsole] = useState(true)
  const consoleRef = useRef<HTMLDivElement>(null)

  // Persist state
  useEffect(() => {
    localStorage.setItem('rtls_collector_points', JSON.stringify(surveyPoints))
    localStorage.setItem('rtls_collector_anchors', JSON.stringify(anchors))
    localStorage.setItem('rtls_collector_waypoints', JSON.stringify(waypoints))
    localStorage.setItem('rtls_collector_obstacles', JSON.stringify(obstacles))
    localStorage.setItem('rtls_raw_collector_records', JSON.stringify(rawRecords))
    localStorage.setItem('rtls_raw_collector_lines', JSON.stringify(rawLines))
  }, [surveyPoints, anchors, waypoints, obstacles, rawRecords, rawLines])

  // Live Raw Ingestion Telemetry Poller & Generator
  useEffect(() => {
    if (!isLiveStreaming) return
    const interval = setInterval(async () => {
      // 1. Try polling backend /api/collector/records
      try {
        const res = await fetch('/api/collector/records?limit=50')
        if (res.ok) {
          const data = await res.json()
          if (data?.records && data.records.length > 0) {
            setRawRecords((prev) => {
              const existingIds = new Set(prev.map((r) => r.id))
              const newRecs = data.records.filter((r: RawDataRecord) => !existingIds.has(r.id))
              if (newRecs.length > 0) {
                return [...newRecs, ...prev].slice(0, 1000)
              }
              return prev
            })
            if (data?.raw_lines && data.raw_lines.length > 0) {
              setRawLines((prev) => {
                const uniqueNewLines = data.raw_lines.slice(-50)
                return Array.from(new Set([...uniqueNewLines, ...prev])).slice(0, 1000)
              })
            }
            return
          }
        }
      } catch {}

      // 2. If simulation active or hardware collector daemon active, generate continuous live raw line
      if (isSimulating || collectorDaemonStatus === 'ACTIVE') {
        const targetAnchor = anchors[Math.floor(Math.random() * anchors.length)] || {
          id: 'ESP32_01',
          macAddress: '24:6F:28:1A:4C:01',
          systemName: 'ESP-01',
        }
        const now = new Date()
        const dStr = now.toISOString().split('T')[0]
        const tStr = now.toTimeString().split(' ')[0] + '.' + String(now.getMilliseconds()).padStart(3, '0')
        const rawRssi = -Math.floor(48 + Math.random() * 38)
        const ts = Date.now()
        const useJson = Math.random() > 0.4
        const payload = useJson
          ? JSON.stringify({ type: 'raw', timestamp: ts, mac: targetMac, rssi: rawRssi })
          : `${ts},${targetAnchor.id},${targetMac},${rawRssi},ESP_NODE`

        const newRec: RawDataRecord = {
          id: `rec_${ts}_${Math.random().toString(36).substring(2, 6)}`,
          date: dStr,
          time: tStr,
          timestamp: ts,
          anchorId: targetAnchor.id,
          deviceMac: targetMac,
          rssi: rawRssi,
          rawPayload: payload,
        }

        setRawRecords((prev) => [newRec, ...prev].slice(0, 1000))
        setRawLines((prev) => [payload, ...prev].slice(0, 1000))
      }
    }, 1500)

    return () => clearInterval(interval)
  }, [isLiveStreaming, isSimulating, collectorDaemonStatus, anchors, targetMac])

  // Auto-scroll plain text console
  useEffect(() => {
    if (autoScrollConsole && consoleRef.current) {
      consoleRef.current.scrollTop = 0
    }
  }, [rawLines, autoScrollConsole])

  // Fetch collector daemon status from server
  useEffect(() => {
    fetch('/api/state')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.services?.collector?.status === 'ACTIVE') {
          setCollectorDaemonStatus('ACTIVE')
        }
      })
      .catch(() => {})
  }, [])

  // Simulated collection progress tick
  useEffect(() => {
    if (!isSimulating) return
    const iv = setInterval(() => {
      setSurveyPoints((prev) => {
        const next = [...prev]
        const target = next.find((p) => p.status === 'collecting') || next.find((p) => p.status === 'pending')
        if (target) {
          target.status = 'collecting'
          target.collectedSamples = Math.min(target.targetSamples, target.collectedSamples + 15)
          if (target.collectedSamples >= target.targetSamples) {
            target.status = 'completed'
          }
        } else {
          setIsSimulating(false)
        }
        return next
      })
    }, 400)
    return () => clearInterval(iv)
  }, [isSimulating])

  // Coordinate Conversion Helper with snap
  const getCanvasCoords = (clientX: number, clientY: number) => {
    if (!svgRef.current) return { x: 50, y: 50 }
    const rect = svgRef.current.getBoundingClientRect()
    let xPct = Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100))
    let yPct = Math.max(0, Math.min(100, ((clientY - rect.top) / rect.height) * 100))

    if (snapToGrid) {
      const stepPctX = (gridSpacingMeters / dims.width) * 100
      const stepPctY = (gridSpacingMeters / dims.height) * 100
      xPct = Math.round(xPct / stepPctX) * stepPctX
      yPct = Math.round(yPct / stepPctY) * stepPctY
    }

    return {
      x: Math.round(xPct * 10) / 10,
      y: Math.round(yPct * 10) / 10,
    }
  }

  // Mouse Movement on Canvas
  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!svgRef.current) return
    const rect = svgRef.current.getBoundingClientRect()
    const rawXPct = Math.max(0, Math.min(100, ((e.clientX - rect.left) / rect.width) * 100))
    const rawYPct = Math.max(0, Math.min(100, ((e.clientY - rect.top) / rect.height) * 100))
    const meters = canvasPctToMeters(rawXPct, rawYPct, dims, 'bottom-left')

    setCursorPos({
      xPct: Math.round(rawXPct * 10) / 10,
      yPct: Math.round(rawYPct * 10) / 10,
      xM: Math.round(meters.x * 100) / 100,
      yM: Math.round(meters.y * 100) / 100,
    })

    if (!dragRef.current) return

    const { x, y } = getCanvasCoords(e.clientX, e.clientY)
    const { id, type } = dragRef.current

    if (type === 'survey_point') {
      setSurveyPoints((prev) => prev.map((p) => (p.id === id ? { ...p, x, y } : p)))
    } else if (type === 'anchor') {
      setAnchors((prev) => prev.map((a) => (a.id === id ? { ...a, x, y } : a)))
    } else if (type === 'waypoint') {
      setWaypoints((prev) => prev.map((w) => (w.id === id ? { ...w, x, y } : w)))
    } else if (type === 'obstacle') {
      setObstacles((prev) => prev.map((o) => (o.id === id ? { ...o, x, y } : o)))
    }
  }

  const handleMouseUp = () => {
    dragRef.current = null
  }

  const handleStartDrag = (id: string, type: CollectorElementType, e: React.MouseEvent) => {
    e.stopPropagation()
    setSelectedId(id)
    setSelectedType(type)
    dragRef.current = {
      id,
      type,
      startX: e.clientX,
      startY: e.clientY,
      initialX: 0,
      initialY: 0,
    }
  }

  // Element Creation
  const handleAddElement = (type: CollectorElementType) => {
    const cx = 50
    const cy = 50
    if (type === 'survey_point') {
      const newId = `SP_${String(surveyPoints.length + 1).padStart(2, '0')}`
      const newPt: SurveyPoint = {
        id: newId,
        label: `Survey Point ${surveyPoints.length + 1}`,
        x: cx,
        y: cy,
        targetSamples: 300,
        collectedSamples: 0,
        status: 'pending',
        heightMeters: 1.0,
        motion: 'stationary',
      }
      setSurveyPoints((prev) => [...prev, newPt])
      setSelectedId(newId)
      setSelectedType('survey_point')
    } else if (type === 'anchor') {
      const newId = `ANCHOR_${String(anchors.length + 1).padStart(2, '0')}`
      const newAnchor: CollectorAnchor = {
        id: newId,
        label: `ESP32 Anchor ${anchors.length + 1}`,
        systemName: `ESP-${String(anchors.length + 1).padStart(2, '0')} (Node)`,
        macAddress: `24:6F:28:1A:4C:${String(anchors.length + 1).padStart(2, '0')}`,
        x: cx,
        y: cy,
        txPower: -60.0,
        channel: 37 + (anchors.length % 3),
        receptionRangeMeters: 8.0,
        port: `COM${3 + (anchors.length % 4)}`,
        status: 'online',
      }
      setAnchors((prev) => [...prev, newAnchor])
      setSelectedId(newId)
      setSelectedType('anchor')
    } else if (type === 'waypoint') {
      const newId = `WP_${String(waypoints.length + 1).padStart(2, '0')}`
      const newWp: WalkWaypoint = {
        id: newId,
        label: `Waypoint ${waypoints.length + 1}`,
        order: waypoints.length + 1,
        x: cx,
        y: cy,
        speedMetersPerSec: 0.8,
        dwellTimeSec: 5,
      }
      setWaypoints((prev) => [...prev, newWp])
      setSelectedId(newId)
      setSelectedType('waypoint')
    } else if (type === 'obstacle') {
      const newId = `OBS_${String(obstacles.length + 1).padStart(2, '0')}`
      const newObs: CollectorObstacle = {
        id: newId,
        label: `Obstacle ${obstacles.length + 1}`,
        x: cx,
        y: cy,
        w: 12,
        h: 4,
        obstacleType: 'Drywall',
        attenuationDb: 4.8,
        interferenceRadiusMeters: 3.5,
      }
      setObstacles((prev) => [...prev, newObs])
      setSelectedId(newId)
      setSelectedType('obstacle')
    }
  }

  // Delete Selected Element
  const handleDeleteSelected = () => {
    if (!selectedId) return
    if (selectedType === 'survey_point') {
      setSurveyPoints((prev) => prev.filter((p) => p.id !== selectedId))
    } else if (selectedType === 'anchor') {
      setAnchors((prev) => prev.filter((a) => a.id !== selectedId))
    } else if (selectedType === 'waypoint') {
      setWaypoints((prev) => prev.filter((w) => w.id !== selectedId))
    } else if (selectedType === 'obstacle') {
      setObstacles((prev) => prev.filter((o) => o.id !== selectedId))
    }
    setSelectedId(null)
  }

  // Auto-Grid Generator: generates uniform grid over room or facility
  const handleGenerateGrid = (roomOnly: boolean = false) => {
    let bounds = { x: 0, y: 0, w: 100, h: 100 }
    let roomId: string | undefined = undefined

    if (roomOnly && schematicRooms.length > 0) {
      const room = schematicRooms[0]
      bounds = { x: room.x, y: room.y, w: room.w, h: room.h }
      roomId = room.id
    }

    const generated = generateUniformGrid(bounds, gridSpacingMeters, dims, {
      roomId,
      prefix: 'SURVEY',
      marginMeters: 0.5,
      targetSamples: 300,
    })

    setSurveyPoints(generated)
    if (generated.length > 0) {
      setSelectedId(generated[0].id)
      setSelectedType('survey_point')
    }
    setStatusMessage(`Generated uniform survey grid with ${generated.length} test points at ${gridSpacingMeters}m spacing.`)
    setTimeout(() => setStatusMessage(null), 4000)
  }

  // Route Optimizer: Shortest Walking Path
  const handleOptimizeRoute = () => {
    if (surveyPoints.length < 2) return
    const optimized = optimizeSurveyPath(surveyPoints, dims)
    setSurveyPoints(optimized)
    const lengthM = calculatePathLength(optimized, dims)
    setStatusMessage(`Route optimized! Shortest survey path length: ${lengthM}m across ${optimized.length} points.`)
    setTimeout(() => setStatusMessage(null), 4000)
  }

  // Quick 4-ESP Setup Wizard
  const handleSetupFourEspPreset = () => {
    const preset = getFourEspAnchorPreset(dims)
    setAnchors(preset)
    setSelectedId(preset[0].id)
    setSelectedType('anchor')
    setStatusMessage(`Configured 4-ESP anchor network with MAC addresses and system names across ${dims.width}m × ${dims.height}m grid.`)
    setTimeout(() => setStatusMessage(null), 4000)
  }

  // Deploy All Anchors & Broadcast to Engine via /api/schematic
  const handleDeployAndBroadcastAnchors = async () => {
    try {
      const schematicData = {
        name: sessionName,
        dimensions: { width: dims.width, height: dims.height, depth: 3.2, unit: 'meters' },
        anchors: anchors.map((a) => {
          const m = canvasPctToMeters(a.x, a.y, dims, 'bottom-left')
          return {
            id: a.id,
            label: a.label,
            mac: a.macAddress || '',
            name: a.systemName || a.label,
            x: Math.round(m.x * 100) / 100,
            y: Math.round(m.y * 100) / 100,
            channel: a.channel,
            tx_power: a.txPower,
            range_m: a.receptionRangeMeters,
          }
        }),
        rooms: schematicRooms,
        walls: obstacles.map((o) => ({
          id: o.id,
          kind: 'wall',
          label: o.label,
          x: o.x,
          y: o.y,
          w: o.w,
          h: o.h,
          attenuation: o.attenuationDb,
        })),
      }

      const res = await fetch('/api/schematic', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(schematicData),
      })

      if (res.ok) {
        setStatusMessage(`Successfully broadcasted ${anchors.length} ESP anchors to engine! MAC addresses & names live in WebSocket feed.`)
      } else {
        setStatusMessage(`Saved anchors locally. Server responded with ${res.status}.`)
      }
    } catch {
      setStatusMessage('Deployed anchors locally in dashboard storage.')
    }
    setTimeout(() => setStatusMessage(null), 4000)
  }

  // Deploy Single Anchor via /api/config/anchors
  const handleDeploySingleAnchor = async (anc: CollectorAnchor) => {
    const m = canvasPctToMeters(anc.x, anc.y, dims, 'bottom-left')
    try {
      const res = await fetch('/api/config/anchors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          anchor_id: anc.id,
          x: Math.round(m.x * 100) / 100,
          y: Math.round(m.y * 100) / 100,
          mac: anc.macAddress || '',
          name: anc.systemName || anc.label,
        }),
      })
      if (res.ok) {
        setStatusMessage(`Anchor ${anc.id} (${anc.systemName || anc.label}) deployed and broadcasted to engine.`)
      } else {
        setStatusMessage(`Updated anchor ${anc.id} locally.`)
      }
    } catch {
      setStatusMessage(`Updated anchor ${anc.id} locally.`)
    }
    setTimeout(() => setStatusMessage(null), 4000)
  }

  // Hardware Collector Control
  const handleToggleCollectorDaemon = async () => {
    const act = collectorDaemonStatus === 'ACTIVE' ? 'stop_collector' : 'start_collector'
    try {
      const res = await fetch('/api/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: act }),
      })
      if (res.ok) {
        setCollectorDaemonStatus(collectorDaemonStatus === 'ACTIVE' ? 'OFFLINE' : 'ACTIVE')
        setStatusMessage(collectorDaemonStatus === 'ACTIVE' ? 'Physical collector daemon stopped.' : 'Physical sensor collector daemon active on USB ports.')
        setTimeout(() => setStatusMessage(null), 4000)
      }
    } catch {
      // Local fallback
      setCollectorDaemonStatus(collectorDaemonStatus === 'ACTIVE' ? 'OFFLINE' : 'ACTIVE')
    }
  }

  // Export Plan to JSON
  const handleExportPlan = () => {
    const plan: SurveySessionPlan = {
      id: `SURVEY_${Date.now()}`,
      name: sessionName,
      targetMac,
      buildingDimensions: dims,
      gridSpacingMeters,
      maxAllocatedSpace: { width: dims.width, height: dims.height },
      surveyPoints,
      anchors,
      waypoints,
      obstacles,
      exclusions: [],
      createdAt: new Date().toISOString(),
    }
    const jsonStr = formatCollectorExport(plan)
    const blob = new Blob([jsonStr], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `survey_session_${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  // Zero-Transformation Export: Data Sheet (.csv)
  const handleExportDataSheet = () => {
    const csvContent = formatDataSheetCsv(rawRecords)
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `raw_datasheet_${Date.now()}.csv`
    a.click()
    URL.revokeObjectURL(url)
    setStatusMessage(`Exported raw data sheet with ${rawRecords.length} records. Date is date, time is time, RSSI is raw.`)
    setTimeout(() => setStatusMessage(null), 3000)
  }

  // Zero-Transformation Export: Plain Text Log (.log)
  const handleExportPlainTextLog = () => {
    const textContent = formatPlainTextLog(rawLines)
    const blob = new Blob([textContent], { type: 'text/plain;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `raw_stream_${Date.now()}.log`
    a.click()
    URL.revokeObjectURL(url)
    setStatusMessage(`Exported verbatim plain text node log with ${rawLines.length} lines.`)
    setTimeout(() => setStatusMessage(null), 3000)
  }

  // Copy Plain Text Log
  const handleCopyPlainTextLog = () => {
    const textContent = formatPlainTextLog(rawLines)
    navigator.clipboard.writeText(textContent)
    setStatusMessage('Copied verbatim plain text node stream to clipboard.')
    setTimeout(() => setStatusMessage(null), 3000)
  }

  // Clear Raw Ingestion Buffer
  const handleClearRawBuffer = async () => {
    setRawRecords([])
    setRawLines([])
    localStorage.removeItem('rtls_raw_collector_records')
    localStorage.removeItem('rtls_raw_collector_lines')
    try {
      await fetch('/api/collector/clear', { method: 'POST' })
    } catch {}
    setStatusMessage('Cleared raw data sheet and plain text log buffer.')
    setTimeout(() => setStatusMessage(null), 3000)
  }

  // Inject Raw Sample Packet (Zero Filter)
  const handleInjectSamplePacket = () => {
    const targetAnchor = anchors[Math.floor(Math.random() * anchors.length)] || {
      id: 'ESP32_01',
      macAddress: '24:6F:28:1A:4C:01',
      systemName: 'ESP-01',
    }
    const now = new Date()
    const dStr = now.toISOString().split('T')[0]
    const tStr = now.toTimeString().split(' ')[0] + '.' + String(now.getMilliseconds()).padStart(3, '0')
    const rawRssi = -Math.floor(52 + Math.random() * 32)
    const ts = Date.now()
    const useJson = Math.random() > 0.5
    const payload = useJson
      ? JSON.stringify({ type: 'raw', timestamp: ts, mac: targetMac, rssi: rawRssi })
      : `${ts},${targetAnchor.id},${targetMac},${rawRssi},ESP_NODE`

    const newRec: RawDataRecord = {
      id: `rec_${ts}_${Math.random().toString(36).substring(2, 6)}`,
      date: dStr,
      time: tStr,
      timestamp: ts,
      anchorId: targetAnchor.id,
      deviceMac: targetMac,
      rssi: rawRssi,
      rawPayload: payload,
    }

    setRawRecords((prev) => [newRec, ...prev].slice(0, 1000))
    setRawLines((prev) => [payload, ...prev].slice(0, 1000))
    setStatusMessage(`Captured new raw packet from ${targetAnchor.id} (RSSI: ${rawRssi} dBm).`)
    setTimeout(() => setStatusMessage(null), 2500)
  }

  // Filtered records for Data Sheet viewer
  const filteredRecords = anchorFilter === 'ALL'
    ? rawRecords
    : rawRecords.filter((r) => r.anchorId === anchorFilter)

  // Find Selected Items
  const selectedPoint = surveyPoints.find((p) => p.id === selectedId)
  const selectedAnchor = anchors.find((a) => a.id === selectedId)
  const selectedWaypoint = waypoints.find((w) => w.id === selectedId)
  const selectedObstacle = obstacles.find((o) => o.id === selectedId)

  // Computed distances for selected point
  const anchorDistances = selectedPoint
    ? computeAnchorDistances(selectedPoint, anchors, dims)
    : []

  // Calculated walking length
  const totalPathMeters = calculatePathLength(surveyPoints, dims)

  // Import Survey Plan JSON
  const handleImportPlan = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (evt) => {
      try {
        const json = JSON.parse(evt.target?.result as string)
        if (json.surveyPoints) setSurveyPoints(json.surveyPoints)
        if (json.anchors) setAnchors(json.anchors)
        if (json.obstacles) setObstacles(json.obstacles)
        if (json.dims) setDims(json.dims)
        setStatusMessage('Successfully imported survey plan JSON.')
        setTimeout(() => setStatusMessage(null), 3000)
      } catch (err) {
        setStatusMessage('Failed to parse survey plan JSON file.')
        setTimeout(() => setStatusMessage(null), 3000)
      }
    }
    reader.readAsText(file)
  }


  return (
    <div className="space-y-4">
      {/* Hidden File Input for Plan Import */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleImportPlan}
        accept=".json"
        className="hidden"
      />

      {/* 1. Sleek Command & Action Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-card p-3 shadow-sm border border-border/40">
        {/* Left: App Title & Mode Switcher */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 pr-2 border-r border-border/40">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-teal-500/15 text-teal-600 dark:text-teal-400">
              <M3Collector size={18} />
            </div>
            <div>
              <div className="text-xs font-bold text-foreground leading-tight">BLE Studio</div>
              <div className="text-[10px] text-muted-foreground font-mono">
                {dims.width}×{dims.height}m • {gridSpacingMeters}m
              </div>
            </div>
          </div>

          {/* Mode Switcher Tabs */}
          <div className="flex items-center gap-1 bg-muted/40 p-1 rounded-xl text-xs font-semibold">
            <button
              type="button"
              onClick={() => setActiveViewTab('planner')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                activeViewTab === 'planner'
                  ? 'bg-teal-600 text-white shadow-xs'
                  : 'hover:bg-muted text-muted-foreground hover:text-foreground'
              }`}
            >
              <M3Grid size={15} />
              <span>Survey Planner</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveViewTab('logger')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                activeViewTab === 'logger'
                  ? 'bg-teal-600 text-white shadow-xs'
                  : 'hover:bg-muted text-muted-foreground hover:text-foreground'
              }`}
            >
              <M3Reports size={15} />
              <span>Raw Ingestion</span>
              <span
                className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono font-bold ${
                  activeViewTab === 'logger'
                    ? 'bg-white/25 text-white'
                    : 'bg-muted text-muted-foreground'
                }`}
              >
                {rawRecords.length}
              </span>
            </button>
          </div>
        </div>

        {/* Right: Cascades & Dropdowns */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Quick Presets Cascading Dropdown */}
          <CollectorDropdown
            align="right"
            items={[
              {
                id: 'preset_5x5',
                label: '5m × 5m Compact Room (1m interval)',
                icon: <M3Grid size={14} />,
                onClick: () => {
                  setDims({ width: 5, height: 5, unit: 'meters' })
                  setGridSpacingMeters(1.0)
                  setStatusMessage('Configured 5m × 5m room with 1.0m intervals.')
                  setTimeout(() => setStatusMessage(null), 3000)
                },
              },
              {
                id: 'preset_10x10_2m',
                label: '10m × 10m Standard Hall (2m interval)',
                icon: <M3Grid size={14} />,
                onClick: () => {
                  setDims({ width: 10, height: 10, unit: 'meters' })
                  setGridSpacingMeters(2.0)
                  setStatusMessage('Configured 10m × 10m hall with 2.0m intervals.')
                  setTimeout(() => setStatusMessage(null), 3000)
                },
              },
              {
                id: 'preset_10x10_1m',
                label: '10m × 10m Standard Hall (1m interval)',
                icon: <M3Grid size={14} />,
                onClick: () => {
                  setDims({ width: 10, height: 10, unit: 'meters' })
                  setGridSpacingMeters(1.0)
                  setStatusMessage('Configured 10m × 10m hall with 1.0m intervals.')
                  setTimeout(() => setStatusMessage(null), 3000)
                },
              },
              {
                id: 'preset_15x10',
                label: '15m × 10m Facility Suite (1m interval)',
                icon: <M3Grid size={14} />,
                onClick: () => {
                  setDims({ width: 15, height: 10, unit: 'meters' })
                  setGridSpacingMeters(1.0)
                  setStatusMessage('Configured 15m × 10m suite with 1.0m intervals.')
                  setTimeout(() => setStatusMessage(null), 3000)
                },
              },
              {
                id: 'preset_hardware_nodes',
                label: 'ESP Hardware Presets',
                icon: <M3Beacon size={14} />,
                subItems: [
                  {
                    id: 'sub_flash_4_esps',
                    label: '⚡ Auto-Place 4 Corner ESPs',
                    icon: <M3Beacon size={14} />,
                    onClick: handleSetupFourEspPreset,
                  },
                  {
                    id: 'sub_broadcast_anchors',
                    label: '📡 Broadcast Anchors to Core Engine',
                    icon: <M3Deploy size={14} />,
                    onClick: handleDeployAndBroadcastAnchors,
                  },
                ],
              },
            ]}
            trigger={(isOpen) => (
              <button
                type="button"
                className={`flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer select-none ${
                  isOpen ? 'bg-muted text-foreground' : 'bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground'
                }`}
              >
                <M3Grid size={14} />
                <span>Presets</span>
                <span className="text-[10px] opacity-60">▼</span>
              </button>
            )}
          />

          {/* Canvas Actions Cascading Dropdown */}
          <CollectorDropdown
            align="right"
            items={[
              {
                id: 'act_optimize_route',
                label: 'Optimize Shortest Route (TSP)',
                icon: <M3Operations size={14} />,
                badge: `${totalPathMeters}m`,
                onClick: handleOptimizeRoute,
              },
              {
                id: 'act_auto_grid',
                label: `Auto-Grid Entire Facility (${gridSpacingMeters}m)`,
                icon: <M3Grid size={14} />,
                onClick: () => handleGenerateGrid(false),
              },
              ...(schematicRooms.length > 0
                ? [
                    {
                      id: 'act_auto_grid_room',
                      label: 'Auto-Grid Selected Room',
                      icon: <M3Grid size={14} />,
                      onClick: () => handleGenerateGrid(true),
                    },
                  ]
                : []),
              {
                id: 'act_simulate_walk',
                label: isSimulating ? 'Stop Survey Simulation' : 'Start Survey Simulation',
                icon: <M3Bolt size={14} />,
                onClick: () => setIsSimulating(!isSimulating),
              },
              {
                id: 'act_daemon_toggle',
                label: collectorDaemonStatus === 'ACTIVE' ? 'Daemon: Stop Collector' : 'Daemon: Start Collector',
                icon: <M3Collector size={14} />,
                onClick: handleToggleCollectorDaemon,
              },
              {
                id: 'act_clear_points',
                label: 'Clear All Survey Points',
                icon: <M3Trash size={14} />,
                danger: true,
                onClick: () => {
                  setSurveyPoints([])
                  setWaypoints([])
                  setSelectedId(null)
                  setHighlightedNodeIds([])
                },
              },
              {
                id: 'act_clear_obstacles',
                label: 'Clear All Obstacles',
                icon: <M3Trash size={14} />,
                danger: true,
                onClick: () => {
                  setObstacles([])
                  setSelectedId(null)
                },
              },
              {
                id: 'act_reset_all',
                label: 'Reset Entire Canvas',
                icon: <M3Trash size={14} />,
                danger: true,
                onClick: () => {
                  setSurveyPoints([])
                  setAnchors([])
                  setObstacles([])
                  setWaypoints([])
                  setSelectedId(null)
                  setHighlightedNodeIds([])
                },
              },
            ]}
            trigger={(isOpen) => (
              <button
                type="button"
                className={`flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer select-none ${
                  isOpen ? 'bg-muted text-foreground' : 'bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground'
                }`}
              >
                <M3Operations size={14} />
                <span>Actions</span>
                <span className="text-[10px] opacity-60">▼</span>
              </button>
            )}
          />

          {/* Layer Visibility Toggle Popover */}
          <CollectorDropdown
            align="right"
            trigger={(isOpen) => (
              <button
                type="button"
                className={`flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer select-none ${
                  isOpen ? 'bg-muted text-foreground' : 'bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground'
                }`}
              >
                <M3Monitor size={14} />
                <span>Layers</span>
                <span className="text-[10px] opacity-60">▼</span>
              </button>
            )}
          >
            {() => (
              <div className="w-56 p-2 space-y-2 text-xs">
                <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground pb-1 border-b border-border/40">
                  Visible Canvas Layers
                </div>
                <div className="space-y-1.5">
                  <label className="flex items-center justify-between p-1.5 rounded-lg hover:bg-muted/50 cursor-pointer">
                    <span className="font-medium">Metric Grid</span>
                    <input
                      type="checkbox"
                      checked={showGrid}
                      onChange={(e) => setShowGrid(e.target.checked)}
                      className="rounded text-teal-600 focus:ring-teal-500"
                    />
                  </label>
                  <label className="flex items-center justify-between p-1.5 rounded-lg hover:bg-muted/50 cursor-pointer">
                    <span className="font-medium">Metric Rulers</span>
                    <input
                      type="checkbox"
                      checked={showRulers}
                      onChange={(e) => setShowRulers(e.target.checked)}
                      className="rounded text-teal-600 focus:ring-teal-500"
                    />
                  </label>
                  <label className="flex items-center justify-between p-1.5 rounded-lg hover:bg-muted/50 cursor-pointer">
                    <span className="font-medium">Range Rings</span>
                    <input
                      type="checkbox"
                      checked={showRangeRings}
                      onChange={(e) => setShowRangeRings(e.target.checked)}
                      className="rounded text-teal-600 focus:ring-teal-500"
                    />
                  </label>
                  <label className="flex items-center justify-between p-1.5 rounded-lg hover:bg-muted/50 cursor-pointer">
                    <span className="font-medium">Interference Zones</span>
                    <input
                      type="checkbox"
                      checked={showInterferenceZones}
                      onChange={(e) => setShowInterferenceZones(e.target.checked)}
                      className="rounded text-teal-600 focus:ring-teal-500"
                    />
                  </label>
                  <label className="flex items-center justify-between p-1.5 rounded-lg hover:bg-muted/50 cursor-pointer">
                    <span className="font-medium">LoS Obstruction Rays</span>
                    <input
                      type="checkbox"
                      checked={showObstructionRays}
                      onChange={(e) => setShowObstructionRays(e.target.checked)}
                      className="rounded text-teal-600 focus:ring-teal-500"
                    />
                  </label>
                  <label className="flex items-center justify-between p-1.5 rounded-lg hover:bg-muted/50 cursor-pointer">
                    <span className="font-medium">Node Distances</span>
                    <input
                      type="checkbox"
                      checked={showDimensions}
                      onChange={(e) => setShowDimensions(e.target.checked)}
                      className="rounded text-teal-600 focus:ring-teal-500"
                    />
                  </label>
                  <label className="flex items-center justify-between p-1.5 rounded-lg hover:bg-muted/50 cursor-pointer">
                    <span className="font-medium">Room Shells</span>
                    <input
                      type="checkbox"
                      checked={showRooms}
                      onChange={(e) => setShowRooms(e.target.checked)}
                      className="rounded text-teal-600 focus:ring-teal-500"
                    />
                  </label>
                  <label className="flex items-center justify-between p-1.5 rounded-lg hover:bg-muted/50 cursor-pointer">
                    <span className="font-medium">Survey Walk Path</span>
                    <input
                      type="checkbox"
                      checked={showPath}
                      onChange={(e) => setShowPath(e.target.checked)}
                      className="rounded text-teal-600 focus:ring-teal-500"
                    />
                  </label>
                </div>
              </div>
            )}
          </CollectorDropdown>

          {/* Export & Import Cascading Dropdown */}
          <CollectorDropdown
            align="right"
            items={[
              {
                id: 'exp_plan_json',
                label: 'Export Survey Plan (.json)',
                icon: <M3Download size={14} />,
                onClick: handleExportPlan,
              },
              {
                id: 'imp_plan_json',
                label: 'Import Survey Plan (.json)',
                icon: <M3Upload size={14} />,
                onClick: () => fileInputRef.current?.click(),
              },
              {
                id: 'exp_raw_csv',
                label: 'Export Raw Data Sheet (.csv)',
                icon: <M3Download size={14} />,
                onClick: handleExportDataSheet,
              },
              {
                id: 'exp_raw_log',
                label: 'Export Plain Text Log (.log)',
                icon: <M3Download size={14} />,
                onClick: handleExportPlainTextLog,
              },
              {
                id: 'copy_raw_log',
                label: 'Copy Plain Text Log to Clipboard',
                icon: <M3Check size={14} />,
                onClick: handleCopyPlainTextLog,
              },
            ]}
            trigger={(isOpen) => (
              <button
                type="button"
                className="flex items-center gap-1.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white px-3 py-1.5 text-xs font-semibold transition-all shadow-xs cursor-pointer select-none"
              >
                <M3Download size={14} />
                <span>Export / Import</span>
                <span className="text-[10px] opacity-70">▼</span>
              </button>
            )}
          />
        </div>
      </div>

      {/* Status banner */}
      {statusMessage && (
        <div className="flex items-center gap-2 rounded-xl bg-teal-500/10 px-3.5 py-2 text-xs font-medium text-teal-700 dark:text-teal-300 animate-in fade-in duration-200">
          <M3Check size={16} />
          {statusMessage}
        </div>
      )}


      {/* TAB A: INTERACTIVE SURVEY PLANNER */}
      {activeViewTab === 'planner' && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">

        {/* Left Column: Element Library, Geometry & Workflow Accordions */}
        <div className="space-y-3 lg:col-span-3">
          {/* Card 1: Element Palette */}
          <CollectorCollapsible
            title="Element Library"
            icon={<M3Tag size={16} />}
            defaultOpen={true}
          >
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => handleAddElement('survey_point')}
                className="flex flex-col items-center justify-center p-2.5 rounded-xl bg-muted/30 hover:bg-teal-500/10 hover:text-teal-600 transition-all text-xs font-semibold gap-1 text-center cursor-pointer"
              >
                <M3Tag size={18} className="text-teal-600" />
                <span>Survey Point</span>
              </button>
              <button
                type="button"
                onClick={() => handleAddElement('anchor')}
                className="flex flex-col items-center justify-center p-2.5 rounded-xl bg-muted/30 hover:bg-teal-500/10 hover:text-teal-600 transition-all text-xs font-semibold gap-1 text-center cursor-pointer"
              >
                <M3Beacon size={18} className="text-teal-600" />
                <span>Receiver Anchor</span>
              </button>
              <button
                type="button"
                onClick={() => handleAddElement('waypoint')}
                className="flex flex-col items-center justify-center p-2.5 rounded-xl bg-muted/30 hover:bg-emerald-500/10 hover:text-emerald-600 transition-all text-xs font-semibold gap-1 text-center cursor-pointer"
              >
                <M3Walk size={18} className="text-emerald-600" />
                <span>Walk Waypoint</span>
              </button>
              <button
                type="button"
                onClick={() => handleAddElement('obstacle')}
                className="flex flex-col items-center justify-center p-2.5 rounded-xl bg-muted/30 hover:bg-amber-500/10 hover:text-amber-600 transition-all text-xs font-semibold gap-1 text-center cursor-pointer"
              >
                <M3Wall size={18} className="text-amber-600" />
                <span>Obstacle Barrier</span>
              </button>
            </div>
          </CollectorCollapsible>

          {/* Card 2: Room Geometry & Grid Subdivision */}
          <CollectorCollapsible
            title="Room Geometry & Grid"
            icon={<M3Grid size={16} />}
            defaultOpen={true}
            badge={<span className="text-[10px] font-mono text-teal-600 font-bold">{dims.width}×{dims.height}m</span>}
          >
            <div className="space-y-3 text-xs">
              {/* Width x Height Custom Inputs */}
              <div>
                <label className="text-[11px] font-semibold text-muted-foreground block mb-1">Room Dimensions (Meters)</label>
                <div className="flex items-center gap-2">
                  <div className="flex-1">
                    <span className="text-[10px] text-muted-foreground block">Width (X)</span>
                    <input
                      type="number"
                      min="1"
                      max="50"
                      step="0.5"
                      value={dims.width}
                      onChange={(e) => setDims({ ...dims, width: Math.max(1, Number(e.target.value)) })}
                      className="w-full rounded-xl bg-muted/40 px-2.5 py-1.5 font-mono text-center font-bold text-foreground focus:ring-2 focus:ring-accent"
                    />
                  </div>
                  <span className="text-muted-foreground font-bold mt-4">×</span>
                  <div className="flex-1">
                    <span className="text-[10px] text-muted-foreground block">Height (Y)</span>
                    <input
                      type="number"
                      min="1"
                      max="50"
                      step="0.5"
                      value={dims.height}
                      onChange={(e) => setDims({ ...dims, height: Math.max(1, Number(e.target.value)) })}
                      className="w-full rounded-xl bg-muted/40 px-2.5 py-1.5 font-mono text-center font-bold text-foreground focus:ring-2 focus:ring-accent"
                    />
                  </div>
                </div>
              </div>

              {/* Grid Subdivision Spacing */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-[11px] font-semibold text-muted-foreground">Grid Interval Step</label>
                  <span className="text-[10px] font-mono text-muted-foreground">
                    {Math.round(dims.width / gridSpacingMeters)}×{Math.round(dims.height / gridSpacingMeters)} cells
                  </span>
                </div>
                <div className="grid grid-cols-4 gap-1">
                  {[0.5, 1.0, 2.0, 2.5].map((lvl) => (
                    <button
                      key={lvl}
                      type="button"
                      onClick={() => setGridSpacingMeters(lvl)}
                      className={`py-1 rounded-lg text-xs font-semibold font-mono transition-all cursor-pointer ${
                        gridSpacingMeters === lvl
                          ? 'bg-teal-600 text-white shadow-xs'
                          : 'bg-muted/40 hover:bg-muted text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      {lvl}m
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </CollectorCollapsible>

          {/* Card 3: Automation & Walk Path */}
          <CollectorCollapsible
            title="Survey Walk & Route"
            icon={<M3Walk size={16} />}
            defaultOpen={true}
            badge={<span className="text-[10px] font-mono font-bold text-emerald-600">{totalPathMeters}m</span>}
          >
            <div className="space-y-2">
              <button
                type="button"
                onClick={() => setIsSimulating(!isSimulating)}
                className={`w-full flex items-center justify-between rounded-xl px-3 py-2 text-xs font-semibold transition-all cursor-pointer ${
                  isSimulating
                    ? 'bg-teal-500/20 text-teal-700 dark:text-teal-300 border border-teal-500/30'
                    : 'bg-muted/40 hover:bg-muted text-foreground'
                }`}
              >
                <span className="flex items-center gap-2">
                  <M3Bolt size={16} className={isSimulating ? 'animate-pulse text-teal-600' : ''} />
                  <span>{isSimulating ? 'Simulating Survey Run...' : 'Simulate Collection Walk'}</span>
                </span>
                <span className={`h-2 w-2 rounded-full ${isSimulating ? 'bg-teal-500 animate-ping' : 'bg-zinc-400'}`} />
              </button>

              <button
                type="button"
                onClick={handleOptimizeRoute}
                className="w-full flex items-center justify-between rounded-xl bg-muted/40 hover:bg-muted px-3 py-2 text-xs font-semibold transition-all cursor-pointer"
              >
                <span className="flex items-center gap-2">
                  <M3Operations size={16} className="text-amber-600" />
                  <span>Optimize Shortest Route</span>
                </span>
                <span className="text-[10px] text-emerald-600 font-bold font-mono">
                  {totalPathMeters}m
                </span>
              </button>
            </div>
          </CollectorCollapsible>

          {/* Card 4: Survey Planning Metrics */}
          <CollectorCollapsible
            title="Planning Metrics"
            icon={<M3Operations size={16} />}
            defaultOpen={false}
          >
            <div className="space-y-2 text-xs font-mono">
              <div className="flex justify-between py-1 border-b border-border/30">
                <span className="text-muted-foreground font-sans">Total Survey Points:</span>
                <span className="font-bold text-foreground">{surveyPoints.length}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/30">
                <span className="text-muted-foreground font-sans">Completed Points:</span>
                <span className="font-bold text-emerald-600">
                  {surveyPoints.filter((p) => p.status === 'completed').length}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/30">
                <span className="text-muted-foreground font-sans">Active Anchors:</span>
                <span className="font-bold text-teal-600">{anchors.length}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/30">
                <span className="text-muted-foreground font-sans">Walk Waypoints:</span>
                <span className="font-bold text-foreground">{waypoints.length}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-muted-foreground font-sans">Total Path Length:</span>
                <span className="font-bold text-indigo-600 dark:text-indigo-400">{totalPathMeters}m</span>
              </div>
            </div>
          </CollectorCollapsible>
        </div>

        {/* Center Column: Interactive Drag-and-Drop SVG Survey Canvas */}
        <div className="space-y-3 lg:col-span-6">
          <div className="relative aspect-square w-full rounded-2xl bg-card shadow-sm overflow-hidden select-none">
            {/* Real-time Cursor Coordinates Banner */}
            <div className="absolute top-3 left-3 z-10 flex items-center gap-2 rounded-xl bg-background/90 backdrop-blur-xs px-3 py-1.5 text-[11px] font-mono text-muted-foreground shadow-xs">
              <span>
                X: <strong className="text-foreground">{cursorPos?.xM ?? 0}m</strong> ({cursorPos?.xPct ?? 0}%)
              </span>
              <span>•</span>
              <span>
                Y: <strong className="text-foreground">{cursorPos?.yM ?? 0}m</strong> ({cursorPos?.yPct ?? 0}%)
              </span>
            </div>

            <svg
              ref={svgRef}
              viewBox="0 0 100 100"
              className="h-full w-full cursor-crosshair"
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
            >
              <defs>
                {/* Metric Grid Pattern */}
                <pattern
                  id="collectorMetricGrid"
                  width={(gridSpacingMeters / dims.width) * 100}
                  height={(gridSpacingMeters / dims.height) * 100}
                  patternUnits="userSpaceOnUse"
                >
                  <path
                    d={`M ${(gridSpacingMeters / dims.width) * 100} 0 L 0 0 0 ${(gridSpacingMeters / dims.height) * 100}`}
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="0.25"
                    className="text-border/60"
                  />
                </pattern>
              </defs>

              {/* Grid Background */}
              {showGrid && (
                <rect width="100" height="100" fill="url(#collectorMetricGrid)" />
              )}

              {/* Metric Axis Graduation Rulers */}
              {showRulers && (
                <g className="pointer-events-none select-none opacity-60">
                  {/* Top X-Axis Ruler */}
                  {Array.from({ length: Math.floor(dims.width / gridSpacingMeters) + 1 }, (_, i) => {
                    const xm = Math.round(i * gridSpacingMeters * 10) / 10
                    const xPct = (xm / dims.width) * 100
                    return (
                      <g key={`ruler_x_${i}`}>
                        <line x1={xPct} y1="0" x2={xPct} y2="1.8" stroke="currentColor" strokeWidth="0.3" className="text-foreground" />
                        <text x={xPct + 0.4} y="3.2" fontSize="1.8" fontWeight="600" fill="currentColor" className="text-muted-foreground">
                          {xm}m
                        </text>
                      </g>
                    )
                  })}
                  {/* Left Y-Axis Ruler */}
                  {Array.from({ length: Math.floor(dims.height / gridSpacingMeters) + 1 }, (_, i) => {
                    const ym = Math.round(i * gridSpacingMeters * 10) / 10
                    const yPct = 100 - (ym / dims.height) * 100
                    return (
                      <g key={`ruler_y_${i}`}>
                        <line x1="0" y1={yPct} x2="1.8" y2={yPct} stroke="currentColor" strokeWidth="0.3" className="text-foreground" />
                        <text x="2.2" y={yPct - 0.4} fontSize="1.8" fontWeight="600" fill="currentColor" className="text-muted-foreground">
                          {ym}m
                        </text>
                      </g>
                    )
                  })}
                </g>
              )}

              {/* Reference Schematic Rooms */}
              {showRooms &&
                schematicRooms.map((room) => (
                  <g key={room.id}>
                    <rect
                      x={room.x}
                      y={room.y}
                      width={room.w}
                      height={room.h}
                      fill="currentColor"
                      className="text-muted/15"
                      stroke="currentColor"
                      strokeWidth="0.6"
                      strokeDasharray="2,2"
                    />
                    <text
                      x={room.x + 2}
                      y={room.y + 4}
                      fontSize="2.5"
                      fontWeight="600"
                      fill="currentColor"
                      className="text-muted-foreground opacity-60 pointer-events-none"
                    >
                      {room.name}
                    </text>
                  </g>
                ))}

              {/* RF Interference & Scattering Fields around Obstacles */}
              {showInterferenceZones &&
                obstacles.map((obs) => {
                  const cx = obs.x + obs.w / 2
                  const cy = obs.y + obs.h / 2
                  const obsWidthM = (obs.w / 100) * dims.width
                  const obsHeightM = (obs.h / 100) * dims.height
                  const rM = obs.interferenceRadiusMeters ?? Math.max(obsWidthM, obsHeightM, 1.5) * 1.5
                  const rPct = (rM / dims.width) * 100
                  const isSel = obs.id === selectedId

                  const fieldColor =
                    obs.obstacleType === 'Metal'
                      ? '#f59e0b'
                      : obs.obstacleType === 'WiFi / RF Noise'
                      ? '#8b5cf6'
                      : obs.obstacleType === 'Concrete'
                      ? '#64748b'
                      : obs.obstacleType === 'Machinery'
                      ? '#ec4899'
                      : '#0284c7'

                  return (
                    <g key={`rf_field_${obs.id}`} className="pointer-events-none">
                      <circle
                        cx={cx}
                        cy={cy}
                        r={rPct}
                        fill={fieldColor}
                        fillOpacity={isSel ? '0.16' : '0.08'}
                        stroke={fieldColor}
                        strokeWidth="0.4"
                        strokeDasharray="2,2"
                        className={isSel ? 'animate-pulse' : ''}
                      />
                      {isSel && (
                        <text
                          x={cx}
                          y={cy - rPct - 1}
                          textAnchor="middle"
                          fontSize="1.8"
                          fontWeight="700"
                          fill={fieldColor}
                        >
                          Interference Zone: {rM.toFixed(1)}m (-{obs.attenuationDb}dB)
                        </text>
                      )}
                    </g>
                  )
                })}

              {/* Obstacle Partitions */}
              {obstacles.map((obs) => (
                <g
                  key={obs.id}
                  className="cursor-move"
                  onMouseDown={(e) => handleStartDrag(obs.id, 'obstacle', e)}
                >
                  <rect
                    x={obs.x}
                    y={obs.y}
                    width={obs.w}
                    height={obs.h}
                    rx="1"
                    fill={obs.id === selectedId ? '#f59e0b' : '#78716c'}
                    fillOpacity="0.4"
                    stroke={obs.id === selectedId ? '#d97706' : '#57534e'}
                    strokeWidth="0.8"
                  />
                  <text
                    x={obs.x + obs.w / 2}
                    y={obs.y + obs.h / 2 + 0.8}
                    textAnchor="middle"
                    fontSize="2.2"
                    fontWeight="600"
                    fill="#fff"
                    className="pointer-events-none"
                  >
                    {obs.obstacleType} (-{obs.attenuationDb}dB)
                  </text>
                </g>
              ))}

              {/* Distance Dimension Lines between Anchors (Splitting Distance between nodes) */}
              {showDimensions && anchors.length >= 2 && (
                <g className="pointer-events-none select-none">
                  {anchors.map((a1, idx) => {
                    if (idx >= 3) return null
                    const a2 = anchors[(idx + 1) % anchors.length]
                    if (!a2 || a1.id === a2.id) return null
                    const p1m = canvasPctToMeters(a1.x, a1.y, dims, 'bottom-left')
                    const p2m = canvasPctToMeters(a2.x, a2.y, dims, 'bottom-left')
                    const dist = Math.hypot(p2m.x - p1m.x, p2m.y - p1m.y)
                    const intervals = Math.round((dist / gridSpacingMeters) * 10) / 10
                    const midX = (a1.x + a2.x) / 2
                    const midY = (a1.y + a2.y) / 2

                    return (
                      <g key={`dim_${a1.id}_${a2.id}`}>
                        <line
                          x1={a1.x}
                          y1={a1.y}
                          x2={a2.x}
                          y2={a2.y}
                          stroke="#6366f1"
                          strokeWidth="0.35"
                          strokeDasharray="2,1"
                          strokeOpacity="0.6"
                        />
                        <rect
                          x={midX - 11}
                          y={midY - 2.2}
                          width="22"
                          height="4.4"
                          rx="1"
                          fill="#1e1b4b"
                          fillOpacity="0.85"
                          stroke="#6366f1"
                          strokeWidth="0.3"
                        />
                        <text
                          x={midX}
                          y={midY + 0.8}
                          textAnchor="middle"
                          fontSize="1.8"
                          fontWeight="700"
                          fill="#c7d2fe"
                        >
                          {dist.toFixed(1)}m ({intervals}×{gridSpacingMeters}m)
                        </text>
                      </g>
                    )
                  })}
                </g>
              )}

              {/* Radio Line-of-Sight & Obstruction Path Rays */}
              {showObstructionRays && selectedAnchor && (
                <g className="pointer-events-none">
                  {surveyPoints.map((pt) => {
                    const los = calculateObstructionLineOfSight(selectedAnchor, pt, obstacles, dims)
                    const midX = (selectedAnchor.x + pt.x) / 2
                    const midY = (selectedAnchor.y + pt.y) / 2
                    return (
                      <g key={`los_sp_${pt.id}`}>
                        <line
                          x1={selectedAnchor.x}
                          y1={selectedAnchor.y}
                          x2={pt.x}
                          y2={pt.y}
                          stroke={los.isObstructed ? '#ef4444' : '#0d9488'}
                          strokeWidth={los.isObstructed ? '0.45' : '0.25'}
                          strokeDasharray={los.isObstructed ? '2,1.5' : '1.5,2'}
                          strokeOpacity={los.isObstructed ? '0.85' : '0.35'}
                        />
                        {los.isObstructed && (
                          <g transform={`translate(${midX}, ${midY})`}>
                            <rect
                              x="-10"
                              y="-1.8"
                              width="20"
                              height="3.6"
                              rx="0.8"
                              fill="#18181b"
                              fillOpacity="0.85"
                              stroke="#ef4444"
                              strokeWidth="0.3"
                            />
                            <text
                              x="0"
                              y="0.8"
                              textAnchor="middle"
                              fontSize="1.7"
                              fontWeight="700"
                              fill="#fca5a5"
                            >
                              -{los.totalAttenuationDb}dB Blocked
                            </text>
                          </g>
                        )}
                      </g>
                    )
                  })}
                </g>
              )}

              {/* Anchor Range Rings */}
              {showRangeRings &&
                anchors.map((anc) => {
                  const radiusPctX = (anc.receptionRangeMeters / dims.width) * 100
                  return (
                    <circle
                      key={`ring_${anc.id}`}
                      cx={anc.x}
                      cy={anc.y}
                      r={radiusPctX}
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="0.4"
                      strokeDasharray="1.5,1.5"
                      className="text-teal-500/40 pointer-events-none"
                    />
                  )
                })}

              {/* Survey Walk Path Polyline */}
              {showPath && surveyPoints.length > 1 && (
                <polyline
                  points={surveyPoints.map((p) => `${p.x},${p.y}`).join(' ')}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="0.6"
                  strokeDasharray="1,1"
                  className="text-teal-500/70 pointer-events-none"
                />
              )}

              {/* Survey Points */}
              {surveyPoints.map((pt, idx) => {
                const isSel = pt.id === selectedId
                const isDone = pt.status === 'completed'
                const isCollecting = pt.status === 'collecting'
                const isHighlighted = highlightedNodeIds.includes(pt.id)

                return (
                  <g
                    key={pt.id}
                    className="cursor-pointer"
                    onMouseDown={(e) => handleStartDrag(pt.id, 'survey_point', e)}
                  >
                    {/* Highlight halo if in interference zone */}
                    {isHighlighted && (
                      <circle
                        cx={pt.x}
                        cy={pt.y}
                        r="4.2"
                        fill="none"
                        stroke="#f59e0b"
                        strokeWidth="0.8"
                        strokeDasharray="1,1"
                        className="animate-spin"
                      />
                    )}

                    {/* Selection halo */}
                    {isSel && (
                      <circle
                        cx={pt.x}
                        cy={pt.y}
                        r="3.2"
                        fill="none"
                        stroke="#0d9488"
                        strokeWidth="0.6"
                        className="animate-pulse"
                      />
                    )}

                    {/* Outer marker circle */}
                    <circle
                      cx={pt.x}
                      cy={pt.y}
                      r="1.8"
                      fill={isDone ? '#10b981' : isCollecting ? '#0d9488' : '#64748b'}
                      stroke="#ffffff"
                      strokeWidth="0.5"
                    />

                    {/* Center point */}
                    <circle cx={pt.x} cy={pt.y} r="0.6" fill="#ffffff" />

                    {/* Point index label */}
                    <text
                      x={pt.x}
                      y={pt.y - 2.4}
                      textAnchor="middle"
                      fontSize="2.2"
                      fontWeight="700"
                      fill="currentColor"
                      className="text-foreground pointer-events-none"
                    >
                      {idx + 1}
                    </text>
                  </g>
                )
              })}

              {/* Receiver Anchors */}
              {anchors.map((anc) => {
                const isSel = anc.id === selectedId
                const isHighlighted = highlightedNodeIds.includes(anc.id)

                return (
                  <g
                    key={anc.id}
                    className="cursor-pointer"
                    onMouseDown={(e) => handleStartDrag(anc.id, 'anchor', e)}
                  >
                    {/* Interference highlight */}
                    {isHighlighted && (
                      <rect
                        x={anc.x - 3.4}
                        y={anc.y - 3.4}
                        width="6.8"
                        height="6.8"
                        rx="1.5"
                        fill="none"
                        stroke="#f59e0b"
                        strokeWidth="0.8"
                        strokeDasharray="1.5,1.5"
                        className="animate-pulse"
                      />
                    )}
                    {isSel && (
                      <rect
                        x={anc.x - 2.6}
                        y={anc.y - 2.6}
                        width="5.2"
                        height="5.2"
                        rx="1"
                        fill="none"
                        stroke="#6366f1"
                        strokeWidth="0.6"
                      />
                    )}
                    <rect
                      x={anc.x - 1.8}
                      y={anc.y - 1.8}
                      width="3.6"
                      height="3.6"
                      rx="0.8"
                      fill="#4f46e5"
                      stroke="#ffffff"
                      strokeWidth="0.5"
                    />
                    <text
                      x={anc.x}
                      y={anc.y + 0.8}
                      textAnchor="middle"
                      fontSize="2.0"
                      fontWeight="800"
                      fill="#ffffff"
                      className="pointer-events-none"
                    >
                      A
                    </text>
                    {/* System Name / Label */}
                    <text
                      x={anc.x}
                      y={anc.y + 3.6}
                      textAnchor="middle"
                      fontSize="1.9"
                      fontWeight="700"
                      fill="currentColor"
                      className="text-foreground pointer-events-none"
                    >
                      {anc.systemName || anc.label}
                    </text>
                    {/* MAC Subtitle */}
                    {anc.macAddress && (
                      <text
                        x={anc.x}
                        y={anc.y + 5.4}
                        textAnchor="middle"
                        fontSize="1.5"
                        fontFamily="monospace"
                        fontWeight="600"
                        fill="currentColor"
                        className="text-muted-foreground pointer-events-none"
                      >
                        {anc.macAddress}
                      </text>
                    )}
                  </g>
                )
              })}

              {/* Waypoints */}
              {waypoints.map((wp) => {
                const isSel = wp.id === selectedId
                return (
                  <g
                    key={wp.id}
                    className="cursor-pointer"
                    onMouseDown={(e) => handleStartDrag(wp.id, 'waypoint', e)}
                  >
                    {isSel && (
                      <circle
                        cx={wp.x}
                        cy={wp.y}
                        r="2.8"
                        fill="none"
                        stroke="#10b981"
                        strokeWidth="0.6"
                      />
                    )}
                    <polygon
                      points={`${wp.x},${wp.y - 1.8} ${wp.x + 1.8},${wp.y + 1.8} ${wp.x - 1.8},${wp.y + 1.8}`}
                      fill="#10b981"
                      stroke="#ffffff"
                      strokeWidth="0.4"
                    />
                    <text
                      x={wp.x}
                      y={wp.y + 3.4}
                      textAnchor="middle"
                      fontSize="1.9"
                      fontWeight="600"
                      fill="currentColor"
                      className="text-foreground pointer-events-none"
                    >
                      W{wp.order}
                    </text>
                  </g>
                )
              })}
            </svg>
          </div>

          {/* Survey Progress Bar */}
          <div className="rounded-2xl bg-card p-4 shadow-sm flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="font-bold text-foreground">Survey Progress:</span>
              <span className="text-muted-foreground font-mono font-semibold">
                {surveyPoints.filter((p) => p.status === 'completed').length} / {surveyPoints.length} Points
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-muted-foreground text-[11px]">
                Total Path: <strong className="text-foreground font-mono font-bold">{totalPathMeters}m</strong>
              </span>
              <div className="w-32 bg-muted rounded-full h-2 overflow-hidden">
                <div
                  className="bg-emerald-500 h-full transition-all duration-300"
                  style={{
                    width: `${
                      surveyPoints.length > 0
                        ? (surveyPoints.filter((p) => p.status === 'completed').length / surveyPoints.length) * 100
                        : 0
                    }%`,
                  }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Dynamic Property Inspector, Distance Matrix & ESP Roster */}
        <div className="space-y-3 lg:col-span-3">
          {/* 1. Property Inspector */}
          <CollectorCollapsible
            title="Property Inspector"
            icon={<M3Info size={16} />}
            defaultOpen={true}
            badge={selectedId ? <span className="text-[10px] font-mono text-teal-600 font-bold">{selectedId}</span> : undefined}
            action={
              selectedId ? (
                <button
                  type="button"
                  onClick={handleDeleteSelected}
                  className="text-rose-500 hover:text-rose-600 p-1 rounded-lg hover:bg-rose-500/10 transition-colors cursor-pointer"
                  title="Delete Selected Item"
                >
                  <M3Trash size={14} />
                </button>
              ) : null
            }
          >
            {selectedPoint && (
              <div className="space-y-3 text-xs">
                <div>
                  <label className="font-semibold text-muted-foreground">Point Label</label>
                  <input
                    type="text"
                    value={selectedPoint.label}
                    onChange={(e) => {
                      const val = e.target.value
                      setSurveyPoints((prev) =>
                        prev.map((p) => (p.id === selectedPoint.id ? { ...p, label: val } : p))
                      )
                    }}
                    className="w-full mt-1 rounded-xl bg-muted/40 px-3 py-1.5 font-medium text-foreground focus:bg-card focus:ring-2 focus:ring-accent"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2 font-mono">
                  <div>
                    <label className="text-muted-foreground font-sans font-semibold">X (Meters)</label>
                    <input
                      type="number"
                      step="0.1"
                      value={Math.round(canvasPctToMeters(selectedPoint.x, selectedPoint.y, dims, 'bottom-left').x * 10) / 10}
                      onChange={(e) => {
                        const newXm = Number(e.target.value)
                        const currentYm = canvasPctToMeters(selectedPoint.x, selectedPoint.y, dims, 'bottom-left').y
                        const newPct = metersToCanvasPct(newXm, currentYm, dims, 'bottom-left')
                        setSurveyPoints((prev) =>
                          prev.map((p) => (p.id === selectedPoint.id ? { ...p, x: newPct.x } : p))
                        )
                      }}
                      className="w-full mt-1 rounded-xl bg-muted/40 px-3 py-1.5 text-foreground focus:bg-card focus:ring-2 focus:ring-accent"
                    />
                  </div>
                  <div>
                    <label className="text-muted-foreground font-sans font-semibold">Y (Meters)</label>
                    <input
                      type="number"
                      step="0.1"
                      value={Math.round(canvasPctToMeters(selectedPoint.x, selectedPoint.y, dims, 'bottom-left').y * 10) / 10}
                      onChange={(e) => {
                        const newYm = Number(e.target.value)
                        const currentXm = canvasPctToMeters(selectedPoint.x, selectedPoint.y, dims, 'bottom-left').x
                        const newPct = metersToCanvasPct(currentXm, newYm, dims, 'bottom-left')
                        setSurveyPoints((prev) =>
                          prev.map((p) => (p.id === selectedPoint.id ? { ...p, y: newPct.x } : p))
                        )
                      }}
                      className="w-full mt-1 rounded-xl bg-muted/40 px-3 py-1.5 text-foreground focus:bg-card focus:ring-2 focus:ring-accent"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="font-semibold text-muted-foreground">Target Samples</label>
                    <input
                      type="number"
                      value={selectedPoint.targetSamples}
                      onChange={(e) => {
                        const val = Number(e.target.value)
                        setSurveyPoints((prev) =>
                          prev.map((p) => (p.id === selectedPoint.id ? { ...p, targetSamples: val } : p))
                        )
                      }}
                      className="w-full mt-1 rounded-xl bg-muted/40 px-3 py-1.5 font-mono text-foreground focus:bg-card focus:ring-2 focus:ring-accent"
                    />
                  </div>
                  <div>
                    <label className="font-semibold text-muted-foreground">Status</label>
                    <select
                      value={selectedPoint.status}
                      onChange={(e) => {
                        const val = e.target.value as any
                        setSurveyPoints((prev) =>
                          prev.map((p) => (p.id === selectedPoint.id ? { ...p, status: val } : p))
                        )
                      }}
                      className="w-full mt-1 rounded-xl bg-muted/40 px-3 py-1.5 text-foreground focus:bg-card focus:ring-2 focus:ring-accent"
                    >
                      <option value="pending">Pending</option>
                      <option value="collecting">Collecting</option>
                      <option value="completed">Completed</option>
                    </select>
                  </div>
                </div>

              </div>
            )}
            {/* Anchor Inspector */}
            {selectedAnchor && (
              <div className="space-y-3 text-xs">
                <div>
                  <label className="font-semibold text-muted-foreground">System Name (System Alias)</label>
                  <input
                    type="text"
                    value={selectedAnchor.systemName || selectedAnchor.label}
                    onChange={(e) => {
                      const val = e.target.value
                      setAnchors((prev) =>
                        prev.map((a) => (a.id === selectedAnchor.id ? { ...a, systemName: val } : a))
                      )
                    }}
                    className="w-full mt-1 rounded-xl bg-muted/40 px-3 py-1.5 font-medium text-foreground focus:bg-card focus:ring-2 focus:ring-accent"
                    placeholder="e.g. ESP32-01 (SW Lobby)"
                  />
                </div>

                <div>
                  <label className="font-semibold text-muted-foreground">Hardware MAC Address</label>
                  <input
                    type="text"
                    value={selectedAnchor.macAddress || ''}
                    onChange={(e) => {
                      const val = e.target.value.toUpperCase()
                      setAnchors((prev) =>
                        prev.map((a) => (a.id === selectedAnchor.id ? { ...a, macAddress: val } : a))
                      )
                    }}
                    className="w-full mt-1 rounded-xl bg-muted/40 px-3 py-1.5 font-mono text-foreground focus:bg-card focus:ring-2 focus:ring-accent"
                    placeholder="24:6F:28:XX:XX:XX"
                  />
                  <p className="text-[10px] text-muted-foreground mt-0.5">
                    Flashed ESP32 hardware MAC address broadcasted over WebSocket & live positioning.
                  </p>
                </div>

                <div>
                  <label className="font-semibold text-muted-foreground">Display Label</label>
                  <input
                    type="text"
                    value={selectedAnchor.label}
                    onChange={(e) => {
                      const val = e.target.value
                      setAnchors((prev) =>
                        prev.map((a) => (a.id === selectedAnchor.id ? { ...a, label: val } : a))
                      )
                    }}
                    className="w-full mt-1 rounded-xl bg-muted/40 px-3 py-1.5 font-medium text-foreground focus:bg-card focus:ring-2 focus:ring-accent"
                  />
                </div>

                {/* Customizable Range Slider */}
                <div>
                  <div className="flex items-center justify-between text-muted-foreground">
                    <label className="font-semibold">Reception Range Radius</label>
                    <span className="font-mono font-bold text-teal-600">
                      {selectedAnchor.receptionRangeMeters} m
                    </span>
                  </div>
                  <input
                    type="range"
                    min="1.0"
                    max="20.0"
                    step="0.5"
                    value={selectedAnchor.receptionRangeMeters}
                    onChange={(e) => {
                      const val = Number(e.target.value)
                      setAnchors((prev) =>
                        prev.map((a) => (a.id === selectedAnchor.id ? { ...a, receptionRangeMeters: val } : a))
                      )
                    }}
                    className="w-full mt-1 accent-teal-600 cursor-pointer"
                  />
                  <p className="text-[10px] text-muted-foreground mt-0.5">
                    Adjusts the RF listening boundary displayed on the canvas.
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="font-semibold text-muted-foreground">BLE Channel</label>
                    <select
                      value={selectedAnchor.channel}
                      onChange={(e) => {
                        const val = Number(e.target.value)
                        setAnchors((prev) =>
                          prev.map((a) => (a.id === selectedAnchor.id ? { ...a, channel: val } : a))
                        )
                      }}
                      className="w-full mt-1 rounded-xl bg-muted/40 px-3 py-1.5 font-mono text-foreground focus:bg-card focus:ring-2 focus:ring-accent"
                    >
                      <option value={37}>37 (2402 MHz)</option>
                      <option value={38}>38 (2426 MHz)</option>
                      <option value={39}>39 (2480 MHz)</option>
                    </select>
                  </div>
                  <div>
                    <label className="font-semibold text-muted-foreground">USB Serial Port</label>
                    <input
                      type="text"
                      value={selectedAnchor.port || 'COM3'}
                      onChange={(e) => {
                        const val = e.target.value
                        setAnchors((prev) =>
                          prev.map((a) => (a.id === selectedAnchor.id ? { ...a, port: val } : a))
                        )
                      }}
                      className="w-full mt-1 rounded-xl bg-muted/40 px-3 py-1.5 font-mono text-foreground focus:bg-card focus:ring-2 focus:ring-accent"
                    />
                  </div>
                </div>

                {/* Deploy Anchor Action */}
                <button
                  onClick={() => handleDeploySingleAnchor(selectedAnchor)}
                  className="w-full flex items-center justify-center gap-2 rounded-xl bg-teal-500/15 hover:bg-teal-500/25 text-teal-700 dark:text-teal-300 px-3 py-2 text-xs font-semibold transition-all cursor-pointer"
                >
                  <M3Deploy size={15} />
                  <span>Broadcast Anchor to Live Engine</span>
                </button>
              </div>
            )}

            {/* Obstacle / Interference Inspector */}
            {selectedObstacle && (
              <div className="space-y-3 text-xs">
                <div>
                  <label className="font-semibold text-muted-foreground">Obstacle / Interference Name</label>
                  <input
                    type="text"
                    value={selectedObstacle.label}
                    onChange={(e) => {
                      const val = e.target.value
                      setObstacles((prev) =>
                        prev.map((o) => (o.id === selectedObstacle.id ? { ...o, label: val } : o))
                      )
                    }}
                    className="w-full mt-1 rounded-xl bg-muted/40 px-3 py-1.5 font-medium text-foreground focus:bg-card focus:ring-2 focus:ring-accent"
                  />
                </div>

                <div>
                  <label className="font-semibold text-muted-foreground">Material & Interference Type</label>
                  <select
                    value={selectedObstacle.obstacleType}
                    onChange={(e) => {
                      const val = e.target.value as any
                      let att = 4.8
                      let rad = 3.0
                      if (val === 'Wood') { att = 3.2; rad = 2.5 }
                      if (val === 'Metal') { att = 12.0; rad = 4.5 }
                      if (val === 'Concrete') { att = 14.0; rad = 4.0 }
                      if (val === 'Human Body') { att = 6.5; rad = 2.0 }
                      if (val === 'WiFi / RF Noise') { att = 9.0; rad = 5.0 }
                      if (val === 'Machinery') { att = 11.0; rad = 4.0 }
                      setObstacles((prev) =>
                        prev.map((o) =>
                          o.id === selectedObstacle.id
                            ? { ...o, obstacleType: val, attenuationDb: att, interferenceRadiusMeters: rad }
                            : o
                        )
                      )
                    }}
                    className="w-full mt-1 rounded-xl bg-muted/40 px-3 py-1.5 text-foreground focus:bg-card focus:ring-2 focus:ring-accent"
                  >
                    <option value="Drywall">Drywall Partition (-4.8 dB)</option>
                    <option value="Wood">Wooden Wall / Furniture (-3.2 dB)</option>
                    <option value="Metal">Metal Cabinet / Pillar (-12.0 dB Reflection)</option>
                    <option value="Concrete">Reinforced Concrete (-14.0 dB Blockage)</option>
                    <option value="Human Body">Human Obstruction Zone (-6.5 dB Shadowing)</option>
                    <option value="WiFi / RF Noise">WiFi / 2.4GHz RF Interference (-9.0 dB Noise)</option>
                    <option value="Machinery">Industrial Machinery (-11.0 dB EMI)</option>
                  </select>
                </div>

                <div>
                  <div className="flex items-center justify-between text-muted-foreground">
                    <label className="font-semibold">RF Attenuation Factor</label>
                    <span className="font-mono font-bold text-amber-600">
                      -{selectedObstacle.attenuationDb} dB
                    </span>
                  </div>
                  <input
                    type="range"
                    min="1.0"
                    max="25.0"
                    step="0.5"
                    value={selectedObstacle.attenuationDb}
                    onChange={(e) => {
                      const val = Number(e.target.value)
                      setObstacles((prev) =>
                        prev.map((o) => (o.id === selectedObstacle.id ? { ...o, attenuationDb: val } : o))
                      )
                    }}
                    className="w-full mt-1 accent-amber-600 cursor-pointer"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between text-muted-foreground">
                    <label className="font-semibold">Interference Scattering Radius</label>
                    <span className="font-mono font-bold text-amber-600">
                      {selectedObstacle.interferenceRadiusMeters ?? 3.0} m
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0.5"
                    max="15.0"
                    step="0.5"
                    value={selectedObstacle.interferenceRadiusMeters ?? 3.0}
                    onChange={(e) => {
                      const val = Number(e.target.value)
                      setObstacles((prev) =>
                        prev.map((o) => (o.id === selectedObstacle.id ? { ...o, interferenceRadiusMeters: val } : o))
                      )
                    }}
                    className="w-full mt-1 accent-amber-600 cursor-pointer"
                  />
                  <p className="text-[10px] text-muted-foreground mt-0.5">
                    Zone within which wireless beacon packets suffer multipath and signal degradation.
                  </p>
                </div>

                {/* Nodes within Interference Range Analysis & Selector */}
                {(() => {
                  const allCandidateNodes = [
                    ...anchors.map((a) => ({ id: a.id, label: a.systemName || a.label, x: a.x, y: a.y, type: 'anchor' as const })),
                    ...surveyPoints.map((p) => ({ id: p.id, label: p.label, x: p.x, y: p.y, type: 'survey_point' as const })),
                  ]
                  const impacted = getNodesInInterferenceRange(selectedObstacle, allCandidateNodes, dims)
                  return (
                    <div className="pt-2 border-t border-border/40 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-[10px] uppercase text-muted-foreground">
                          Nodes in Range ({impacted.length})
                        </span>
                        {impacted.length > 0 && (
                          <button
                            onClick={() => {
                              setHighlightedNodeIds(impacted.map((item) => item.node.id))
                              setStatusMessage(`Highlighted ${impacted.length} nodes impacted by ${selectedObstacle.label}`)
                              setTimeout(() => setStatusMessage(null), 3000)
                            }}
                            className="text-[10px] text-amber-600 font-bold hover:underline cursor-pointer"
                          >
                            Highlight Nodes
                          </button>
                        )}
                      </div>
                      {impacted.length === 0 ? (
                        <p className="text-[11px] text-muted-foreground">No nodes currently within interference radius.</p>
                      ) : (
                        <div className="space-y-1 max-h-36 overflow-y-auto">
                          {impacted.map((item) => (
                            <div
                              key={item.node.id}
                              className="flex items-center justify-between p-1.5 rounded-lg bg-amber-500/10 text-[11px] font-mono"
                            >
                              <span className="font-sans truncate max-w-[120px] font-medium">{item.node.label}</span>
                              <span className="text-amber-700 dark:text-amber-300 font-bold">{item.distanceMeters}m</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })()}
              </div>
            )}

            {!selectedPoint && !selectedAnchor && !selectedObstacle && !selectedWaypoint && (
              <div className="py-6 text-center text-muted-foreground space-y-2">
                <M3Info size={24} className="mx-auto opacity-40" />
                <p>Click any survey point, anchor, or obstacle on the canvas to inspect its parameters.</p>
              </div>
            )}
          </CollectorCollapsible>

          {/* 2. Anchor Distance Matrix (when a survey point is selected) */}
          {selectedPoint && (
            <CollectorCollapsible
              title="Anchor Distance Matrix"
              icon={<M3Beacon size={16} />}
              defaultOpen={true}
              badge={<span className="text-[10px] text-teal-600 font-mono">Euclidean</span>}
            >
              <div className="space-y-1.5 max-h-48 overflow-y-auto">
                {anchorDistances.map((ad) => (
                  <div
                    key={ad.anchorId}
                    className={`flex items-center justify-between rounded-xl p-2 text-[11px] font-mono ${
                      ad.inRange
                        ? 'bg-muted/40 text-foreground'
                        : 'bg-rose-500/10 text-rose-500'
                    }`}
                  >
                    <span className="truncate max-w-[110px] font-sans font-medium">{ad.label}</span>
                    <div className="flex items-center gap-1.5">
                      <span className="font-bold">{ad.distanceMeters}m</span>
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          ad.inRange ? 'bg-emerald-500' : 'bg-rose-500'
                        }`}
                        title={ad.inRange ? 'In Radio Range' : 'Out of Range'}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </CollectorCollapsible>
          )}

          {/* 3. ESP32 Anchor Roster */}
          <CollectorCollapsible
            title={`ESP32 Anchor Roster (${anchors.length})`}
            icon={<M3Deploy size={16} />}
            defaultOpen={false}
            badge={<span className="text-[10px] text-teal-600 font-bold font-mono">Live Broadcast</span>}
          >
          <div className="rounded-2xl bg-card p-4 shadow-sm space-y-3 text-xs">
            <div className="flex items-center justify-between">
              <h4 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                ESP32 Anchor Roster ({anchors.length})
              </h4>
              <span className="text-[10px] text-teal-600 font-bold font-mono">Live Broadcast</span>
            </div>

            <div className="space-y-1.5 font-mono">
              <div className="flex justify-between text-[11px]">
                <span className="text-muted-foreground font-sans">Beacon MAC:</span>
                <span className="font-bold text-foreground">{targetMac}</span>
              </div>
              <div className="flex justify-between text-[11px]">
                <span className="text-muted-foreground font-sans">Grid Interval:</span>
                <span className="text-foreground font-bold">{gridSpacingMeters}m step</span>
              </div>
            </div>

            {/* List of active anchors with MAC and System Name */}
            <div className="space-y-1.5 pt-1 border-t border-border/40 max-h-48 overflow-y-auto">
              {anchors.map((anc) => {
                const isSel = anc.id === selectedId
                const m = canvasPctToMeters(anc.x, anc.y, dims, 'bottom-left')
                return (
                  <div
                    key={anc.id}
                    onClick={() => {
                      setSelectedId(anc.id)
                      setSelectedType('anchor')
                    }}
                    className={`p-2 rounded-xl transition-all cursor-pointer ${
                      isSel
                        ? 'bg-indigo-500/15 border border-indigo-500/30 text-foreground'
                        : 'bg-muted/40 hover:bg-muted text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    <div className="flex items-center justify-between font-sans">
                      <span className="font-bold text-foreground text-[11px] truncate max-w-[130px]">
                        {anc.systemName || anc.label}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-background/60 font-mono text-indigo-600 dark:text-indigo-400 font-bold">
                        Ch.{anc.channel}
                      </span>
                    </div>
                    <div className="flex items-center justify-between font-mono text-[10px] mt-0.5">
                      <span className="text-muted-foreground">{anc.macAddress || 'No MAC set'}</span>
                      <span>({m.x.toFixed(1)}m, {m.y.toFixed(1)}m)</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
          </CollectorCollapsible>
        </div>

        </div>
      )}

      {/* TAB B: ZERO-TRANSFORMATION RAW INGESTION & LIVE LOGGER */}
      {activeViewTab === 'logger' && (
        <div className="space-y-4">
          {/* Fidelity Guarantee Header Banner */}
          <div className="rounded-2xl border border-emerald-500/30 bg-gradient-to-r from-emerald-950/25 via-card to-card p-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3.5">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 shadow-inner">
                  <M3Collector size={26} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-foreground">
                      Zero-Transformation Raw Ingestion Studio
                    </h3>
                    <span className="text-[10px] rounded-md px-2 py-0.5 font-mono font-bold bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20">
                      100% RAW FIDELITY
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Date is date, time is time, RSSI is raw RSSI. No cleaning, no filtering, no smoothing, and no appending. Discards zero information.
                  </p>
                </div>
              </div>

              {/* Real-time summary stats */}
              <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
                <div className="rounded-xl bg-muted/40 px-3 py-1.5 text-center border border-border/30">
                  <div className="text-[10px] text-muted-foreground uppercase font-sans font-semibold">Total Packets</div>
                  <div className="font-bold text-foreground text-sm">{rawRecords.length}</div>
                </div>
                <div className="rounded-xl bg-muted/40 px-3 py-1.5 text-center border border-border/30">
                  <div className="text-[10px] text-muted-foreground uppercase font-sans font-semibold">Active Nodes</div>
                  <div className="font-bold text-teal-600 text-sm">{new Set(rawRecords.map((r) => r.anchorId)).size}</div>
                </div>
                <div className="rounded-xl bg-muted/40 px-3 py-1.5 text-center border border-border/30">
                  <div className="text-[10px] text-muted-foreground uppercase font-sans font-semibold">Filter Rate</div>
                  <div className="font-bold text-emerald-600 text-sm">0.0% (Zero Filter)</div>
                </div>
                <div className="rounded-xl bg-muted/40 px-3 py-1.5 text-center border border-border/30">
                  <div className="text-[10px] text-muted-foreground uppercase font-sans font-semibold">Target Tag MAC</div>
                  <div className="font-bold text-foreground text-xs">{targetMac}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Action Toolbar */}
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-card p-3 shadow-xs border border-border/40">
            <div className="flex flex-wrap items-center gap-2">
              {/* Stream Toggle */}
              <button
                onClick={() => setIsLiveStreaming(!isLiveStreaming)}
                className={`flex items-center gap-2 rounded-xl px-3.5 py-1.5 text-xs font-semibold transition-all cursor-pointer ${
                  isLiveStreaming
                    ? 'bg-emerald-500 text-white shadow-xs'
                    : 'bg-muted/60 text-muted-foreground hover:text-foreground'
                }`}
              >
                <span className={`h-2 w-2 rounded-full ${isLiveStreaming ? 'bg-white animate-pulse' : 'bg-zinc-400'}`} />
                {isLiveStreaming ? 'Streaming Live (Active)' : 'Stream Paused'}
              </button>

              {/* Node Filter */}
              <div className="flex items-center gap-1.5 text-xs bg-muted/40 px-3 py-1.5 rounded-xl border border-border/30">
                <span className="text-muted-foreground font-medium">Filter Node:</span>
                <select
                  value={anchorFilter}
                  onChange={(e) => setAnchorFilter(e.target.value)}
                  className="bg-transparent font-semibold text-foreground focus:outline-hidden"
                >
                  <option value="ALL">All Reporting Nodes ({rawRecords.length})</option>
                  {Array.from(new Set(rawRecords.map((r) => r.anchorId))).map((ancId) => (
                    <option key={ancId} value={ancId}>
                      {ancId} ({rawRecords.filter((r) => r.anchorId === ancId).length})
                    </option>
                  ))}
                </select>
              </div>

              {/* Inject Test Packet */}
              <button
                onClick={handleInjectSamplePacket}
                className="flex items-center gap-1.5 rounded-xl bg-teal-500/10 hover:bg-teal-500/20 text-teal-700 dark:text-teal-300 px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer"
                title="Capture an immediate sample uncleaned packet from active ESP32 anchors"
              >
                <M3Bolt size={14} />
                <span>⚡ Capture Test Packet</span>
              </button>
            </div>

            {/* Export Actions */}

            {/* Unified Export & Actions Cascading Dropdown */}
            <div className="flex items-center gap-2">
              <CollectorDropdown
                align="right"
                items={[
                  {
                    id: 'export_csv',
                    label: 'Export Data Sheet (.csv)',
                    icon: <M3Download size={14} />,
                    onClick: handleExportDataSheet,
                  },
                  {
                    id: 'export_log',
                    label: 'Export Plain Text Log (.log)',
                    icon: <M3Download size={14} />,
                    onClick: handleExportPlainTextLog,
                  },
                  {
                    id: 'copy_log',
                    label: 'Copy Log to Clipboard',
                    icon: <M3Check size={14} />,
                    onClick: handleCopyPlainTextLog,
                  },
                  {
                    id: 'clear_buffer',
                    label: 'Clear Raw Buffer',
                    icon: <M3Trash size={14} />,
                    danger: true,
                    onClick: handleClearRawBuffer,
                  },
                ]}
                trigger={(isOpen) => (
                  <button
                    type="button"
                    className="flex items-center gap-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white px-3.5 py-1.5 text-xs font-semibold transition-all shadow-xs cursor-pointer select-none"
                  >
                    <M3Download size={14} />
                    <span>Export & Logs</span>
                    <span className="text-[10px] opacity-70">▼</span>
                  </button>
                )}
              />
            </div>

          </div>

          {/* Dual Ingestion Grid: Data Sheet (Left) + Plain Text Log (Right) */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
            {/* 1. Structured Raw Data Sheet (Spreadsheet / CSV view) */}
            <div className="rounded-2xl bg-card p-4 shadow-sm border border-border/40 space-y-3 lg:col-span-7">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <M3Reports size={18} className="text-teal-600" />
                  <h4 className="text-xs font-bold uppercase tracking-wider text-foreground">
                    Tabular Data Sheet (Uncleaned & Unmodified)
                  </h4>
                </div>
                <span className="text-[10px] text-muted-foreground font-mono">
                  {filteredRecords.length} records shown
                </span>
              </div>

              {/* Table */}
              <div className="overflow-x-auto rounded-xl border border-border/40 max-h-[480px] overflow-y-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-muted/60 sticky top-0 z-10 text-[11px] font-semibold text-muted-foreground uppercase font-sans">
                    <tr>
                      <th className="p-2.5 pl-3">Date</th>
                      <th className="p-2.5">Time</th>
                      <th className="p-2.5">Anchor</th>
                      <th className="p-2.5">Device MAC</th>
                      <th className="p-2.5 text-right">Raw RSSI</th>
                      <th className="p-2.5 pr-3 text-right">Raw Payload</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/30 font-mono text-[11px]">
                    {filteredRecords.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="p-8 text-center text-muted-foreground font-sans">
                          No raw packets matching current filter. Telemetry stream is active...
                        </td>
                      </tr>
                    ) : (
                      filteredRecords.map((r) => (
                        <tr key={r.id} className="hover:bg-muted/20 transition-colors">
                          <td className="p-2 pl-3 font-medium text-foreground whitespace-nowrap">{r.date}</td>
                          <td className="p-2 text-muted-foreground whitespace-nowrap">{r.time}</td>
                          <td className="p-2">
                            <span className="px-1.5 py-0.5 rounded-md bg-teal-500/10 text-teal-700 dark:text-teal-300 font-bold">
                              {r.anchorId}
                            </span>
                          </td>
                          <td className="p-2 text-muted-foreground text-[10px]">{r.deviceMac}</td>
                          <td className="p-2 text-right">
                            <span
                              className={`px-2 py-0.5 rounded-md font-bold ${
                                Number(r.rssi) >= -65
                                  ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                                  : Number(r.rssi) >= -75
                                  ? 'bg-amber-500/15 text-amber-600 dark:text-amber-400'
                                  : 'bg-rose-500/15 text-rose-600 dark:text-rose-400'
                              }`}
                            >
                              {r.rssi} dBm
                            </span>
                          </td>
                          <td
                            className="p-2 pr-3 text-right text-[10px] text-muted-foreground truncate max-w-[140px]"
                            title={r.rawPayload}
                          >
                            {r.rawPayload}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* 2. Verbatim Plain Text Log Console */}
            <div className="rounded-2xl bg-card p-4 shadow-sm border border-border/40 space-y-3 lg:col-span-5 flex flex-col">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <M3Monitor size={18} className="text-emerald-500" />
                  <h4 className="text-xs font-bold uppercase tracking-wider text-foreground">
                    Verbatim Plain Text Log (.log)
                  </h4>
                </div>
                <div className="flex items-center gap-2 text-[10px]">
                  <label className="flex items-center gap-1 text-muted-foreground cursor-pointer">
                    <input
                      type="checkbox"
                      checked={autoScrollConsole}
                      onChange={(e) => setAutoScrollConsole(e.target.checked)}
                      className="rounded text-emerald-500"
                    />
                    Auto-scroll
                  </label>
                  <span className="font-mono text-muted-foreground">({rawLines.length} lines)</span>
                </div>
              </div>

              {/* Console terminal window */}
              <div
                ref={consoleRef}
                className="flex-1 rounded-xl bg-slate-950 p-3 font-mono text-[11px] text-emerald-400 border border-border/50 max-h-[480px] overflow-y-auto space-y-1 select-all"
              >
                {rawLines.length === 0 ? (
                  <div className="text-slate-500 italic p-6 text-center">
                    Awaiting verbatim lines from BLE receiver nodes...
                  </div>
                ) : (
                  rawLines.map((line, idx) => (
                    <div key={idx} className="flex items-start gap-2 hover:bg-slate-900/60 rounded px-1">
                      <span className="text-slate-600 select-none w-7 text-right flex-shrink-0 text-[10px]">
                        {idx + 1}
                      </span>
                      <span className="break-all whitespace-pre-wrap text-emerald-300">{line}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
