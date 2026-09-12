import { useState, useMemo } from 'react'
import type { MapItem } from '../../lib/simulation'
import type { SchematicAnchor, SchematicRoom, SchematicData } from './FloorEditor'
import {
  M3Building,
  M3Business,
  M3Beacon,
  M3Deploy,
  M3Check,
  M3Sparkles,
  M3Grid,
  M3Tag,
  M3Monitor,
  M3Info,
  M3Bolt,
} from '../common/MaterialIcon'
import { CollectorCollapsible } from '../collector/CollectorCollapsible'

export interface CasualSetupProps {
  mapItems: MapItem[]
  onMapItems: (items: MapItem[]) => void
  onSwitchToEngineerMode?: () => void
  onNavigateToMonitor?: () => void
  onLaunchTour?: () => void
}

type SpacePreset = 'single_room' | 'two_rooms' | 'complex' | 'warehouse' | 'custom'
type AnchorLayout = 'four_corners' | 'three_perimeter' | 'center_proximity'
type EnvironmentType = 'open' | 'office' | 'warehouse'

interface SpacePresetOption {
  id: SpacePreset
  name: string
  dims: { width: number; height: number }
  description: string
  icon: string
  roomCount: number
}

const SPACE_PRESETS: SpacePresetOption[] = [
  {
    id: 'single_room',
    name: 'Single Studio / Office',
    dims: { width: 5, height: 5 },
    description: 'A cozy single room, meeting suite, or retail booth.',
    icon: '🏠',
    roomCount: 1,
  },
  {
    id: 'two_rooms',
    name: '2-Room Office Suite',
    dims: { width: 10, height: 10 },
    description: 'Open workspace and private conference room divided by a wall.',
    icon: '🏢',
    roomCount: 2,
  },
  {
    id: 'complex',
    name: '4-Room Smart Complex',
    dims: { width: 10, height: 10 },
    description: 'Executive suite, boardroom, operations hub, and entrance.',
    icon: '🏬',
    roomCount: 4,
  },
  {
    id: 'warehouse',
    name: 'Open Warehouse / Hall',
    dims: { width: 20, height: 15 },
    description: 'Large open floor with high ceilings, aisles, or showroom spaces.',
    icon: '🏭',
    roomCount: 1,
  },
]

