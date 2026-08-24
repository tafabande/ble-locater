import type { Alert, Severity } from '../../lib/simulation'
import { relativeTime } from '../../lib/format'

interface Props {
  alerts: Alert[]
}

const SEV: Record<Severity, { color: string; label: string }> = {
  critical: { color: 'var(--status-lost)', label: 'Critical' },
  warning: { color: 'var(--status-stale)', label: 'Warning' },
  info: { color: 'var(--accent)', label: 'Info' },
}

const KIND_ICON: Record<Alert['kind'], string> = {
  geofence: '⚠',
  'signal-lost': '⚡',
  'low-battery': '▩',
  calibration: '⚙',
}

export function AlertsPanel({ alerts }: Props) {
  const open = alerts.filter((a) => !a.acknowledged).length
  return (
    <div className="rounded-[var(--radius)] border border-border/40 bg-card shadow-xs">
      <div className="flex items-center justify-between border-b border-border/30 px-4 py-3">
        <h2 className="text-sm font-semibold">Alerts</h2>
        <span
          className="rounded-full px-2 py-0.5 font-mono text-[11px] font-medium"
          style={{ background: open ? 'rgba(208,59,59,0.12)' : 'var(--muted)', color: open ? 'var(--status-lost)' : 'var(--muted-foreground)' }}
        >
          {open} open
        </span>
      </div>
      <div className="max-h-[260px] overflow-y-auto">
        {alerts.length === 0 && <div className="px-4 py-8 text-center text-sm text-muted-foreground">No alerts. System nominal.</div>}
        {alerts.map((a) => {
          const s = SEV[a.severity]
          return (
            <div key={a.id} className={`flex gap-3 border-b border-border/30 px-4 py-2.5 last:border-0 ${a.acknowledged ? 'opacity-55' : ''}`}>
              <span className="mt-0.5 grid size-5 shrink-0 place-items-center rounded text-[11px]" style={{ background: 'var(--accent-soft)', color: s.color }}>
                {KIND_ICON[a.kind]}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-xs font-medium" style={{ color: s.color }}>
                    {s.label}
                  </span>
                  <span className="font-mono text-[10px] text-muted-foreground">{relativeTime(a.ts)}</span>
                </div>
                <p className="truncate text-xs text-foreground">{a.message}</p>
                <p className="font-mono text-[10px] text-muted-foreground">{a.tag}</p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
