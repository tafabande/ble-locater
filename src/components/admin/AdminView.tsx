import { useState } from 'react'
import type { MapItem, SimState } from '../../lib/simulation'
import type { Mode } from '../../lib/datasource'
import { History } from './History'
import { Analytics } from './Analytics'
import { Calibration } from './Calibration'
import { FloorEditor } from './FloorEditor'
import { Configuration } from './Configuration'
import { CasualSetup } from './CasualSetup'
import { canAccess, type UserRole } from '../../lib/rbac'
import { M3Grid, M3Admin, M3Operations, M3Reports, M3Training, M3Sparkles } from '../common/MaterialIcon'
import { InteractiveTourGuide } from '../common/InteractiveTourGuide'
import { CASUAL_SETUP_TOUR, ENGINEER_STUDIO_TOUR } from '../../lib/tourGuides'

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
  simulationEnabled?: boolean
  onToggleSimulation?: (val: boolean) => void
  onNavigate?: (view: any) => void
}

type SetupMode = 'casual' | 'engineer'
type Tab = 'floor' | 'calibration' | 'analytics' | 'history' | 'config'

const TABS: { id: Tab; label: string; minRole: UserRole; icon: typeof M3Grid }[] = [
  { id: 'floor', label: 'Floor Plan Designer', minRole: 'admin', icon: M3Grid },
  { id: 'calibration', label: 'Calibration', minRole: 'admin', icon: M3Operations },
  { id: 'analytics', label: 'Analytics', minRole: 'admin', icon: M3Reports },
  { id: 'history', label: 'History', minRole: 'admin', icon: M3Training },
  { id: 'config', label: 'Configuration', minRole: 'admin', icon: M3Admin },
]

export function AdminView({
  sim,
  mode,
  interval,
  onInterval,
  endpoint,
  onEndpoint,
  mapItems,
  onMapItems,
  role,
  simulationEnabled,
  onToggleSimulation,
  onNavigate,
}: Props) {
  const [setupMode, setSetupMode] = useState<SetupMode>(() => {
    const saved = localStorage.getItem('rtls_setup_mode') as SetupMode
    return saved === 'engineer' || saved === 'casual' ? saved : 'casual'
  })
  const [tab, setTab] = useState<Tab>('floor')
  const [isTourOpen, setIsTourOpen] = useState(false)
  const visibleTabs = TABS.filter((t) => canAccess(role, t.minRole))

  if (!canAccess(role, 'admin')) {
    return (
      <div className="rounded-2xl bg-amber-500/10 p-5 text-sm text-amber-600 font-semibold shadow-xs">
        Admin role is required for calibration, map editing, and system configuration.
      </div>
    )
  }

  const handleModeChange = (nextMode: SetupMode) => {
    setSetupMode(nextMode)
    localStorage.setItem('rtls_setup_mode', nextMode)
  }

  return (
    <div className="space-y-5">
      {/* Top Setup Mode Command Bar (Matching Collector Page Design) */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-card p-3 shadow-sm border border-border/40">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 pr-2 border-r border-border/40">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-teal-500/15 text-teal-600 dark:text-teal-400">
              <M3Admin size={18} />
            </div>
            <div>
              <div className="text-xs font-bold text-foreground leading-tight">Facility Setup</div>
              <div className="text-[10px] text-muted-foreground font-mono">
                {setupMode === 'casual' ? 'Casual Mode (Non-Engineer)' : 'Engineer Mode (Advanced Studio)'}
              </div>
            </div>
          </div>

          {/* Mode Switcher Tabs */}
          <div className="flex items-center gap-1 bg-muted/40 p-1 rounded-xl text-xs font-semibold">
            <button
              type="button"
              onClick={() => handleModeChange('casual')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                setupMode === 'casual'
                  ? 'bg-teal-600 text-white shadow-xs'
                  : 'hover:bg-muted text-muted-foreground hover:text-foreground'
              }`}
            >
              <M3Sparkles size={15} />
              <span>Casual Setup</span>
            </button>
            <button
              type="button"
              onClick={() => handleModeChange('engineer')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                setupMode === 'engineer'
                  ? 'bg-teal-600 text-white shadow-xs'
                  : 'hover:bg-muted text-muted-foreground hover:text-foreground'
              }`}
            >
              <M3Operations size={15} />
              <span>Engineer Studio</span>
            </button>
          </div>
        </div>

        {/* Right side status / hint & Guide launcher */}
        <div className="flex items-center gap-3 text-xs">
          <button
            type="button"
            onClick={() => setIsTourOpen(true)}
            className="flex items-center gap-1.5 rounded-xl border border-teal-500/40 bg-teal-500/10 hover:bg-teal-500/20 px-3 py-1.5 text-xs font-bold text-teal-700 dark:text-teal-300 transition-all cursor-pointer shadow-xs"
            title="Start game-style walkthrough for this mode"
          >
            <span className="text-sm">🎮</span>
            <span>{setupMode === 'casual' ? 'Casual Quest Guide' : 'Engineer Quest Guide'}</span>
          </button>

          <span className="text-[11px] text-muted-foreground font-medium hidden sm:inline">
            {setupMode === 'casual'
              ? '✨ Friendly visual setup without complex equations'
              : '🛠️ CAD blueprints, log-distance ML calibration, and decibels'}
          </span>
        </div>
      </div>

      {/* CASUAL SETUP MODE */}
      {setupMode === 'casual' && (
        <CasualSetup
          mapItems={mapItems}
          onMapItems={onMapItems}
          onSwitchToEngineerMode={() => handleModeChange('engineer')}
          onNavigateToMonitor={() => onNavigate?.('monitor')}
          onLaunchTour={() => setIsTourOpen(true)}
        />
      )}

      {/* ENGINEER STUDIO MODE (Existing Full Technical Toolset) */}
      {setupMode === 'engineer' && (
        <div className="space-y-6">
          {/* Admin Sub-Navigation Tabs */}
          <div className="inline-flex p-1.5 rounded-2xl bg-muted/40 shadow-xs gap-1 overflow-x-auto text-xs">
            {visibleTabs.map((t) => {
              const Icon = t.icon
              const isAct = tab === t.id
              return (
                <button
                  key={t.id}
                  id={`tour-eng-tab-${t.id}`}
                  onClick={() => setTab(t.id)}
                  className={`flex items-center gap-2 whitespace-nowrap px-4 py-2 font-medium rounded-xl transition-all focus-visible:outline-2 focus-visible:outline-accent cursor-pointer ${
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
              simulationEnabled={simulationEnabled}
              onToggleSimulation={onToggleSimulation}
            />
          )}
        </div>
      )}

      {/* Interactive Game Tour Guide for Both Tabs */}
      <InteractiveTourGuide
        isOpen={isTourOpen}
        onClose={() => setIsTourOpen(false)}
        steps={setupMode === 'casual' ? CASUAL_SETUP_TOUR : ENGINEER_STUDIO_TOUR}
        tourTitle={setupMode === 'casual' ? 'Casual Setup Quest' : 'Engineer Studio Quest'}
        onTabChange={(tabKey) => {
          if (setupMode === 'engineer' && ['floor', 'calibration', 'analytics', 'history', 'config'].includes(tabKey)) {
            setTab(tabKey as Tab)
          }
        }}
      />
    </div>
  )
}