export function CasualSetup({
  onMapItems,
  onSwitchToEngineerMode,
  onNavigateToMonitor,
  onLaunchTour,
}: CasualSetupProps) {
  // 1. Space selection state
  const [selectedPreset, setSelectedPreset] = useState<SpacePreset>('single_room')
  const [customDims, setCustomDims] = useState({ width: 8, height: 6 })
  const [facilityName, setFacilityName] = useState('My Tracked Space')

  // 2. Hardware anchor layout
  const [anchorLayout, setAnchorLayout] = useState<AnchorLayout>('four_corners')

  // 3. Environment type (replaces path loss exponent & dB attenuation)
  const [envType, setEnvType] = useState<EnvironmentType>('office')

  // 4. Interactive Test Tag on the preview canvas
  const [testTagPos, setTestTagPos] = useState({ xPct: 50, yPct: 50 })
  const [isDraggingTag, setIsDraggingTag] = useState(false)

  // 5. Feedback status
  const [feedback, setFeedback] = useState<{ msg: string; type: 'success' | 'info' } | null>(null)
  const [isApplying, setIsApplying] = useState(false)
  const [isApplied, setIsApplied] = useState(false)

  // Active space dimensions
  const activeDims = useMemo(() => {
    if (selectedPreset === 'custom') return customDims
    const preset = SPACE_PRESETS.find((p) => p.id === selectedPreset)
    return preset ? preset.dims : { width: 10, height: 10 }
  }, [selectedPreset, customDims])

  // Computed anchors based on space dimensions and layout
  const computedAnchors = useMemo<SchematicAnchor[]>(() => {
    const tx = envType === 'open' ? -72.0 : envType === 'office' ? -77.8 : -82.0
    if (anchorLayout === 'four_corners') {
      return [
        {
          id: 'ANCHOR_01',
          label: 'Front-Left Corner',
          x: 10,
          y: 15,
          corner: 'top-left',
          placement: 'corner',
          txPower: tx,
          channel: 37,
          host: true,
        },
        {
          id: 'ANCHOR_02',
          label: 'Front-Right Corner',
          x: 90,
          y: 15,
          corner: 'top-right',
          placement: 'corner',
          txPower: tx,
          channel: 38,
          host: false,
        },
        {
          id: 'ANCHOR_03',
          label: 'Back-Left Corner',
          x: 10,
          y: 85,
          corner: 'bottom-left',
          placement: 'corner',
          txPower: tx,
          channel: 39,
          host: false,
        },
        {
          id: 'ANCHOR_04',
          label: 'Back-Right Corner',
          x: 90,
          y: 85,
          corner: 'bottom-right',
          placement: 'corner',
          txPower: tx,
          channel: 37,
          host: false,
        },
      ]
    } else if (anchorLayout === 'three_perimeter') {
      return [
        {
          id: 'ANCHOR_01',
          label: 'Front-Center Node',
          x: 50,
          y: 15,
          corner: 'top-center',
          placement: 'triangulation',
          txPower: tx,
          channel: 37,
          host: true,
        },
        {
          id: 'ANCHOR_02',
          label: 'Back-Left Node',
          x: 15,
          y: 85,
          corner: 'bottom-left',
          placement: 'triangulation',
          txPower: tx,
          channel: 38,
          host: false,
        },
        {
          id: 'ANCHOR_03',
          label: 'Back-Right Node',
          x: 85,
          y: 85,
          corner: 'bottom-right',
          placement: 'triangulation',
          txPower: tx,
          channel: 39,
          host: false,
        },
      ]
    } else {
      return [
        {
          id: 'ANCHOR_01',
          label: 'Center Ceiling Node',
          x: 50,
          y: 50,
          corner: 'center',
          placement: 'proximity_center',
          txPower: tx,
          channel: 37,
          host: true,
        },
      ]
    }
  }, [anchorLayout, envType])

  // Computed rooms based on preset
  const computedRooms = useMemo<SchematicRoom[]>(() => {
    if (selectedPreset === 'single_room' || selectedPreset === 'warehouse' || selectedPreset === 'custom') {
      return [
        {
          id: 'main_space',
          name: facilityName || 'Main Space',
          x: 5,
          y: 5,
          w: 90,
          h: 90,
          restricted: false,
          allow: [],
          nodeCount: computedAnchors.length as 1 | 3 | 4,
        },
      ]
    } else if (selectedPreset === 'two_rooms') {
      return [
        {
          id: 'room_1',
          name: 'Open Workspace',
          x: 5,
          y: 5,
          w: 43,
          h: 90,
          restricted: false,
          allow: [],
          nodeCount: 4,
        },
        {
          id: 'room_2',
          name: 'Conference Room',
          x: 52,
          y: 5,
          w: 43,
          h: 90,
          restricted: false,
          allow: [],
          nodeCount: 4,
        },
      ]
    } else {
      // 4-Room Complex
      return [
        { id: 'room_a', name: 'Executive Suite', x: 5, y: 5, w: 42, h: 42, restricted: false, allow: [], nodeCount: 4 },
        { id: 'room_b', name: 'Meeting Room', x: 53, y: 5, w: 42, h: 42, restricted: false, allow: [], nodeCount: 4 },
        { id: 'room_c', name: 'Operations Hub', x: 5, y: 53, w: 42, h: 42, restricted: false, allow: [], nodeCount: 4 },
        { id: 'room_d', name: 'Lobby & Reception', x: 53, y: 53, w: 42, h: 42, restricted: false, allow: [], nodeCount: 4 },
      ]
    }
  }, [selectedPreset, facilityName, computedAnchors.length])

  // Computed partition walls based on preset and environment
  const computedWalls = useMemo<MapItem[]>(() => {
    const attenuation = envType === 'open' ? 3 : envType === 'office' ? 8 : 14
    if (selectedPreset === 'two_rooms') {
      return [
        { id: 'w1', kind: 'wall', label: 'Dividing Wall', x: 49, y: 5, w: 2, h: 90, attenuation },
        { id: 'd1', kind: 'door', label: 'Connecting Door', x: 48, y: 45, w: 4, h: 10, attenuation: 0 },
      ]
    } else if (selectedPreset === 'complex') {
      return [
        { id: 'w1', kind: 'wall', label: 'Central Vertical Wall', x: 48, y: 5, w: 4, h: 90, attenuation },
        { id: 'w2', kind: 'wall', label: 'Central Horizontal Wall', x: 5, y: 48, w: 90, h: 4, attenuation },
        { id: 'd1', kind: 'door', label: 'North Corridor Door', x: 47, y: 22, w: 6, h: 6, attenuation: 0 },
        { id: 'd2', kind: 'door', label: 'South Corridor Door', x: 47, y: 72, w: 6, h: 6, attenuation: 0 },
      ]
    }
    return []
  }, [selectedPreset, envType])

  // Calculate real-time distance from test tag to anchors
  const testTagMeters = useMemo(() => {
    return {
      x: (testTagPos.xPct / 100) * activeDims.width,
      y: (testTagPos.yPct / 100) * activeDims.height,
    }
  }, [testTagPos, activeDims])

  const anchorDistances = useMemo(() => {
    return computedAnchors.map((anc) => {
      const ancM = {
        x: (anc.x / 100) * activeDims.width,
        y: (anc.y / 100) * activeDims.height,
      }
      const dist = Math.hypot(ancM.x - testTagMeters.x, ancM.y - testTagMeters.y)
      return {
        id: anc.id,
        label: anc.label,
        distanceM: Math.round(dist * 10) / 10,
        signalRating: dist < 3 ? 'Excellent' : dist < 7 ? 'Good' : 'Moderate',
      }
    })
  }, [computedAnchors, activeDims, testTagMeters])

  // Handle Dragging Test Tag
  const handleSvgMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!isDraggingTag) return
    const rect = e.currentTarget.getBoundingClientRect()
    const xPct = Math.max(5, Math.min(95, Math.round(((e.clientX - rect.left) / rect.width) * 100)))
    const yPct = Math.max(5, Math.min(95, Math.round(((e.clientY - rect.top) / rect.height) * 100)))
    setTestTagPos({ xPct, yPct })
  }

  const handleSvgClick = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const xPct = Math.max(5, Math.min(95, Math.round(((e.clientX - rect.left) / rect.width) * 100)))
    const yPct = Math.max(5, Math.min(95, Math.round(((e.clientY - rect.top) / rect.height) * 100)))
    setTestTagPos({ xPct, yPct })
  }

  // Deploy / Apply Setup
  const handleApplySetup = async () => {
    setIsApplying(true)
    const schematicData: SchematicData = {
      name: facilityName,
      dimensions: { width: activeDims.width, height: activeDims.height, unit: 'meters' },
      blueprint: null,
      blueprintOpacity: 0.35,
      anchors: computedAnchors,
      rooms: computedRooms,
      walls: computedWalls,
    }

    try {
      // 1. Save to local storage for offline / immediate sync
      localStorage.setItem('rtls_schematic_name', facilityName)
      localStorage.setItem('rtls_schematic_dims', JSON.stringify({ width: activeDims.width, height: activeDims.height, unit: 'meters' }))
      localStorage.setItem('rtls_schematic_rooms', JSON.stringify(computedRooms))
      localStorage.setItem('rtls_schematic_anchors', JSON.stringify(computedAnchors))
      localStorage.setItem('rtls_schematic_walls', JSON.stringify(computedWalls))

      // 2. Update memory state for immediate visual sync
      onMapItems(computedWalls)

      // 3. Deploy to FastAPI RTLS backend if available
      try {
        await fetch('/api/schematic', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(schematicData),
        })
      } catch {
        // Safe in offline / mock demo mode
      }

      setIsApplied(true)
      setFeedback({
        msg: `Setup applied successfully! Configured ${computedRooms.length} room(s) and ${computedAnchors.length} anchor node(s).`,
        type: 'success',
      })
    } catch {
      setFeedback({
        msg: 'Failed to apply configuration. Please check browser storage permissions.',
        type: 'info',
      })
    } finally {
      setIsApplying(false)
    }
  }

  return (
    <div className="space-y-5">
      {/* 1. Hero Friendly Banner */}
      <div className="rounded-3xl border border-teal-500/30 bg-gradient-to-br from-teal-950/20 via-card to-card p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-teal-500/15 text-teal-600 dark:text-teal-400 shadow-inner">
              <M3Sparkles size={28} />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h2 className="text-lg font-bold tracking-tight text-foreground">
                  Quick Space Setup
                </h2>
                <span className="rounded-full bg-teal-500/15 px-2.5 py-0.5 text-[11px] font-bold text-teal-700 dark:text-teal-300 border border-teal-500/20">
                  Casual Mode
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-1 max-w-xl">
                Configure your tracking facility in seconds with simple visual choices. No coordinate geometry, dB equations, or complex engineering required.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {onLaunchTour && (
              <button
                type="button"
                onClick={onLaunchTour}
                className="flex items-center gap-1.5 rounded-xl border border-teal-500/40 bg-teal-500/10 hover:bg-teal-500/20 px-3 py-2 text-xs font-bold text-teal-700 dark:text-teal-300 transition-all cursor-pointer shadow-xs"
                title="Launch game-like interactive quest walkthrough"
              >
                <span>🎮</span>
                <span>Quest Guide</span>
              </button>
            )}

            {onSwitchToEngineerMode && (
              <button
                type="button"
                onClick={onSwitchToEngineerMode}
                className="flex items-center gap-1.5 rounded-xl border border-border/60 bg-muted/40 hover:bg-muted px-3 py-2 text-xs font-semibold text-foreground transition-all cursor-pointer"
                title="Switch to full technical CAD designer and ML calibration tables"
              >
                <M3Grid size={15} className="text-muted-foreground" />
                <span>Engineer Mode</span>
              </button>
            )}

            <button
              type="button"
              onClick={handleApplySetup}
              disabled={isApplying}
              className="flex items-center gap-2 rounded-xl bg-teal-600 hover:bg-teal-700 text-white px-5 py-2 text-xs font-bold transition-all shadow-sm cursor-pointer disabled:opacity-50"
            >
              <M3Deploy size={16} />
              <span>{isApplying ? 'Applying...' : 'Apply & Activate Setup'}</span>
            </button>
          </div>
        </div>

        {/* Feedback Alert */}
        {feedback && (
          <div className="mt-4 flex items-center justify-between gap-2 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 px-4 py-2.5 text-xs font-semibold text-emerald-700 dark:text-emerald-300 animate-in fade-in duration-200">
            <div className="flex items-center gap-2">
              <M3Check size={16} />
              <span>{feedback.msg}</span>
            </div>
            {onNavigateToMonitor && (
              <button
                type="button"
                onClick={onNavigateToMonitor}
                className="rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1 text-xs font-bold cursor-pointer transition-all shadow-xs"
              >
                Open Live Monitor →
              </button>
            )}
          </div>
        )}
      </div>

      {/* 2. Main Setup Grid: Steps on Left, Live Preview on Right */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
        {/* Left Column: 3 Simple Setup Cards */}
        <div className="space-y-4 lg:col-span-7">
          {/* STEP 1: Space & Dimensions */}
          <div id="tour-casual-space" className="rounded-2xl transition-all">
            <CollectorCollapsible
              title="Step 1: Choose Your Space"
              icon={<M3Building size={16} />}
              defaultOpen={true}
              badge={
                <span className="text-[10px] font-mono font-bold text-teal-600">
                  {activeDims.width}m × {activeDims.height}m
                </span>
              }
            >
            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-muted-foreground block mb-1">Facility / Space Name</label>
                <input
                  type="text"
                  value={facilityName}
                  onChange={(e) => setFacilityName(e.target.value)}
                  placeholder="e.g. Innovation Lab, Main Office, Retail Store"
                  className="w-full rounded-xl bg-muted/40 px-3 py-2 text-xs font-medium text-foreground focus:bg-card focus:ring-2 focus:ring-teal-500"
                />
              </div>

              {/* Space Preset Cards */}
              <div className="grid grid-cols-2 gap-2.5">
                {SPACE_PRESETS.map((preset) => {
                  const isSel = selectedPreset === preset.id
                  return (
                    <div
                      key={preset.id}
                      onClick={() => setSelectedPreset(preset.id)}
                      className={`p-3 rounded-2xl border transition-all cursor-pointer select-none ${
                        isSel
                          ? 'border-teal-500 bg-teal-500/10 shadow-xs'
                          : 'border-border/50 bg-card hover:bg-muted/40 hover:border-border'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xl">{preset.icon}</span>
                        <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-muted text-muted-foreground">
                          {preset.dims.width} × {preset.dims.height}m
                        </span>
                      </div>
                      <div className="font-bold text-foreground text-xs mt-1.5">{preset.name}</div>
                      <p className="text-[11px] text-muted-foreground mt-0.5 leading-snug line-clamp-2">
                        {preset.description}
                      </p>
                    </div>
                  )
                })}
              </div>

              {/* Custom Size Toggle */}
              <div className="pt-2 border-t border-border/30">
                <button
                  type="button"
                  onClick={() => setSelectedPreset('custom')}
                  className={`text-xs font-semibold flex items-center gap-1.5 cursor-pointer ${
                    selectedPreset === 'custom' ? 'text-teal-600 font-bold' : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <span>✏️ Enter Custom Dimensions</span>
                  {selectedPreset === 'custom' && <span>(Active)</span>}
                </button>

                {selectedPreset === 'custom' && (
                  <div className="grid grid-cols-2 gap-3 mt-2">
                    <div>
                      <span className="text-[10px] text-muted-foreground font-medium block mb-1">Width (X Axis)</span>
                      <div className="flex items-center gap-1.5">
                        <input
                          type="number"
                          min="3"
                          max="50"
                          value={customDims.width}
                          onChange={(e) => setCustomDims({ ...customDims, width: Math.max(3, Number(e.target.value)) })}
                          className="w-full rounded-xl bg-muted/40 px-3 py-1.5 text-xs font-mono font-bold text-foreground focus:ring-2 focus:ring-teal-500"
                        />
                        <span className="text-muted-foreground font-mono">m</span>
                      </div>
                    </div>

                    <div>
                      <span className="text-[10px] text-muted-foreground font-medium block mb-1">Length (Y Axis)</span>
                      <div className="flex items-center gap-1.5">
                        <input
                          type="number"
                          min="3"
                          max="50"
                          value={customDims.height}
                          onChange={(e) => setCustomDims({ ...customDims, height: Math.max(3, Number(e.target.value)) })}
                          className="w-full rounded-xl bg-muted/40 px-3 py-1.5 text-xs font-mono font-bold text-foreground focus:ring-2 focus:ring-teal-500"
                        />
                        <span className="text-muted-foreground font-mono">m</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </CollectorCollapsible>
          </div>

          {/* STEP 2: Anchor Placement Choice */}
          <div id="tour-casual-anchors" className="rounded-2xl transition-all">
            <CollectorCollapsible
              title="Step 2: Tracking Boxes Placement"
              icon={<M3Beacon size={16} />}
              defaultOpen={true}
              badge={
                <span className="text-[10px] font-mono font-bold text-teal-600">
                  {computedAnchors.length} Nodes
                </span>
              }
            >
            <div className="space-y-3 text-xs">
              <p className="text-muted-foreground leading-relaxed">
                Where are your hardware receiver anchors mounted? Select your layout to automatically place them:
              </p>

              <div className="space-y-2">
                {/* 4 Corners */}
                <div
                  onClick={() => setAnchorLayout('four_corners')}
                  className={`p-3 rounded-2xl border transition-all cursor-pointer flex items-start gap-3 ${
                    anchorLayout === 'four_corners'
                      ? 'border-teal-500 bg-teal-500/10 shadow-xs'
                      : 'border-border/50 bg-card hover:bg-muted/40 hover:border-border'
                  }`}
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-teal-500/20 text-teal-600 font-bold shrink-0">
                    ⭐
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-foreground">4-Corner Coverage (Recommended)</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-teal-500/20 text-teal-700 dark:text-teal-300 font-bold">
                        Best Accuracy
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                      Place one anchor box in each of the four corners. Provides complete 2D triangulation across the whole floor.
                    </p>
                  </div>
                </div>

                {/* 3 Nodes Perimeter */}
                <div
                  onClick={() => setAnchorLayout('three_perimeter')}
                  className={`p-3 rounded-2xl border transition-all cursor-pointer flex items-start gap-3 ${
                    anchorLayout === 'three_perimeter'
                      ? 'border-teal-500 bg-teal-500/10 shadow-xs'
                      : 'border-border/50 bg-card hover:bg-muted/40 hover:border-border'
                  }`}
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-indigo-500/20 text-indigo-600 font-bold shrink-0">
                    🔺
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-foreground">3-Node Triangular Perimeter</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-muted text-muted-foreground font-semibold">
                        3 Anchors
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                      Place three anchors around the walls forming a triangle. Good for small spaces and cost savings.
                    </p>
                  </div>
                </div>

                {/* Single Node Presence */}
                <div
                  onClick={() => setAnchorLayout('center_proximity')}
                  className={`p-3 rounded-2xl border transition-all cursor-pointer flex items-start gap-3 ${
                    anchorLayout === 'center_proximity'
                      ? 'border-teal-500 bg-teal-500/10 shadow-xs'
                      : 'border-border/50 bg-card hover:bg-muted/40 hover:border-border'
                  }`}
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-amber-500/20 text-amber-600 font-bold shrink-0">
                    📍
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-foreground">Single Center Node</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-muted text-muted-foreground font-semibold">
                        1 Anchor
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                      Place one anchor in the center of the space. Detects whether people/assets are inside or nearby.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </CollectorCollapsible>
          </div>

          {/* STEP 3: Environment Type (No Math or Decibels) */}
          <div id="tour-casual-env" className="rounded-2xl transition-all">
            <CollectorCollapsible
              title="Step 3: Space Environment"
              icon={<M3Business size={16} />}
              defaultOpen={true}
              badge={
                <span className="text-[10px] font-mono font-bold text-teal-600 capitalize">
                  {envType} Space
                </span>
              }
            >
            <div className="space-y-3 text-xs">
              <p className="text-muted-foreground leading-relaxed">
                What does your space look like? This sets the wireless signal calibration automatically:
              </p>

              <div className="grid grid-cols-3 gap-2">
                {/* Open */}
                <div
                  onClick={() => setEnvType('open')}
                  className={`p-3 rounded-2xl border text-center transition-all cursor-pointer select-none ${
                    envType === 'open'
                      ? 'border-teal-500 bg-teal-500/10 shadow-xs'
                      : 'border-border/50 bg-card hover:bg-muted/40 hover:border-border'
                  }`}
                >
                  <div className="text-2xl mb-1">🛋️</div>
                  <div className="font-bold text-foreground text-xs">Open Space</div>
                  <div className="text-[10px] text-muted-foreground mt-0.5 leading-tight">
                    Living rooms, open halls, minimal walls.
                  </div>
                </div>

                {/* Office */}
                <div
                  onClick={() => setEnvType('office')}
                  className={`p-3 rounded-2xl border text-center transition-all cursor-pointer select-none ${
                    envType === 'office'
                      ? 'border-teal-500 bg-teal-500/10 shadow-xs'
                      : 'border-border/50 bg-card hover:bg-muted/40 hover:border-border'
                  }`}
                >
                  <div className="text-2xl mb-1">🚪</div>
                  <div className="font-bold text-foreground text-xs">Standard Office</div>
                  <div className="text-[10px] text-muted-foreground mt-0.5 leading-tight">
                    Drywall partitions, doors, cubicles.
                  </div>
                </div>

                {/* Warehouse */}
                <div
                  onClick={() => setEnvType('warehouse')}
                  className={`p-3 rounded-2xl border text-center transition-all cursor-pointer select-none ${
                    envType === 'warehouse'
                      ? 'border-teal-500 bg-teal-500/10 shadow-xs'
                      : 'border-border/50 bg-card hover:bg-muted/40 hover:border-border'
                  }`}
                >
                  <div className="text-2xl mb-1">🧱</div>
                  <div className="font-bold text-foreground text-xs">Dense Space</div>
                  <div className="text-[10px] text-muted-foreground mt-0.5 leading-tight">
                    Concrete walls, metal shelves, inventory.
                  </div>
                </div>
              </div>
            </div>
          </CollectorCollapsible>
          </div>
        </div>

        {/* Right Column: Live Interactive Preview & Test Tag Canvas */}
        <div className="space-y-4 lg:col-span-5">
          <div id="tour-casual-preview" className="rounded-3xl border border-border/50 bg-card p-4 shadow-sm space-y-3 transition-all">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5">
                  <M3Monitor size={16} className="text-teal-600" />
                  <span>Interactive Room Preview</span>
                </h3>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  Click or drag the <strong>Badge</strong> to test live tracking!
                </p>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-teal-500/15 text-teal-700 dark:text-teal-300 font-bold">
                Live Simulation
              </span>
            </div>

            {/* Interactive SVG Canvas */}
            <div className="relative aspect-square w-full rounded-2xl bg-muted/20 border border-border/40 overflow-hidden select-none">
              <svg
                viewBox="0 0 100 100"
                className="w-full h-full cursor-crosshair"
                onClick={handleSvgClick}
                onMouseMove={handleSvgMouseMove}
                onMouseUp={() => setIsDraggingTag(false)}
                onMouseLeave={() => setIsDraggingTag(false)}
              >
                {/* Background Room Shells */}
                {computedRooms.map((r) => (
                  <g key={r.id}>
                    <rect
                      x={r.x}
                      y={r.y}
                      width={r.w}
                      height={r.h}
                      rx="3"
                      fill="rgba(13, 148, 136, 0.08)"
                      stroke="rgba(13, 148, 136, 0.35)"
                      strokeWidth="0.8"
                    />
                    <text
                      x={r.x + r.w / 2}
                      y={r.y + r.h / 2}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fontSize="3.2"
                      fontWeight="700"
                      fill="currentColor"
                      className="text-foreground/70 pointer-events-none"
                    >
                      {r.name}
                    </text>
                  </g>
                ))}

                {/* Partition Walls */}
                {computedWalls.map((w) => (
                  <rect
                    key={w.id}
                    x={w.x}
                    y={w.y}
                    width={w.w}
                    height={w.h}
                    rx="1"
                    fill={w.kind === 'door' ? '#0d9488' : '#64748b'}
                    fillOpacity={w.kind === 'door' ? '0.3' : '0.6'}
                  />
                ))}

                {/* Range Rings & Anchors */}
                {computedAnchors.map((anc) => (
                  <g key={anc.id}>
                    {/* Signal coverage halo */}
                    <circle
                      cx={anc.x}
                      cy={anc.y}
                      r="14"
                      fill="rgba(20, 184, 166, 0.05)"
                      stroke="rgba(20, 184, 166, 0.25)"
                      strokeWidth="0.4"
                      strokeDasharray="2,2"
                    />
                    {/* Anchor Marker */}
                    <circle
                      cx={anc.x}
                      cy={anc.y}
                      r="2.8"
                      fill="#0d9488"
                      stroke="#ffffff"
                      strokeWidth="0.8"
                    />
                    <text
                      x={anc.x}
                      y={anc.y - 4}
                      textAnchor="middle"
                      fontSize="2.2"
                      fontWeight="bold"
                      fill="currentColor"
                      className="text-foreground font-mono"
                    >
                      {anc.label.split(' ')[0]}
                    </text>
                  </g>
                ))}

                {/* Distance lines to test tag */}
                {computedAnchors.map((anc) => (
                  <line
                    key={`line_${anc.id}`}
                    x1={anc.x}
                    y1={anc.y}
                    x2={testTagPos.xPct}
                    y2={testTagPos.yPct}
                    stroke="rgba(20, 184, 166, 0.3)"
                    strokeWidth="0.3"
                    strokeDasharray="1,1"
                  />
                ))}

                {/* Interactive Test Tag */}
                <g
                  className="cursor-grab active:cursor-grabbing"
                  onMouseDown={(e) => {
                    e.stopPropagation()
                    setIsDraggingTag(true)
                  }}
                >
                  <circle
                    cx={testTagPos.xPct}
                    cy={testTagPos.yPct}
                    r="4.5"
                    fill="rgba(99, 102, 241, 0.2)"
                    className="animate-ping"
                  />
                  <circle
                    cx={testTagPos.xPct}
                    cy={testTagPos.yPct}
                    r="3.2"
                    fill="#6366f1"
                    stroke="#ffffff"
                    strokeWidth="0.8"
                  />
                  <text
                    x={testTagPos.xPct}
                    y={testTagPos.yPct + 0.8}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize="2.4"
                    fill="#ffffff"
                    fontWeight="bold"
                    className="pointer-events-none"
                  >
                    🏷️
                  </text>
                  <text
                    x={testTagPos.xPct}
                    y={testTagPos.yPct + 6.5}
                    textAnchor="middle"
                    fontSize="2.2"
                    fill="currentColor"
                    fontWeight="700"
                    className="text-foreground font-mono"
                  >
                    Test Tag ({testTagMeters.x.toFixed(1)}m, {testTagMeters.y.toFixed(1)}m)
                  </text>
                </g>
              </svg>
            </div>

            {/* Real-time Distance Readout */}
            <div className="space-y-1.5 pt-1 text-xs font-mono">
              <div className="flex items-center justify-between text-[11px] pb-1 border-b border-border/30 font-sans">
                <span className="font-bold text-foreground">Simulated Distances:</span>
                <span className="text-teal-600 font-semibold">Drag tag to test</span>
              </div>
              <div className="grid grid-cols-2 gap-1.5">
                {anchorDistances.map((ad) => (
                  <div
                    key={ad.id}
                    className="flex items-center justify-between p-1.5 rounded-xl bg-muted/40 border border-border/30 text-[11px]"
                  >
                    <span className="text-muted-foreground font-sans truncate max-w-[90px]">{ad.label}</span>
                    <span className="font-bold text-foreground">{ad.distanceM || 0}m</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Bottom Apply Action */}
            <div id="tour-casual-activate" className="pt-2 border-t border-border/30 transition-all rounded-2xl">
              <button
                type="button"
                onClick={handleApplySetup}
                disabled={isApplying}
                className="w-full flex items-center justify-center gap-2 rounded-2xl bg-teal-600 hover:bg-teal-700 text-white p-3 text-xs font-bold transition-all shadow-sm cursor-pointer disabled:opacity-50"
              >
                <M3Check size={18} />
                <span>
                  {isApplied ? 'Setup Configured & Live! Apply Again' : 'Confirm & Activate Space'}
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
