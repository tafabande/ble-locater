import { useEffect, useState } from 'react'
import { useSimulation, DEFAULT_MAP, buildPipeline, type MapItem, type Tag, type SimState } from './lib/simulation'
import { useLiveSource, EMPTY_STATE, type Mode } from './lib/datasource'
import { AppShell, type View } from './components/AppShell'
import { MonitorView } from './components/monitor/MonitorView'
import { CollectorView } from './components/collector/CollectorView'
import { AdminView } from './components/admin/AdminView'
import { ReportsView } from './components/reports/ReportsView'
import { ConnectionScreen } from './components/ConnectionScreen'
import { AlertToasts } from './components/AlertToasts'
import { ErrorDiagnosticBanner } from './components/ErrorDiagnosticBanner'
import { canAccess, type UserRole } from './lib/rbac'
import { TEMPLATES } from './components/admin/FloorEditor'

const DEFAULT_ENDPOINT = '/api/state'

export default function App() {
  const [view, setView] = useState<View>('monitor')
  const [mode, setMode] = useState<Mode>(() => {
    const saved = localStorage.getItem('fleetview-mode') as Mode
    return saved === 'demo' || saved === 'live' ? saved : 'live'
  })
  const [simulationEnabled, setSimulationEnabled] = useState<boolean>(() => {
    const saved = localStorage.getItem('rtls_simulation_enabled')
    return saved !== null ? saved === 'true' : true
  })
  const [selected, setSelected] = useState<string | null>(null)
  const [focus, setFocus] = useState<string | null>(null)
  const [interval, setIntervalMs] = useState(2500)
  const [endpoint, setEndpoint] = useState(DEFAULT_ENDPOINT)
  const [role, setRole] = useState<UserRole>(() => (localStorage.getItem('fleetview-role') as UserRole) || 'operator')
  const [mapItems, setMapItems] = useState<MapItem[]>(() => {
    try {
      const saved = localStorage.getItem('rtls_schematic_walls')
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  })
  const [schematicRooms, setSchematicRooms] = useState<any[]>(() => {
    try {
      const saved = localStorage.getItem('rtls_schematic_rooms')
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  })
  const [schematicAnchors, setSchematicAnchors] = useState<any[]>(() => {
    try {
      const saved = localStorage.getItem('rtls_schematic_anchors')
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  })
  const [now, setNow] = useState(Date.now())
  const [adminOpens, setAdminOpens] = useState(0)

  // Keep schematic in sync with localStorage and backend when navigating
  useEffect(() => {
    try {
      const r = localStorage.getItem('rtls_schematic_rooms')
      const a = localStorage.getItem('rtls_schematic_anchors')
      const w = localStorage.getItem('rtls_schematic_walls')
      if (r) setSchematicRooms(JSON.parse(r))
      if (a) setSchematicAnchors(JSON.parse(a))
      if (w) setMapItems(JSON.parse(w))
    } catch {}

    fetch('/api/schematic')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && Array.isArray(data.rooms) && data.rooms.length > 0) {
          setSchematicRooms(data.rooms)
          if (Array.isArray(data.anchors)) setSchematicAnchors(data.anchors)
          if (Array.isArray(data.walls)) setMapItems(data.walls)
        }
      })
      .catch(() => {})
  }, [view])

  const demo = useSimulation(interval, simulationEnabled || mode === 'demo', mapItems, schematicAnchors, schematicRooms)
  const live = useLiveSource(mode === 'live', endpoint, interval)

  useEffect(() => {
    const iv = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(iv)
  }, [])

  // Surface open alerts as toasts whenever the operator opens the admin panel.
  useEffect(() => {
    if (view === 'admin') setAdminOpens((n) => n + 1)
  }, [view])

  useEffect(() => {
    localStorage.setItem('fleetview-role', role)
    if (view === 'admin' && !canAccess(role, 'admin')) setView('monitor')
  }, [role, view])

  useEffect(() => {
    localStorage.setItem('fleetview-mode', mode)
  }, [mode])

  useEffect(() => {
    localStorage.setItem('rtls_simulation_enabled', String(simulationEnabled))
  }, [simulationEnabled])

  // Base anchors and geofences
  const baseAnchors = live.state?.anchors?.length
    ? live.state.anchors
    : schematicAnchors.length
    ? schematicAnchors
    : demo.anchors
  const baseGeofences = live.state?.geofences?.length
    ? live.state.geofences
    : schematicRooms.length
    ? schematicRooms
    : demo.geofences

  // Strictly REAL hardware tags from live source
  const realTags = (live.state?.tags ?? []).filter((t) => !t.isSimulated && !t.id.toLowerCase().includes('sim'))

  // Simulation demonstration tag: illustrates real-time trilateration & geofencing
  const simDemoTag = demo.tags.find((t) => t.id === 'SIM-01') ?? demo.tags[0]
  const formattedSimTag: Tag | null = simDemoTag
    ? {
        ...simDemoTag,
        id: 'SIM-01',
        label: 'Simulation Tag',
        isSimulated: true,
      }
    : null

  // Active display tags for floor plan and roster
  let displayTags: Tag[] = []
  if (mode === 'live') {
    displayTags = [...realTags]
    if (simulationEnabled && formattedSimTag) {
      displayTags.push(formattedSimTag)
    }
  } else {
    displayTags = simulationEnabled ? demo.tags : []
  }

  // Active SimState for visual UI (Monitor, Map, 3D Building)
  const sim: SimState = {
    anchors: baseAnchors,
    tags: displayTags,
    geofences: baseGeofences,
    events: live.state?.events?.length ? live.state.events : demo.events,
    alerts: live.state?.alerts?.length ? live.state.alerts : demo.alerts,
    pipeline: mode === 'live' ? (live.state?.pipeline ?? buildPipeline(displayTags, [], displayTags.length)) : demo.pipeline,
    seenSeries: live.state?.seenSeries?.length ? live.state.seenSeries : demo.seenSeries,
    packetsPerSec: mode === 'live' ? (live.state?.packetsPerSec ?? (simulationEnabled ? 5 : 0)) : demo.packetsPerSec,
    startedAt: live.state?.startedAt ?? demo.startedAt,
  }

  // Strictly REAL SimState for Analytics, History, Reports, and Data:
  // "also all analytics and data and stuff will use the real stuff"
  const realSimState: SimState = {
    anchors: baseAnchors,
    tags: realTags,
    geofences: baseGeofences,
    events: live.state?.events ?? [],
    alerts: (live.state?.alerts ?? []).filter((a) => !a.tag?.toLowerCase().includes('sim')),
    pipeline: live.state?.pipeline ?? buildPipeline(realTags, [], realTags.length),
    seenSeries: live.state?.seenSeries ?? [],
    packetsPerSec: live.state?.packetsPerSec ?? 0,
    startedAt: live.state?.startedAt ?? Date.now(),
  }

  const hostAnchor = sim.anchors.find((a) => a.host)
  const online = sim.tags.filter((t) => t.status !== 'lost').length

  // Searchable entities: tags + anchors.
  const searchItems = [
    ...sim.tags.map((t) => ({ id: t.id, label: t.label, sub: `TAG-${t.id}`, kind: 'tag' as const })),
    ...sim.anchors.map((a) => ({ id: a.id, label: a.label, sub: a.ssid, kind: 'anchor' as const })),
  ]

  const onFocus = (id: string | null) => {
    setFocus(id)
    // focusing a tag also selects it so the detail panel follows
    if (id && sim.tags.some((t) => t.id === id)) setSelected(id)
    if (id === null) setSelected(null)
  }

  const showConnection = mode === 'live' && view === 'monitor' && live.state === null && !simulationEnabled

  const handleLoadDemoPreset = () => {
    localStorage.setItem('rtls_schematic_rooms', JSON.stringify(TEMPLATES.facility.rooms))
    localStorage.setItem('rtls_schematic_anchors', JSON.stringify(TEMPLATES.facility.anchors))
    localStorage.setItem('rtls_schematic_walls', JSON.stringify(TEMPLATES.facility.walls))
    setSchematicRooms(TEMPLATES.facility.rooms)
    setSchematicAnchors(TEMPLATES.facility.anchors)
    setMapItems(TEMPLATES.facility.walls)
  }

  return (
    <>
    <AppShell
      view={view}
      onView={setView}
      role={role}
      onRole={setRole}
      mode={mode}
      onMode={setMode}
      connStatus={mode === 'live' ? live.status : null}
      now={now}
      hostSsid={hostAnchor?.ssid ?? '—'}
      online={online}
      total={sim.tags.length}
      searchItems={searchItems}
      focus={focus}
      onFocus={onFocus}
      simulationEnabled={simulationEnabled}
      onToggleSimulation={setSimulationEnabled}
    >
      {canAccess(role, 'operator') && (
        <ErrorDiagnosticBanner
          mode={mode}
          connStatus={mode === 'live' ? live.status : null}
          error={live.error}
          endpoint={endpoint}
          sim={sim}
          onRetry={live.retry}
          onSwitchDemo={() => setMode('demo')}
        />
      )}

      {view === 'monitor' && (
        showConnection ? (
          <ConnectionScreen
            status={live.status}
            endpoint={endpoint}
            error={live.error}
            onRetry={live.retry}
            onDemo={() => setMode('demo')}
          />
        ) : (
          <MonitorView
            sim={sim}
            mapItems={mapItems}
            selected={selected}
            onSelect={setSelected}
            focus={focus}
            onFocus={onFocus}
            role={role}
            onNavigateToSetup={() => setView('admin')}
            onLoadDemoPreset={handleLoadDemoPreset}
          />
        )
      )}
      {view === 'collector' && (
        <CollectorView
          buildingDims={{ width: 10, height: 10, unit: 'meters' }}
          schematicRooms={schematicRooms}
          schematicAnchors={schematicAnchors}
          mapItems={mapItems}
          role={role}
        />
      )}
      {view === 'reports' && (
        <ReportsView
          sim={realSimState}
          mode={mode}
          onMode={setMode}
          connStatus={mode === 'live' ? live.status : null}
          endpoint={endpoint}
          role={role}
        />
      )}
      {view === 'admin' && (
        <AdminView
          sim={realSimState}
          mode={mode}
          interval={interval}
          onInterval={setIntervalMs}
          endpoint={endpoint}
          onEndpoint={setEndpoint}
          mapItems={mapItems}
          onMapItems={setMapItems}
          role={role}
          simulationEnabled={simulationEnabled}
          onToggleSimulation={setSimulationEnabled}
        />
      )}
    </AppShell>
    <AlertToasts alerts={realSimState.alerts} trigger={adminOpens} />
    </>
  )
}
