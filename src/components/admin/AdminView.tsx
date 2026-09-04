import { useState } from 'react'
import type { MapItem, SimState } from '../../lib/simulation'
import type { Mode } from '../../lib/datasource'
import { History } from './History'
import { Analytics } from './Analytics'
import { Calibration } from './Calibration'
import { FloorEditor } from './FloorEditor'
import { Configuration } from './Configuration'
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
  { id: 'floor', label: 'Floor Plan Designer', minRole: 'admin', icon: M3Grid },
  { id: 'calibration', label: 'Calibration', minRole: 'admin', icon: M3Operations },
  { id: 'analytics', label: 'Analytics', minRole: 'admin', icon: M3Reports },
  { id: 'history', label: 'History', minRole: 'admin', icon: M3Training },
  { id: 'config', label: 'Configuration', minRole: 'admin', icon: M3Admin },
]

export function AdminView({ sim, mode, interval, onInterval, endpoint, onEndpoint, mapItems, onMapItems, role }: Props) {
  const [tab, setTab] = useState<Tab>('floor')
  const visibleTabs = TABS.filter((t) => canAccess(role, t.minRole))

  if (!canAccess(role, 'admin')) {
    return (
      <div className="rounded-2xl bg-amber-500/10 p-5 text-sm text-amber-600 font-semibold shadow-xs">
        Admin role is required for calibration, map editing, and system configuration.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Admin Sub-Navigation Tabs */}
      <div className="inline-flex p-1.5 rounded-2xl bg-muted/40 shadow-xs gap-1 overflow-x-auto text-xs">
        {visibleTabs.map((t) => {
          const Icon = t.icon
          const isAct = tab === t.id
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-2 whitespace-nowrap px-4 py-2 font-medium rounded-xl transition-all focus-visible:outline-2 focus-visible:outline-accent ${
                isAct ? 'bg-card text-foreground font-bold shadow-sm' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Icon size={16} />
              {t.label}
            </button>
          )
        })}
      </div>

      {tab === 'floor' && <FloorEditor mapItems={mapItems} onMapItems={onMapItems} />}
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
    </div>
  )
}
