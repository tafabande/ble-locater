import type { Anchor, Tag } from '../../lib/simulation'
import { STATUS_META, batteryColor } from '../../lib/format'

interface Props {
  tag: Tag | null
  anchors: Anchor[]
}

export function TagDetail({ tag }: Props) {
  if (!tag) {
    return (
      <div className="grid min-h-[220px] place-items-center rounded-2xl bg-card p-8 text-center shadow-sm">
        <div>
          <div className="mx-auto mb-3 grid size-10 place-items-center rounded-full bg-muted text-muted-foreground">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="size-5">
              <circle cx="12" cy="12" r="3" />
              <circle cx="12" cy="12" r="8" opacity="0.5" />
            </svg>
          </div>
          <p className="text-sm font-semibold text-foreground">No tag selected</p>
          <p className="mt-1 text-xs text-muted-foreground">Select a tag on the map or roster to inspect its signal.</p>
        </div>
      </div>
    )
  }

  const meta = STATUS_META[tag.status]
  const maxRssi = -40
  const minRssi = -100
  const pct = (r: number) => Math.max(0, Math.min(100, ((r - minRssi) / (maxRssi - minRssi)) * 100))

  return (
    <div className="rounded-2xl bg-card p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-foreground tracking-tight">{tag.label}</h2>
          <p className="font-mono text-[11px] text-muted-foreground">TAG-{tag.id}</p>
        </div>
        <span
          className="flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold"
          style={{ background: 'var(--accent-soft)', color: meta.color }}
        >
          <span className="size-1.5 rounded-full" style={{ background: meta.color }} />
          {meta.label}
        </span>
      </div>

      {tag.violating && (
        <div className="flex items-center gap-2 rounded-xl bg-rose-500/10 px-3.5 py-2 text-xs font-semibold text-rose-500">
          ⚠ Geofence breach — unauthorized zone
        </div>
      )}

      {/* Recessed Stat Wells with Hierarchy */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 rounded-xl bg-muted/40 p-2">
        <Cell label="Zone" value={tag.zone} />
        <Cell label="Battery" value={`${Math.round(tag.battery)}%`} color={batteryColor(tag.battery)} mono />
        <Cell label="Position" value={`${tag.x.toFixed(0)},${tag.y.toFixed(0)}`} mono />
        <Cell label="σ (1σ)" value={`${tag.uncertainty}m`} mono color={tag.uncertainty > 2.5 ? 'var(--status-stale)' : undefined} />
      </div>

      {/* Anchor RSSI Solving Sub-Panel */}
      <div className="rounded-xl bg-muted/30 p-3.5 space-y-2.5">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Anchor RSSI</span>
          <span className="font-mono text-[10px] text-muted-foreground">● used in solve</span>
        </div>
        <div className="space-y-2">
          {tag.readings.map((r) => (
            <div key={r.anchorId} className="flex items-center gap-3">
              <span className="flex w-9 items-center gap-1 font-mono text-[11px] text-muted-foreground">
                <span className="size-1.5 rounded-full" style={{ background: r.used ? 'var(--accent)' : 'transparent', border: r.used ? undefined : '1px solid var(--muted-foreground)' }} />
                {r.anchorId}
              </span>
              <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-muted">
                <div
                  className="absolute inset-y-0 left-0 rounded-full"
                  style={{ width: `${pct(r.rssi)}%`, background: r.used ? 'var(--accent)' : 'var(--muted-foreground)', transition: 'width 1s ease' }}
                />
              </div>
              <span className="w-20 text-right font-mono text-[11px] tabular-nums text-foreground">
                {r.rssi} · {r.distance}m
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Sparkline Trend */}
      <div className="rounded-xl bg-muted/30 p-3.5 space-y-2">
        <div className="font-mono text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Nearest RSSI trend</div>
        <Sparkline data={tag.rssiHistory} />
      </div>
    </div>
  )
}

function Cell({ label, value, color, mono }: { label: string; value: string; color?: string; mono?: boolean }) {
  return (
    <div className="rounded-lg bg-card p-2.5 shadow-xs">
      <div className="font-mono text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={`mt-0.5 text-sm font-bold ${mono ? 'font-mono tabular-nums' : ''}`} style={color ? { color } : undefined}>
        {value}
      </div>
    </div>
  )
}

function Sparkline({ data }: { data: number[] }) {
  if (data.length < 2) return <div className="h-10 text-xs text-muted-foreground">collecting…</div>
  const w = 300
  const h = 40
  const min = Math.min(...data) - 2
  const max = Math.max(...data) + 2
  const pts = data.map((d, i) => {
    const x = (i / (data.length - 1)) * w
    const y = h - ((d - min) / (max - min || 1)) * h
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-10 w-full" preserveAspectRatio="none">
      <polyline points={pts.join(' ')} fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
    </svg>
  )
}
