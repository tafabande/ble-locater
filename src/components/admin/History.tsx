import { useMemo, useState } from 'react'
import type { Alert, EventRow, Severity } from '../../lib/simulation'
import { clockTime, relativeTime } from '../../lib/format'

interface Props {
  events: EventRow[]
  alerts: Alert[]
}

const SEV_COLOR: Record<Severity, string> = {
  critical: 'var(--status-lost)',
  warning: 'var(--status-stale)',
  info: 'var(--accent)',
}

const TYPE_META: Record<EventRow['type'], { label: string; color: string }> = {
  enter: { label: 'Zone enter', color: 'var(--status-online)' },
  exit: { label: 'Zone exit', color: 'var(--muted-foreground)' },
  connect: { label: 'Connect', color: 'var(--accent)' },
  disconnect: { label: 'Disconnect', color: 'var(--status-lost)' },
  'low-battery': { label: 'Low battery', color: 'var(--status-stale)' },
}

const FILTERS: { id: 'all' | EventRow['type']; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'enter', label: 'Enter' },
  { id: 'exit', label: 'Exit' },
  { id: 'disconnect', label: 'Disconnect' },
  { id: 'low-battery', label: 'Low battery' },
]

export function History({ events, alerts }: Props) {
  const [source, setSource] = useState<'events' | 'alerts'>('events')
  const [filter, setFilter] = useState<'all' | EventRow['type']>('all')
  const [q, setQ] = useState('')

  const rows = useMemo(
    () =>
      events.filter(
        (e) =>
          (filter === 'all' || e.type === filter) &&
          (q === '' || e.tag.toLowerCase().includes(q.toLowerCase()) || e.zone.toLowerCase().includes(q.toLowerCase()))
      ),
    [events, filter, q]
  )

  return (
    <div className="rounded-[var(--radius)] border border-border bg-card">
      <div className="flex items-center gap-1 border-b border-border p-3">
        {(['events', 'alerts'] as const).map((s) => (
          <button
            key={s}
            onClick={() => setSource(s)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              source === s ? 'bg-accent-soft text-accent' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {s === 'events' ? 'Movement events' : `Alert log (${alerts.length})`}
          </button>
        ))}
      </div>

      {source === 'alerts' ? (
        <div className="max-h-[520px] overflow-y-auto">
          <table className="w-full text-left text-sm">
            <thead className="sticky top-0 bg-card">
              <tr className="border-b border-border font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                <th className="px-4 py-2.5 font-medium">Time</th>
                <th className="px-4 py-2.5 font-medium">Severity</th>
                <th className="px-4 py-2.5 font-medium">Source</th>
                <th className="px-4 py-2.5 font-medium">Message</th>
                <th className="px-4 py-2.5 font-medium">State</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a) => (
                <tr key={a.id} className="border-b border-border last:border-0 hover:bg-muted">
                  <td className="whitespace-nowrap px-4 py-2.5 font-mono text-xs tabular-nums text-muted-foreground">
                    {clockTime(a.ts)}
                    <span className="ml-1.5 text-[10px] opacity-70">{relativeTime(a.ts)}</span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="inline-flex items-center gap-1.5 text-xs font-medium" style={{ color: SEV_COLOR[a.severity] }}>
                      <span className="size-1.5 rounded-full" style={{ background: SEV_COLOR[a.severity] }} />
                      {a.severity}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs">{a.tag}</td>
                  <td className="px-4 py-2.5 text-xs text-foreground">{a.message}</td>
                  <td className="px-4 py-2.5 text-xs text-muted-foreground">{a.acknowledged ? 'Acknowledged' : 'Open'}</td>
                </tr>
              ))}
              {alerts.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-sm text-muted-foreground">
                    No alerts recorded.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      ) : (
      <>
      <div className="flex flex-col gap-3 border-b border-border p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-1">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                filter === f.id ? 'border-accent bg-accent-soft text-accent' : 'border-border text-muted-foreground hover:text-foreground'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search tag or zone…"
          className="w-full rounded-md border border-border bg-panel px-3 py-1.5 font-mono text-xs outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-ring sm:w-56"
        />
      </div>

      <div className="max-h-[520px] overflow-y-auto">
        <table className="w-full text-left text-sm">
          <thead className="sticky top-0 bg-card">
            <tr className="border-b border-border font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
              <th className="px-4 py-2.5 font-medium">Time</th>
              <th className="px-4 py-2.5 font-medium">Event</th>
              <th className="px-4 py-2.5 font-medium">Tag</th>
              <th className="px-4 py-2.5 font-medium">Zone</th>
              <th className="px-4 py-2.5 font-medium">Detail</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((e) => {
              const m = TYPE_META[e.type]
              return (
                <tr key={e.id} className="border-b border-border last:border-0 hover:bg-muted">
                  <td className="whitespace-nowrap px-4 py-2.5 font-mono text-xs tabular-nums text-muted-foreground">
                    {clockTime(e.ts)}
                    <span className="ml-1.5 text-[10px] opacity-70">{relativeTime(e.ts)}</span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="inline-flex items-center gap-1.5 text-xs font-medium">
                      <span className="size-1.5 rounded-full" style={{ background: m.color }} />
                      {m.label}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs">{e.tag}</td>
                  <td className="px-4 py-2.5 text-xs text-muted-foreground">{e.zone}</td>
                  <td className="px-4 py-2.5 text-xs text-muted-foreground">{e.detail}</td>
                </tr>
              )
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-sm text-muted-foreground">
                  No events match this filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      </>
      )}
    </div>
  )
}
