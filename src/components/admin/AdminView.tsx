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

interface Props {
  sim: SimState
  mode: Mode
  interval: number
  onInterval: (n: number) => void
  endpoint: string
  onEndpoint: (v: string) => void
  mapItems: MapItem[]
  onMapItems: (items: MapItem[]) => void
}

type Tab = 'overview' | 'history' | 'analytics' | 'calibration' | 'floor' | 'config'

const TABS: { id: Tab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'history', label: 'History' },
  { id: 'analytics', label: 'Analytics' },
  { id: 'calibration', label: 'Calibration' },
  { id: 'floor', label: 'Schematic Studio' },
  { id: 'config', label: 'Configuration' },
]

export function AdminView({ sim, mode, interval, onInterval, endpoint, onEndpoint, mapItems, onMapItems }: Props) {
  const [tab, setTab] = useState<Tab>('overview')
  const [selected, setSelected] = useState<string | null>(null)
  const selectedTag = sim.tags.find((t) => t.id === selected) ?? null

  return (
    <div className="space-y-6">
      <div className="flex gap-1 overflow-x-auto border-b border-border">
        {TABS.map((t) => (
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
      {tab === 'floor' && <FloorEditor mapItems={mapItems} onMapItems={onMapItems} />}
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
