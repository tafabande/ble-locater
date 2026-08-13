import { useState } from 'react'
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  Line,
  ComposedChart,
} from 'recharts'
import type { Anchor } from '../../lib/simulation'
import { clockTime } from '../../lib/format'

interface Props {
  anchors: Anchor[]
}

const INK = '#121619'
const MUTED = '#6b7472'
const GRID = '#e3e7e6'
const TEAL = '#0d9488'
const BLUE = '#2a78d6'
const AMBER = '#eda100'

const axis = { stroke: MUTED, fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }
const ttStyle = {
  contentStyle: { background: '#fff', border: `1px solid ${GRID}`, borderRadius: 8, fontSize: 12, fontFamily: 'JetBrains Mono, monospace' } as const,
  labelStyle: { color: INK, fontWeight: 600 },
}

export function Calibration({ anchors }: Props) {
  const [sel, setSel] = useState(anchors[0]?.id ?? '')
  const anchor = anchors.find((a) => a.id === sel) ?? anchors[0]

  // Synthesised RSSI-vs-distance samples around the fitted log-distance model.
  const samples = Array.from({ length: 42 }, () => {
    const d = 0.6 + Math.random() * 14
    const model = anchor.txPower - 10 * anchor.cal.n * Math.log10(d)
    const rssi = model + (Math.random() - 0.5) * anchor.cal.rmse * 6
    return { d: Math.round(d * 10) / 10, rssi: Math.round(rssi) }
  })
  const fitLine = Array.from({ length: 20 }, (_, i) => {
    const d = 0.6 + (i / 19) * 14
    return { d: Math.round(d * 10) / 10, model: Math.round(anchor.txPower - 10 * anchor.cal.n * Math.log10(d)) }
  })
  const merged = [...samples.map((s) => ({ ...s, model: null })), ...fitLine.map((f) => ({ ...f, rssi: null }))]

  return (
    <div className="space-y-6">
      {/* per-anchor ML parameter table */}
      <div className="rounded-[var(--radius)] border border-border bg-card">
        <div className="border-b border-border px-4 py-3">
          <h3 className="text-sm font-semibold">ML Calibration Parameters</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">Per-anchor log-distance path-loss model fitted from RSSI samples</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                <th className="px-4 py-2.5 font-medium">Node</th>
                <th className="px-4 py-2.5 font-medium">TX @1m</th>
                <th className="px-4 py-2.5 font-medium">n (path loss)</th>
                <th className="px-4 py-2.5 font-medium">Env offset</th>
                <th className="px-4 py-2.5 font-medium">RMSE</th>
                <th className="px-4 py-2.5 font-medium">R²</th>
                <th className="px-4 py-2.5 font-medium">Samples</th>
                <th className="px-4 py-2.5 font-medium">Updated</th>
              </tr>
            </thead>
            <tbody>
              {anchors.map((a) => (
                <tr
                  key={a.id}
                  onClick={() => setSel(a.id)}
                  className={`cursor-pointer border-b border-border last:border-0 ${sel === a.id ? 'bg-accent-soft' : 'hover:bg-muted'}`}
                >
                  <td className="px-4 py-3 font-mono text-xs font-medium">{a.label}</td>
                  <td className="px-4 py-3 font-mono text-xs tabular-nums">{a.txPower} dBm</td>
                  <td className="px-4 py-3 font-mono text-xs tabular-nums">{a.cal.n.toFixed(2)}</td>
                  <td className="px-4 py-3 font-mono text-xs tabular-nums">{a.cal.envDb} dB</td>
                  <td className="px-4 py-3 font-mono text-xs tabular-nums" style={{ color: a.cal.rmse > 0.6 ? AMBER : INK }}>
                    {a.cal.rmse.toFixed(2)} m
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-2 font-mono text-xs tabular-nums">
                      <span className="relative h-1.5 w-14 overflow-hidden rounded-full bg-muted">
                        <span className="absolute inset-y-0 left-0 rounded-full" style={{ width: `${a.cal.r2 * 100}%`, background: a.cal.r2 > 0.94 ? TEAL : AMBER }} />
                      </span>
                      {a.cal.r2.toFixed(2)}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs tabular-nums text-muted-foreground">{a.cal.samples}</td>
                  <td className="px-4 py-3 font-mono text-xs tabular-nums text-muted-foreground">{clockTime(a.cal.updated)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title={`RSSI vs distance — ${anchor.label}`} sub="Sample scatter with fitted path-loss curve">
          <ResponsiveContainer width="100%" height={260}>
            <ComposedChart data={merged} margin={{ top: 8, right: 12, bottom: 4, left: -12 }}>
              <CartesianGrid stroke={GRID} />
              <XAxis type="number" dataKey="d" name="Distance" unit="m" tick={axis} tickLine={false} axisLine={{ stroke: GRID }} />
              <YAxis type="number" dataKey="rssi" name="RSSI" unit="dBm" tick={axis} tickLine={false} axisLine={false} domain={['dataMin - 4', 'dataMax + 4']} />
              <ZAxis range={[40, 40]} />
              <Tooltip {...ttStyle} cursor={{ stroke: GRID }} />
              <Scatter data={samples} fill={BLUE} fillOpacity={0.55} />
              <Line type="monotone" dataKey="model" data={fitLine} stroke={TEAL} strokeWidth={2} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Model residuals (RMSE)" sub="Per-anchor fit error in meters — lower is better">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={anchors.map((a) => ({ node: a.id, rmse: a.cal.rmse }))} margin={{ top: 8, right: 12, bottom: 4, left: -18 }}>
              <CartesianGrid stroke={GRID} vertical={false} />
              <XAxis dataKey="node" tick={axis} tickLine={false} axisLine={{ stroke: GRID }} />
              <YAxis tick={axis} tickLine={false} axisLine={false} />
              <Tooltip {...ttStyle} cursor={{ fill: 'rgba(13,148,136,0.06)' }} />
              <Bar dataKey="rmse" radius={[3, 3, 0, 0]} barSize={30}>
                {anchors.map((a) => (
                  <Cell key={a.id} fill={a.cal.rmse > 0.6 ? AMBER : TEAL} />
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
