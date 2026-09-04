import type { MapItem, SimState } from '../../lib/simulation'
import { canAccess, type UserRole } from '../../lib/rbac'
import { evaluateFacilityReadiness } from '../../lib/geometry'
import { M3CropSquare, M3Beacon, M3Warning, M3Admin } from '../common/MaterialIcon'
import { SpatialView } from './SpatialView'
import { TagDetail } from './TagDetail'

interface Props {
  sim: SimState
  mapItems: MapItem[]
  selected: string | null
  onSelect: (id: string | null) => void
  focus: string | null
  onFocus: (id: string | null) => void
  role?: UserRole
  onNavigateToSetup?: () => void
  onLoadDemoPreset?: () => void
}

export function MonitorView({
  sim,
  mapItems,
  selected,
  onSelect,
  focus,
  onFocus,
  role = 'admin',
  onNavigateToSetup,
  onLoadDemoPreset,
}: Props) {
  const selectedTag = sim.tags.find((t) => t.id === selected) ?? null
  const isAdmin = canAccess(role, 'admin')

  // Rigorous system readiness evaluation (no_rooms | no_anchors | invalid_geometry | ready)
  const readiness = evaluateFacilityReadiness(sim.geofences, sim.anchors, { width: 10, height: 10 })

  // If facility is not fully ready (e.g. no rooms, no anchors, or degenerate geometry),
  // do NOT display mock defaults. Show a dedicated, actionable onboarding screen.
  if (readiness.status !== 'ready') {
    const isNoRooms = readiness.status === 'no_rooms'
    const isNoAnchors = readiness.status === 'no_anchors'
    const isInvalidGeom = readiness.status === 'invalid_geometry'

    return (
      <div className="rounded-3xl bg-card p-8 sm:p-12 shadow-xl text-center max-w-3xl mx-auto my-8 space-y-8 animate-in fade-in zoom-in-95 duration-300">
        {/* Status Badge */}
        <div
          className={`inline-flex items-center gap-2 px-3.5 py-1 rounded-full font-mono text-xs font-semibold ${
            isNoRooms
              ? 'bg-rose-500/10 text-rose-500'
              : isNoAnchors
              ? 'bg-amber-500/10 text-amber-500'
              : 'bg-orange-500/10 text-orange-500'
          }`}
        >
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-current"></span>
          </span>
          {isNoRooms
            ? 'Setup Required · No Rooms Configured'
            : isNoAnchors
            ? 'Anchors Missing · Placement Required'
            : 'Degenerate Geometry · Solver Blocked'}
        </div>

        {/* Hero Header */}
        <div className="space-y-3 max-w-xl mx-auto">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-teal-500/10 flex items-center justify-center text-teal-600 dark:text-teal-400">
            {isNoRooms ? <M3CropSquare size={32} /> : isNoAnchors ? <M3Beacon size={32} /> : <M3Warning size={32} />}
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            {isNoRooms
              ? 'No Facility Layout Configured'
              : isNoAnchors
              ? 'Rooms Configured, But No Anchors Placed'
              : 'Anchor Layout Needs Adjustment'}
          </h2>
          <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
            {isNoRooms
              ? 'Your live positioning dashboard requires configured room boundaries and receiver anchors before tracking can begin. No default mock setup is loaded so you can configure your exact physical facility.'
              : isNoAnchors
              ? `You have configured ${readiness.roomCount} room(s), but haven't placed any BLE receiver anchors yet. Anchors are required to detect tag signals and compute multilateration positions.`
              : 'The positioning engine detected geometric conditioning issues that prevent reliable 2D multilateration:'}
          </p>

          {/* Issue Warnings for Degenerate Geometry */}
          {isInvalidGeom && readiness.issues.length > 0 && (
            <div className="rounded-2xl bg-amber-500/10 p-4 text-left font-mono text-xs text-amber-400 space-y-1.5 mt-4">
              {readiness.issues.map((iss, idx) => (
                <div key={idx} className="flex items-start gap-2">
                  <M3Warning size={14} className="text-amber-500 shrink-0 mt-0.5" />
                  <span>{iss}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Big Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
          <button
            onClick={() => (onNavigateToSetup ? onNavigateToSetup() : null)}
            className="w-full sm:w-auto px-8 py-4 rounded-2xl bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 text-white font-bold text-base shadow-xl shadow-teal-900/20 transition-all transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-3 cursor-pointer group"
          >
            {isNoRooms ? <M3CropSquare size={20} /> : isNoAnchors ? <M3Beacon size={20} /> : <M3Admin size={20} />}
            <span>
              {isNoRooms
                ? 'Open Floor Plan Designer'
                : isNoAnchors
                ? 'Plant Anchors in Floor Plan Designer'
                : 'Fix Geometry in Floor Plan Designer'}
            </span>
            <span className="transition-transform group-hover:translate-x-1 font-mono">→</span>
          </button>
        </div>

        {/* 3-Step Guided Workflow Preview */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-left pt-6">
          <div className="p-5 rounded-2xl bg-muted/40 space-y-2">
            <div className="text-[10px] font-mono font-bold tracking-wider text-teal-600 dark:text-teal-400">01. DESIGN ROOMS</div>
            <div className="font-bold text-sm text-foreground">Define Boundaries</div>
            <div className="text-xs text-muted-foreground leading-relaxed">Add rooms with physical metric dimensions or trace floor plans.</div>
          </div>
          <div className="p-5 rounded-2xl bg-muted/40 space-y-2">
            <div className="text-[10px] font-mono font-bold tracking-wider text-emerald-600 dark:text-emerald-400">02. AUTO CORNER NODES</div>
            <div className="font-bold text-sm text-foreground">Plant Receiver Anchors</div>
            <div className="text-xs text-muted-foreground leading-relaxed">Nodes automatically pin to the 4 corners of each room (or 3-node triangulation).</div>
          </div>
          <div className="p-5 rounded-2xl bg-muted/40 space-y-2">
            <div className="text-[10px] font-mono font-bold tracking-wider text-teal-600 dark:text-teal-400">03. LIVE TRACKING</div>
            <div className="font-bold text-sm text-foreground">Deploy to Positioning Engine</div>
            <div className="text-xs text-muted-foreground leading-relaxed">Deploy to activate real-time multilateration, geofencing, and live telemetry.</div>
          </div>
        </div>

        {/* Optional Demo Option for testing only */}
        {onLoadDemoPreset && (
          <div className="pt-2 text-xs text-muted-foreground">
            Want to test system capabilities with sample data?{' '}
            <button
              onClick={onLoadDemoPreset}
              className="text-teal-600 dark:text-teal-400 hover:underline font-semibold cursor-pointer"
            >
              Load 4-Room Demo Preset
            </button>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Admin Quick Launcher Bar */}
      {isAdmin && onNavigateToSetup && (
        <div className="flex justify-end">
          <button
            onClick={onNavigateToSetup}
            className="rounded-xl bg-card hover:bg-panel px-3.5 py-2 text-xs font-semibold text-foreground transition-all shadow-sm hover:shadow-md flex items-center gap-2 focus-visible:outline-2 focus-visible:outline-accent cursor-pointer"
          >
            <M3CropSquare size={15} className="text-accent" />
            <span>Floor Plan Designer</span>
          </button>
        </div>
      )}

      {/* Hero Spatial View & Detail Panel */}
      <div className={`grid grid-cols-1 gap-6 ${selectedTag ? 'xl:grid-cols-[1fr_360px]' : ''}`}>
        <SpatialView sim={sim} mapItems={mapItems} selected={selected} onSelect={onSelect} focus={focus} onFocus={onFocus} />
        {selectedTag && (
          <div className="space-y-6">
            <TagDetail tag={selectedTag} anchors={sim.anchors} />
          </div>
        )}
      </div>
    </div>
  )
}
