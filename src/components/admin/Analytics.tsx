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
const BLUE = '#2a78d6'
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
  const dwell = dwellByZone(sim.tags)

  // RSSI distribution (histogram) across all current readings
  const buckets = [
    { range: '−50', min: -55, max: -45 },
    { range: '−60', min: -65, max: -55 },
    { range: '−70', min: -75, max: -65 },
    { range: '−80', min: -85, max: -75 },
    { range: '−90', min: -100, max: -85 },
  ]
  const rssiDist = buckets.map((b) => ({
    range: b.range,
    count: sim.tags.reduce((a, t) => a + t.readings.filter((r) => r.rssi > b.min && r.rssi <= b.max).length, 0),
  }))

  const tt = tooltipStyle()

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Kpi label="Peak tags / hr" value={`${Math.max(...sim.seenSeries.map((s) => s.tags), 0)}`} />
        <Kpi label="Avg dwell" value={`${Math.round(dwell.reduce((a, d) => a + d.dwell, 0) / dwell.length)}m`} />
        <Kpi label="Events logged" value={`${sim.events.length}`} />
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
              <Bar dataKey="packets" fill={BLUE} radius={[3, 3, 0, 0]} name="Packets" />
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
                  <Cell key={i} fill={i < 2 ? TEAL : i < 4 ? BLUE : MUTED} />
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
    <div className="rounded-[var(--radius)] border border-border bg-card p-4 sm:p-5">
      <div className="mb-4">
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p>
      </div>
      {children}
    </div>
  )
}

function Kpi({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="rounded-[var(--radius)] border border-border bg-card p-4">
      <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">{label}</div>
      <div className={`mt-2 text-2xl font-semibold tabular-nums ${accent ? 'text-accent' : ''}`}>{value}</div>
    </div>
  )
}
