import { useEffect, useState } from 'react'
import type { Alert, Severity } from '../lib/simulation'
import { relativeTime } from '../lib/format'
import { M3Error, M3Warning, M3Info, M3Close } from './common/MaterialIcon'

interface Props {
  alerts: Alert[]
  /** Increments each time the admin panel is opened; triggers a fresh batch. */
  trigger: number
}

const SEV_META: Record<Severity, { label: string; icon: typeof M3Error; badgeClass: string; borderClass: string; textClass: string }> = {
  critical: {
    label: 'Critical',
    icon: M3Error,
    badgeClass: 'bg-rose-500/10 text-rose-600',
    borderClass: 'border-l-4 border-l-rose-600',
    textClass: 'text-rose-600 font-bold',
  },
  warning: {
    label: 'Warning',
    icon: M3Warning,
    badgeClass: 'bg-amber-500/10 text-amber-600',
    borderClass: 'border-l-4 border-l-amber-600',
    textClass: 'text-amber-600 font-bold',
  },
  info: {
    label: 'Info',
    icon: M3Info,
    badgeClass: 'bg-teal-500/10 text-teal-600',
    borderClass: 'border-l-4 border-l-teal-600',
    textClass: 'text-teal-600 font-bold',
  },
}

export function AlertToasts({ alerts, trigger }: Props) {
  const [shown, setShown] = useState<Alert[]>([])

  useEffect(() => {
    if (trigger === 0) return
    const active = alerts.filter((a) => !a.acknowledged).slice(0, 4)
    setShown(active)
    if (active.length === 0) return
    const timers = active.map((a, i) =>
      setTimeout(() => setShown((s) => s.filter((x) => x.id !== a.id)), 5500 + i * 500)
    )
    return () => timers.forEach(clearTimeout)
  }, [trigger, alerts])

  const dismiss = (id: string) => setShown((s) => s.filter((x) => x.id !== id))

  if (shown.length === 0) return null

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-[340px] max-w-[calc(100vw-2rem)] flex-col gap-2.5">
      {shown.map((a) => {
        const meta = SEV_META[a.severity]
        const Icon = meta.icon
        return (
          <div
            key={a.id}
            className={`pointer-events-auto flex items-start gap-3 rounded-xl border border-border/40 bg-card/95 p-3.5 shadow-lg backdrop-blur transition-all ${meta.borderClass} animate-pop-in`}
          >
            <div className={`grid size-7 shrink-0 place-items-center rounded-lg ${meta.badgeClass}`}>
              <Icon size={16} />
            </div>

            <div className="min-w-0 flex-1 space-y-0.5">
              <div className="flex items-center justify-between gap-2">
                <span className={`text-xs ${meta.textClass}`}>{meta.label}</span>
                <span className="font-mono text-[10px] text-muted-foreground">{relativeTime(a.ts)}</span>
              </div>
              <p className="text-xs text-foreground font-medium leading-snug">{a.message}</p>
              <p className="font-mono text-[10px] text-muted-foreground">{a.tag}</p>
            </div>

            <button
              onClick={() => dismiss(a.id)}
              className="shrink-0 p-1 text-muted-foreground hover:text-foreground rounded-md transition-colors focus-visible:outline-2 focus-visible:outline-accent"
              aria-label="Dismiss"
            >
              <M3Close size={14} />
            </button>
          </div>
        )
      })}
    </div>
  )
}
