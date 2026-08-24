import { useState } from 'react'
import type { MapItem, SimState } from '../../lib/simulation'
import type { Mode } from '../../lib/datasource'
import { StatTiles } from '../monitor/StatTiles'
import { PipelineStatus } from '../monitor/PipelineStatus'
import { TagList } from '../monitor/TagList'
import { TagDetail } from '../monitor/TagDetail'
import { AlertsPanel } from '../monitor/AlertsPanel'
import { History } from './History'
import { Analytics } from './Analytics'
import { Calibration } from './Calibration'
import { FloorEditor } from './FloorEditor'
import { Configuration } from './Configuration'
import { RoomDesignWizard } from './RoomDesignWizard'
import { canAccess, type UserRole } from '../../lib/rbac'

interface Props {
  sim: SimState
  mode: Mode
  interval: number
  onInterval: (n: number) => void
  endpoint: string
  onEndpoint: (v: string) => void
  mapItems: MapItem[]
  onMapItems: (items: MapItem[]) => void
  role: UserRole
}

type Tab = 'overview' | 'history' | 'analytics' | 'calibration' | 'floor' | 'config'

const TABS: { id: Tab; label: string; minRole: UserRole }[] = [
  { id: 'overview', label: 'Overview', minRole: 'admin' },
  { id: 'history', label: 'History', minRole: 'admin' },
  { id: 'analytics', label: 'Analytics', minRole: 'admin' },
  { id: 'calibration', label: 'Calibration', minRole: 'admin' },
  { id: 'floor', label: 'Schematic Studio', minRole: 'admin' },
  { id: 'config', label: 'Configuration', minRole: 'admin' },
]

export function AdminView({ sim, mode, interval, onInterval, endpoint, onEndpoint, mapItems, onMapItems, role }: Props) {
  const [tab, setTab] = useState<Tab>('overview')
  const [selected, setSelected] = useState<string | null>(null)
  const selectedTag = sim.tags.find((t) => t.id === selected) ?? null
  const visibleTabs = TABS.filter((t) => canAccess(role, t.minRole))

  const [showWizard, setShowWizard] = useState(false)

  if (!canAccess(role, 'admin')) {
    return (
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-5 text-sm text-amber-100">
        Admin role is required for calibration, map editing, and system configuration.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex gap-1 overflow-x-auto border-b border-border/40">
        {visibleTabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`relative -mb-px whitespace-nowrap px-4 py-2.5 text-sm font-medium transition-colors ${
              tab === t.id ? 'text-accent' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {t.label}
            {tab === t.id && <span className="absolute inset-x-0 -bottom-px h-0.5 rounded-full bg-accent" />}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="space-y-6">
          {/* 3D Room Setup Launcher Banner */}
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl bg-card p-5 shadow-xs">
            <div>
              <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                🛠️ Interactive 3D Room Designer & BLE Node Setup
              </h3>
              <p className="text-xs text-muted-foreground mt-1 max-w-xl">
                Set 3D room dimensions, drag & drop furniture items onto the floorplan, plant fixed BLE anchor nodes, and configure mobile asset tags with live endpoint persistence (`/api/schematic`).
              </p>
            </div>
            <button
              onClick={() => setShowWizard(true)}
              className="rounded-lg bg-accent hover:bg-accent/90 px-4 py-2 text-xs font-bold text-primary-foreground transition-colors shadow-sm flex items-center gap-2 focus-visible:outline-2 focus-visible:outline-accent"
            >
              🛠️ Open 3D Room Designer Wizard
            </button>
          </div>

          <StatTiles sim={sim} />
          <PipelineStatus pipeline={sim.pipeline} />
          <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_360px]">
            <div className="space-y-6">
              <AlertsPanel alerts={sim.alerts} />
              <TagList tags={sim.tags} selected={selected} onSelect={setSelected} />
            </div>
            <TagDetail tag={selectedTag} anchors={sim.anchors} />
          </div>
        </div>
      )}
      {tab === 'history' && <History events={sim.events} alerts={sim.alerts} />}
      {tab === 'analytics' && <Analytics sim={sim} />}
      {tab === 'calibration' && <Calibration anchors={sim.anchors} />}
      {tab === 'floor' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center bg-card p-4 rounded-xl shadow-xs">
            <div>
              <h3 className="text-sm font-bold text-foreground">Interactive Schematic Studio</h3>
              <p className="text-xs text-muted-foreground">Manage map geometry, furniture items, and anchor coordinates.</p>
            </div>
            <button
              onClick={() => setShowWizard(true)}
              className="rounded-lg bg-accent hover:bg-accent/90 px-4 py-2 text-xs font-bold text-primary-foreground transition-colors shadow-sm flex items-center gap-2 focus-visible:outline-2 focus-visible:outline-accent"
            >
              🛠️ Open 3D Room Setup Wizard
            </button>
          </div>
          <FloorEditor mapItems={mapItems} onMapItems={onMapItems} />
        </div>
      )}

      {showWizard && (
        <RoomDesignWizard
          onClose={() => setShowWizard(false)}
          onSaved={() => setShowWizard(false)}
        />
      )}
      {tab === 'config' && (
        <Configuration
          anchors={sim.anchors}
          mode={mode}
          interval={interval}
          onInterval={onInterval}
          endpoint={endpoint}
          onEndpoint={onEndpoint}
        />
      )}
    </div>
  )
}
