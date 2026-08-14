import { useEffect, useState } from 'react'
import { useSimulation, DEFAULT_MAP, type MapItem } from './lib/simulation'
import { useLiveSource, EMPTY_STATE, type Mode } from './lib/datasource'
import { AppShell, type View } from './components/AppShell'
import { MonitorView } from './components/monitor/MonitorView'
import { AdminView } from './components/admin/AdminView'
import { ConnectionScreen } from './components/ConnectionScreen'
import { AlertToasts } from './components/AlertToasts'

const DEFAULT_ENDPOINT = 'http://192.168.4.1/api/positions'

export default function App() {
  const [view, setView] = useState<View>('monitor')
  const [mode, setMode] = useState<Mode>('demo')
  const [selected, setSelected] = useState<string | null>(null)
  const [focus, setFocus] = useState<string | null>(null)
  const [interval, setIntervalMs] = useState(2500)
  const [endpoint, setEndpoint] = useState(DEFAULT_ENDPOINT)
  const [mapItems, setMapItems] = useState<MapItem[]>(DEFAULT_MAP)
  const [now, setNow] = useState(Date.now())
  const [adminOpens, setAdminOpens] = useState(0)

  const demo = useSimulation(interval, mode === 'demo', mapItems)
  const live = useLiveSource(mode === 'live', endpoint, interval)

  useEffect(() => {
    const iv = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(iv)
  }, [])

  // Surface open alerts as toasts whenever the operator opens the admin panel.
  useEffect(() => {
    if (view === 'admin') setAdminOpens((n) => n + 1)
  }, [view])

  const sim = mode === 'demo' ? demo : live.state ?? EMPTY_STATE
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

  const showConnection = mode === 'live' && view === 'monitor' && live.state === null

  return (
    <>
    <AppShell
      view={view}
      onView={setView}
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
    >
      {view === 'monitor' ? (
        showConnection ? (
          <ConnectionScreen
            status={live.status}
            endpoint={endpoint}
            error={live.error}
            onRetry={live.retry}
            onDemo={() => setMode('demo')}
          />
        ) : (
          <MonitorView sim={sim} mapItems={mapItems} selected={selected} onSelect={setSelected} focus={focus} onFocus={onFocus} />
        )
      ) : (
        <AdminView
          sim={sim}
          mode={mode}
          interval={interval}
          onInterval={setIntervalMs}
          endpoint={endpoint}
          onEndpoint={setEndpoint}
          mapItems={mapItems}
          onMapItems={setMapItems}
        />
      )}
    </AppShell>
    <AlertToasts alerts={sim.alerts} trigger={adminOpens} />
    </>
  )
}
