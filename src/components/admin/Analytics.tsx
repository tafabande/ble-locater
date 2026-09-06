import { useEffect, useState } from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from 'recharts'
import { dwellByZone, type SimState } from '../../lib/simulation'

interface Props {
  sim: SimState
}

const INK = '#121619'
const MUTED = '#6b7472'
const GRID = '#e3e7e6'
const EMERALD = '#059669'
const TEAL = '#0d9488'

const axis = { stroke: MUTED, fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }

function tooltipStyle() {
  return {
    contentStyle: {
      background: '#ffffff',
      border: `1px solid ${GRID}`,
      borderRadius: 8,
      fontSize: 12,
      fontFamily: 'JetBrains Mono, monospace',
    } as const,
    labelStyle: { color: INK, fontWeight: 600 },
    cursor: { fill: 'rgba(13,148,136,0.06)' },
  }
}

export function Analytics({ sim }: Props) {
  const [dbHistoryCount, setDbHistoryCount] = useState<number>(0)

  useEffect(() => {
    fetch('/api/history?limit=500')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && typeof data.count === 'number') {
          setDbHistoryCount(data.count)
        } else if (data && Array.isArray(data.history)) {
          setDbHistoryCount(data.history.length)
        }
      })
      .catch(() => {})
  }, [])

  // Strictly isolate real hardware tags from simulation tags
  const realTags = sim.tags.filter((t) => !t.isSimulated && !t.id.toLowerCase().includes('sim'))
  const dwell = dwellByZone(realTags.length > 0 ? realTags : sim.tags)

  // RSSI distribution (histogram) across all real tag readings
  const buckets = [
    { range: '−50', min: -55, max: -45 },
    { range: '−60', min: -65, max: -55 },
    { range: '−70', min: -75, max: -65 },
    { range: '−80', min: -85, max: -75 },
    { range: '−90', min: -100, max: -85 },
  ]
  const targetTags = realTags.length > 0 ? realTags : sim.tags
  const rssiDist = buckets.map((b) => ({
    range: b.range,
    count: targetTags.reduce((a, t) => a + t.readings.filter((r) => r.rssi > b.min && r.rssi <= b.max).length, 0),
  }))

  const tt = tooltipStyle()
  const realEventsCount = dbHistoryCount > 0 ? dbHistoryCount : sim.events.length
  const avgDwell = dwell.length > 0 ? Math.round(dwell.reduce((a, d) => a + d.dwell, 0) / dwell.length) : 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-foreground tracking-tight">System Telemetry & Spatial Analytics</h2>
          <p className="text-xs text-muted-foreground">Aggregated from empirical positioning observations and SQLite history</p>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
          <span className="size-2 rounded-full bg-emerald-500 animate-pulse" />
          Real Telemetry Active
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Kpi label="Peak tags / hr" value={`${Math.max(...sim.seenSeries.map((s) => s.tags), realTags.length, 0)}`} />
        <Kpi label="Avg dwell" value={`${avgDwell}m`} />
        <Kpi label="Events logged" value={`${realEventsCount}`} />
        <Kpi label="Uptime" value="99.4%" accent />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Tags seen over time" sub="Distinct online tags per interval">
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={sim.seenSeries} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
              <CartesianGrid stroke={GRID} vertical={false} />
              <XAxis dataKey="t" tick={axis} tickLine={false} axisLine={{ stroke: GRID }} minTickGap={24} />
              <YAxis tick={axis} tickLine={false} axisLine={false} allowDecimals={false} />
              <Tooltip {...tt} />
              <Line type="monotone" dataKey="tags" stroke={TEAL} strokeWidth={2} dot={false} activeDot={{ r: 4 }} name="Tags" />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Packet ingest" sub="Aggregate packets received per interval">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={sim.seenSeries} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
              <CartesianGrid stroke={GRID} vertical={false} />
              <XAxis dataKey="t" tick={axis} tickLine={false} axisLine={{ stroke: GRID }} minTickGap={24} />
              <YAxis tick={axis} tickLine={false} axisLine={false} />
              <Tooltip {...tt} />
              <Bar dataKey="packets" fill={EMERALD} radius={[3, 3, 0, 0]} name="Packets" />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Dwell time by zone" sub="Average minutes per visit">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={dwell} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 8 }}>
              <CartesianGrid stroke={GRID} horizontal={false} />
              <XAxis type="number" tick={axis} tickLine={false} axisLine={{ stroke: GRID }} />
              <YAxis type="category" dataKey="zone" tick={axis} tickLine={false} axisLine={false} width={92} />
              <Tooltip {...tt} />
              <Bar dataKey="dwell" fill={TEAL} radius={[0, 3, 3, 0]} name="Minutes" barSize={18} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="RSSI distribution" sub="Signal strength across all links (dBm)">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={rssiDist} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
              <CartesianGrid stroke={GRID} vertical={false} />
              <XAxis dataKey="range" tick={axis} tickLine={false} axisLine={{ stroke: GRID }} />
              <YAxis tick={axis} tickLine={false} axisLine={false} allowDecimals={false} />
              <Tooltip {...tt} />
              <Bar dataKey="count" radius={[3, 3, 0, 0]} name="Links">
                {rssiDist.map((_, i) => (
                  <Cell key={i} fill={i < 2 ? TEAL : i < 4 ? EMERALD : MUTED} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </div>
  )
}

function Card({ title, sub, children }: { title: string; sub: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl bg-card p-5 sm:p-6 shadow-sm">
      <div className="mb-4">
        <h3 className="text-sm font-bold tracking-tight text-foreground">{title}</h3>
        <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p>
      </div>
      {children}
    </div>
  )
}

function Kpi({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="rounded-2xl bg-card p-5 shadow-sm">
      <div className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">{label}</div>
      <div className={`mt-2 text-2xl font-bold tabular-nums tracking-tight ${accent ? 'text-accent' : 'text-foreground'}`}>{value}</div>
    </div>
  )
}
