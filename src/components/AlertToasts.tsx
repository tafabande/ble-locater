import { useEffect, useState } from 'react'
import type { Alert, Severity } from '../lib/simulation'
import { relativeTime } from '../lib/format'

interface Props {
  alerts: Alert[]
  /** Increments each time the admin panel is opened; triggers a fresh batch. */
  trigger: number
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

export function AlertToasts({ alerts, trigger }: Props) {
  const [shown, setShown] = useState<Alert[]>([])

  // On each admin-open, snapshot the currently open alerts and surface them.
  useEffect(() => {
    if (trigger === 0) return
    const active = alerts.filter((a) => !a.acknowledged).slice(0, 4)
    setShown(active)
    if (active.length === 0) return
    const timers = active.map((a, i) =>
      setTimeout(() => setShown((s) => s.filter((x) => x.id !== a.id)), 5200 + i * 500)
    )
    return () => timers.forEach(clearTimeout)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trigger])

  const dismiss = (id: string) => setShown((s) => s.filter((x) => x.id !== id))

  if (shown.length === 0) return null

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-[320px] max-w-[calc(100vw-2rem)] flex-col gap-2">
      {shown.map((a) => {
        const s = SEV[a.severity]
        return (
          <div
            key={a.id}
            className="pointer-events-auto flex gap-3 rounded-[var(--radius)] border border-border bg-card/95 px-3.5 py-3 shadow-lg backdrop-blur"
            style={{ borderLeft: `3px solid ${s.color}` }}
          >
            <span className="mt-0.5 grid size-6 shrink-0 place-items-center rounded text-xs" style={{ background: 'var(--accent-soft)', color: s.color }}>
              {KIND_ICON[a.kind]}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-xs font-semibold" style={{ color: s.color }}>{s.label}</span>
                <span className="font-mono text-[10px] text-muted-foreground">{relativeTime(a.ts)}</span>
              </div>
              <p className="mt-0.5 text-xs text-foreground">{a.message}</p>
              <p className="font-mono text-[10px] text-muted-foreground">{a.tag}</p>
            </div>
            <button
              onClick={() => dismiss(a.id)}
              className="shrink-0 text-muted-foreground transition-colors hover:text-foreground"
              aria-label="Dismiss"
            >
              ✕
            </button>
          </div>
        )
      })}
    </div>
  )
}
