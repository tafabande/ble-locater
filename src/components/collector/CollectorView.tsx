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
} from '../../lib/collectorGrid'
import {
  canvasPctToMeters,
  metersToCanvasPct,
  type BuildingDimensions,
} from '../../lib/geometry'
import { type MapItem } from '../../lib/simulation'
import { type UserRole } from '../../lib/rbac'
import {
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
} from '../common/MaterialIcon'

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
  const [showRangeRings, setShowRangeRings] = useState(true)
  const [showRooms, setShowRooms] = useState(true)
  const [showPath, setShowPath] = useState(true)

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
      { id: 'ANCHOR_01', label: 'ESP32 Anchor A (SW)', x: 5, y: 95, txPower: -60.0, channel: 37, receptionRangeMeters: 8.0, port: 'COM3', status: 'online' },
      { id: 'ANCHOR_02', label: 'ESP32 Anchor B (SE)', x: 95, y: 95, txPower: -60.0, channel: 38, receptionRangeMeters: 8.0, port: 'COM4', status: 'online' },
      { id: 'ANCHOR_03', label: 'ESP32 Anchor C (NW)', x: 5, y: 5, txPower: -60.0, channel: 39, receptionRangeMeters: 8.0, port: 'COM5', status: 'online' },
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
      { id: 'OBS_01', label: 'Drywall Partition', x: 48, y: 20, w: 4, h: 60, obstacleType: 'Drywall', attenuationDb: 4.8 },
      { id: 'OBS_02', label: 'Metal Filing Cabinet', x: 20, y: 10, w: 10, h: 8, obstacleType: 'Metal', attenuationDb: 12.0 },
    ]
  })

  // Selection and UI state
  const [selectedId, setSelectedId] = useState<string | null>('SP_01')
  const [selectedType, setSelectedType] = useState<CollectorElementType>('survey_point')
  const [cursorPos, setCursorPos] = useState<{ xPct: number; yPct: number; xM: number; yM: number } | null>(null)
  const [collectorDaemonStatus, setCollectorDaemonStatus] = useState<'ACTIVE' | 'OFFLINE'>('OFFLINE')
  const [isSimulating, setIsSimulating] = useState(false)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)

  // Persist state
  useEffect(() => {
    localStorage.setItem('rtls_collector_points', JSON.stringify(surveyPoints))
    localStorage.setItem('rtls_collector_anchors', JSON.stringify(anchors))
    localStorage.setItem('rtls_collector_waypoints', JSON.stringify(waypoints))
    localStorage.setItem('rtls_collector_obstacles', JSON.stringify(obstacles))
  }, [surveyPoints, anchors, waypoints, obstacles])

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
        x: cx,
        y: cy,
        txPower: -60.0,
        channel: 37,
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

  return (
    <div className="space-y-4">
      {/* 1. Header Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-card p-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-500/10 text-teal-600 dark:text-teal-400">
            <M3Collector size={22} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={sessionName}
                onChange={(e) => setSessionName(e.target.value)}
                className="bg-transparent text-sm font-bold text-foreground focus:outline-hidden focus:ring-2 focus:ring-accent rounded-lg px-1.5 py-0.5"
              />
              <span className="text-[10px] rounded-full px-2.5 py-0.5 font-semibold bg-muted text-muted-foreground">
                {dims.width}m × {dims.height}m
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              Survey Grid Planner, Range Allocation & Ground-Truth Collector
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Grid Snap & Spacing */}
          <div className="flex items-center gap-2 rounded-xl bg-muted/40 px-3 py-1.5 text-xs">
            <label className="flex items-center gap-1.5 font-semibold cursor-pointer">
              <input
                type="checkbox"
                checked={snapToGrid}
                onChange={(e) => setSnapToGrid(e.target.checked)}
                className="rounded text-accent focus:ring-accent"
              />
              Snap Grid
            </label>
            <span className="text-muted-foreground/40">|</span>
            <select
              value={gridSpacingMeters}
              onChange={(e) => setGridSpacingMeters(Number(e.target.value))}
              className="bg-transparent font-semibold text-foreground focus:outline-hidden"
            >
              <option value={0.25}>0.25 m</option>
              <option value={0.5}>0.5 m</option>
              <option value={1.0}>1.0 m</option>
              <option value={1.5}>1.5 m</option>
              <option value={2.0}>2.0 m</option>
            </select>
          </div>

          {/* Hardware Daemon Toggle */}
          <button
            onClick={handleToggleCollectorDaemon}
            className={`flex items-center gap-2 rounded-xl px-3.5 py-1.5 text-xs font-semibold transition-all shadow-xs cursor-pointer ${
              collectorDaemonStatus === 'ACTIVE'
                ? 'bg-emerald-500 text-white hover:bg-emerald-600'
                : 'bg-muted/60 hover:bg-muted text-foreground'
            }`}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                collectorDaemonStatus === 'ACTIVE' ? 'bg-white animate-pulse' : 'bg-rose-500'
              }`}
            />
            {collectorDaemonStatus === 'ACTIVE' ? 'Hardware Collector: ON' : 'Hardware Collector: OFF'}
          </button>

          {/* Simulate Run */}
          <button
            onClick={() => setIsSimulating(!isSimulating)}
            className={`flex items-center gap-2 rounded-xl px-3.5 py-1.5 text-xs font-semibold transition-all cursor-pointer ${
              isSimulating
                ? 'bg-teal-500/20 text-teal-600'
                : 'bg-muted/60 hover:bg-muted text-foreground'
            }`}
          >
            <M3Operations size={15} />
            {isSimulating ? 'Simulating Run...' : 'Simulate Collection'}
          </button>

          {/* Export Plan */}
          <button
            onClick={handleExportPlan}
            className="flex items-center gap-2 rounded-xl bg-accent text-accent-foreground px-3.5 py-1.5 text-xs font-semibold hover:opacity-90 transition-opacity shadow-xs cursor-pointer"
          >
            <M3Download size={15} />
            Export Plan
          </button>
        </div>
      </div>

      {/* Status banner */}
      {statusMessage && (
        <div className="flex items-center gap-2 rounded-xl bg-teal-500/10 px-3.5 py-2 text-xs font-medium text-teal-700 dark:text-teal-300">
          <M3Check size={16} />
          {statusMessage}
        </div>
      )}

      {/* 2. Main Studio Grid: Palette (Left), Canvas (Center), Property Inspector (Right) */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        {/* Left Column: Element Library & Efficiency Tools */}
        <div className="space-y-4 lg:col-span-3">
          {/* Add Elements Palette */}
          <div className="rounded-2xl bg-card p-4 shadow-sm space-y-3">
            <h4 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              Element Library (Click to Add)
            </h4>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => handleAddElement('survey_point')}
                className="flex flex-col items-center justify-center p-3 rounded-xl bg-muted/30 hover:bg-teal-500/10 hover:text-teal-600 transition-all text-xs font-semibold gap-1.5 text-center cursor-pointer"
              >
                <M3Tag size={20} className="text-teal-600" />
                <span>Survey Point</span>
              </button>
              <button
                onClick={() => handleAddElement('anchor')}
                className="flex flex-col items-center justify-center p-3 rounded-xl bg-muted/30 hover:bg-teal-500/10 hover:text-teal-600 transition-all text-xs font-semibold gap-1.5 text-center cursor-pointer"
              >
                <M3Beacon size={20} className="text-teal-600" />
                <span>Receiver Anchor</span>
              </button>
              <button
                onClick={() => handleAddElement('waypoint')}
                className="flex flex-col items-center justify-center p-3 rounded-xl bg-muted/30 hover:bg-emerald-500/10 hover:text-emerald-600 transition-all text-xs font-semibold gap-1.5 text-center cursor-pointer"
              >
                <M3Walk size={20} className="text-emerald-600" />
                <span>Walk Waypoint</span>
              </button>
              <button
                onClick={() => handleAddElement('obstacle')}
                className="flex flex-col items-center justify-center p-3 rounded-xl bg-muted/30 hover:bg-amber-500/10 hover:text-amber-600 transition-all text-xs font-semibold gap-1.5 text-center cursor-pointer"
              >
                <M3Wall size={20} className="text-amber-600" />
                <span>Obstacle Barrier</span>
              </button>
            </div>
          </div>

          {/* Efficiency & Automation Tools */}
          <div className="rounded-2xl bg-card p-4 shadow-sm space-y-3">
            <h4 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex items-center justify-between">
              <span>Efficiency Tools</span>
              <span className="text-teal-600 font-bold flex items-center gap-1">
                <M3Bolt size={14} />
                <span>Fast Survey</span>
              </span>
            </h4>
            <div className="space-y-2">
              <button
                onClick={() => handleGenerateGrid(false)}
                className="w-full flex items-center justify-between rounded-xl bg-muted/40 hover:bg-muted px-3 py-2 text-xs font-semibold transition-all cursor-pointer"
              >
                <span className="flex items-center gap-2">
                  <M3Grid size={16} className="text-teal-600" />
                  <span>Auto-Grid Entire Facility</span>
                </span>
                <span className="text-[10px] text-muted-foreground font-mono">{gridSpacingMeters}m</span>
              </button>

              {schematicRooms.length > 0 && (
                <button
                  onClick={() => handleGenerateGrid(true)}
                  className="w-full flex items-center justify-between rounded-xl bg-muted/40 hover:bg-muted px-3 py-2 text-xs font-semibold transition-all cursor-pointer"
                >
                  <span className="flex items-center gap-2">
                    <M3Grid size={16} className="text-teal-600" />
                    <span>Auto-Grid Selected Room</span>
                  </span>
                  <span className="text-[10px] text-muted-foreground font-mono">Room 1</span>
                </button>
              )}

              <button
                onClick={handleOptimizeRoute}
                className="w-full flex items-center justify-between rounded-xl bg-muted/40 hover:bg-muted px-3 py-2 text-xs font-semibold transition-all cursor-pointer"
              >
                <span className="flex items-center gap-2">
                  <M3Operations size={16} className="text-amber-600" />
                  <span>Optimize Shortest Walking Route</span>
                </span>
                <span className="text-[10px] text-emerald-600 font-bold font-mono">
                  {totalPathMeters}m
                </span>
              </button>

              <button
                onClick={() => {
                  setSurveyPoints([])
                  setWaypoints([])
                  setSelectedId(null)
                }}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-600 px-3 py-2 text-xs font-semibold transition-all cursor-pointer"
              >
                <M3Trash size={14} />
                <span>Clear All Survey Points</span>
              </button>
            </div>
          </div>

          {/* Visibility Toggles */}
          <div className="rounded-2xl bg-card p-4 shadow-sm space-y-2.5 text-xs">
            <h4 className="font-bold uppercase tracking-wider text-muted-foreground text-[10px]">
              Layer Visibility
            </h4>
            <div className="grid grid-cols-2 gap-2">
              <label className="flex items-center gap-1.5 cursor-pointer font-medium">
                <input
                  type="checkbox"
                  checked={showGrid}
                  onChange={(e) => setShowGrid(e.target.checked)}
                  className="rounded text-accent"
                />
                Metric Grid
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer font-medium">
                <input
                  type="checkbox"
                  checked={showRangeRings}
                  onChange={(e) => setShowRangeRings(e.target.checked)}
                  className="rounded text-accent"
                />
                Range Rings
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer font-medium">
                <input
                  type="checkbox"
                  checked={showRooms}
                  onChange={(e) => setShowRooms(e.target.checked)}
                  className="rounded text-accent"
                />
                Room Shells
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer font-medium">
                <input
                  type="checkbox"
                  checked={showPath}
                  onChange={(e) => setShowPath(e.target.checked)}
                  className="rounded text-accent"
                />
                Survey Walk Path
              </label>
            </div>
          </div>
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

                return (
                  <g
                    key={pt.id}
                    className="cursor-pointer"
                    onMouseDown={(e) => handleStartDrag(pt.id, 'survey_point', e)}
                  >
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
                return (
                  <g
                    key={anc.id}
                    className="cursor-pointer"
                    onMouseDown={(e) => handleStartDrag(anc.id, 'anchor', e)}
                  >
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
                    <text
                      x={anc.x}
                      y={anc.y + 3.6}
                      textAnchor="middle"
                      fontSize="2.0"
                      fontWeight="600"
                      fill="currentColor"
                      className="text-foreground pointer-events-none"
                    >
                      {anc.id}
                    </text>
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

        {/* Right Column: Dynamic Property Inspector & Distance Matrix */}
        <div className="space-y-4 lg:col-span-3">
          {/* Selected Item Properties */}
          <div className="rounded-2xl bg-card p-4 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-1">
              <h4 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                Property Inspector
              </h4>
              {selectedId && (
                <button
                  onClick={handleDeleteSelected}
                  className="text-rose-500 hover:text-rose-600 p-1.5 rounded-lg hover:bg-rose-500/10 transition-colors cursor-pointer"
                  title="Delete Selected Item"
                >
                  <M3Trash size={15} />
                </button>
              )}
            </div>

            {/* Survey Point Inspector */}
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

                {/* Euclidean Distance Matrix to Active Anchors */}
                <div className="pt-2">
                  <h5 className="font-bold text-muted-foreground text-[10px] uppercase tracking-wider mb-2 flex items-center justify-between">
                    <span>Anchor Distance Matrix</span>
                    <span className="text-[10px] text-teal-600 font-mono">Euclidean (m)</span>
                  </h5>
                  <div className="space-y-1.5 max-h-40 overflow-y-auto">
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
                </div>
              </div>
            )}

            {/* Anchor Inspector */}
            {selectedAnchor && (
              <div className="space-y-3 text-xs">
                <div>
                  <label className="font-semibold text-muted-foreground">Anchor Label</label>
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
              </div>
            )}

            {/* Obstacle Inspector */}
            {selectedObstacle && (
              <div className="space-y-3 text-xs">
                <div>
                  <label className="font-semibold text-muted-foreground">Obstacle Name</label>
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
                  <label className="font-semibold text-muted-foreground">Material Type</label>
                  <select
                    value={selectedObstacle.obstacleType}
                    onChange={(e) => {
                      const val = e.target.value as any
                      let att = 4.8
                      if (val === 'Wood') att = 3.2
                      if (val === 'Metal') att = 12.0
                      if (val === 'Concrete') att = 14.0
                      if (val === 'Human Body') att = 6.5
                      setObstacles((prev) =>
                        prev.map((o) =>
                          o.id === selectedObstacle.id
                            ? { ...o, obstacleType: val, attenuationDb: att }
                            : o
                        )
                      )
                    }}
                    className="w-full mt-1 rounded-xl bg-muted/40 px-3 py-1.5 text-foreground focus:bg-card focus:ring-2 focus:ring-accent"
                  >
                    <option value="Drywall">Drywall Partition</option>
                    <option value="Wood">Wooden Wall / Furniture</option>
                    <option value="Metal">Metal Cabinet / Pillar</option>
                    <option value="Concrete">Reinforced Concrete</option>
                    <option value="Human Body">Human Obstruction Zone</option>
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
                    max="20.0"
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
              </div>
            )}

            {/* Empty State Inspector */}
            {!selectedPoint && !selectedAnchor && !selectedObstacle && !selectedWaypoint && (
              <div className="py-6 text-center text-muted-foreground space-y-2">
                <M3Info size={24} className="mx-auto opacity-40" />
                <p>Click any survey point, anchor, or obstacle on the canvas to inspect its parameters.</p>
              </div>
            )}
          </div>

          {/* Quick Hardware Telemetry Summary */}
          <div className="rounded-2xl bg-card p-4 shadow-sm space-y-2.5 text-xs">
            <h4 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              Hardware Telemetry Target
            </h4>
            <div className="space-y-1.5 font-mono">
              <div className="flex justify-between">
                <span className="text-muted-foreground font-sans">Beacon MAC:</span>
                <span className="font-bold text-foreground">{targetMac}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground font-sans">Active Receivers:</span>
                <span className="text-emerald-600 font-bold">{anchors.length} Nodes</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground font-sans">Grid Resolution:</span>
                <span className="text-foreground font-bold">{gridSpacingMeters}m step</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
