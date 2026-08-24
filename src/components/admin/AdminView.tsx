import { useState } from 'react'
import type { MapItem, SimState } from '../../lib/simulation'
import type { Mode } from '../../lib/datasource'
import { History } from './History'
import { Analytics } from './Analytics'
import { Calibration } from './Calibration'
import { FloorEditor } from './FloorEditor'
import { Configuration } from './Configuration'
import { RoomDesignWizard } from './RoomDesignWizard'
import { canAccess, type UserRole } from '../../lib/rbac'
import { M3Grid, M3Admin, M3Operations, M3Reports, M3Training } from '../common/MaterialIcon'

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

type Tab = 'floor' | 'calibration' | 'analytics' | 'history' | 'config'

const TABS: { id: Tab; label: string; minRole: UserRole; icon: typeof M3Grid }[] = [
  { id: 'floor', label: 'Schematic Studio & 3D Designer', minRole: 'admin', icon: M3Grid },
  { id: 'calibration', label: 'Calibration', minRole: 'admin', icon: M3Operations },
  { id: 'analytics', label: 'Analytics', minRole: 'admin', icon: M3Reports },
  { id: 'history', label: 'History', minRole: 'admin', icon: M3Training },
  { id: 'config', label: 'Configuration', minRole: 'admin', icon: M3Admin },
]

export function AdminView({ sim, mode, interval, onInterval, endpoint, onEndpoint, mapItems, onMapItems, role }: Props) {
  const [tab, setTab] = useState<Tab>('floor')
  const visibleTabs = TABS.filter((t) => canAccess(role, t.minRole))
  const [showWizard, setShowWizard] = useState(false)

  if (!canAccess(role, 'admin')) {
    return (
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-5 text-sm text-amber-600 font-medium">
        Admin role is required for calibration, map editing, and system configuration.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Admin Sub-Navigation Tabs */}
      <div className="flex gap-1 overflow-x-auto border-b border-border/40 text-xs">
        {visibleTabs.map((t) => {
          const Icon = t.icon
          const isAct = tab === t.id
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`relative flex items-center gap-1.5 -mb-px whitespace-nowrap px-4 py-2.5 font-medium transition-colors focus-visible:outline-2 focus-visible:outline-accent ${
                isAct ? 'text-accent font-bold' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Icon size={16} />
              {t.label}
              {isAct && <span className="absolute inset-x-0 -bottom-px h-0.5 rounded-full bg-accent" />}
            </button>
          )
        })}
      </div>

      {tab === 'floor' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-border/40 bg-card p-4 shadow-xs">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Interactive Schematic Studio</h3>
              <p className="text-xs text-muted-foreground mt-0.5">Manage room geometry, furniture objects, and anchor node coordinates.</p>
            </div>
            <button
              onClick={() => setShowWizard(true)}
              className="rounded-lg bg-accent hover:bg-accent/90 px-4 py-2 text-xs font-bold text-primary-foreground transition-colors shadow-xs flex items-center gap-2 focus-visible:outline-2 focus-visible:outline-accent"
            >
              <M3Grid size={15} />
              Open 3D Room Designer Wizard
            </button>
          </div>
          <FloorEditor mapItems={mapItems} onMapItems={onMapItems} />
        </div>
      )}

      {tab === 'calibration' && <Calibration anchors={sim.anchors} />}
      {tab === 'analytics' && <Analytics sim={sim} />}
      {tab === 'history' && <History events={sim.events} alerts={sim.alerts} />}
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

      {showWizard && (
        <RoomDesignWizard
          onClose={() => setShowWizard(false)}
          onSaved={() => setShowWizard(false)}
        />
      )}
    </div>
  )
}
