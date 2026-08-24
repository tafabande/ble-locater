import { useState } from 'react'
import type { Alert, Severity } from '../../lib/simulation'
import { relativeTime } from '../../lib/format'
import { M3Error, M3Warning, M3Info, M3CheckCircle, M3Bell, M3Check } from '../common/MaterialIcon'

interface Props {
  alerts: Alert[]
  onAcknowledgeAll?: () => void
}

type FilterSeverity = 'all' | Severity | 'unack'

const SEV_META: Record<Severity, { label: string; icon: typeof M3Error; badgeClass: string; textClass: string }> = {
  critical: {
    label: 'Critical',
    icon: M3Error,
    badgeClass: 'bg-rose-500/10 text-rose-600 border border-rose-500/20',
    textClass: 'text-rose-600 font-semibold',
  },
  warning: {
    label: 'Warning',
    icon: M3Warning,
    badgeClass: 'bg-amber-500/10 text-amber-600 border border-amber-500/20',
    textClass: 'text-amber-600 font-semibold',
  },
  info: {
    label: 'Info',
    icon: M3Info,
    badgeClass: 'bg-teal-500/10 text-teal-600 border border-teal-500/20',
    textClass: 'text-teal-600 font-semibold',
  },
}

export function AlertsPanel({ alerts, onAcknowledgeAll }: Props) {
  const [filter, setFilter] = useState<FilterSeverity>('all')
  const [ackedIds, setAckedIds] = useState<Set<string>>(new Set())

  const isAcked = (a: Alert) => a.acknowledged || ackedIds.has(a.id)

  const openCount = alerts.filter((a) => !isAcked(a)).length
  const criticalCount = alerts.filter((a) => a.severity === 'critical' && !isAcked(a)).length
  const warningCount = alerts.filter((a) => a.severity === 'warning' && !isAcked(a)).length

  const filteredAlerts = alerts.filter((a) => {
    if (filter === 'all') return true
    if (filter === 'unack') return !isAcked(a)
    return a.severity === filter
  })

  const toggleAck = (id: string) => {
    setAckedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleAckAll = () => {
    const allIds = new Set(alerts.map((a) => a.id))
    setAckedIds(allIds)
    onAcknowledgeAll?.()
  }

  return (
    <div className="rounded-xl border border-border/40 bg-card p-4 space-y-3.5 shadow-xs">
      {/* Header & Stats */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/30 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="grid size-8 place-items-center rounded-lg bg-accent-soft text-accent">
            <M3Bell size={18} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-foreground">Real-Time Alerts</h2>
              {openCount > 0 && (
                <span className="rounded-full bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 text-[10px] font-bold text-rose-600">
                  {openCount} active
                </span>
              )}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Geofence, signal telemetry & battery thresholds
            </p>
          </div>
        </div>

        {openCount > 0 && (
          <button
            onClick={handleAckAll}
            className="flex items-center gap-1.5 rounded-lg bg-panel border border-border/50 hover:bg-muted px-2.5 py-1 text-xs font-medium text-foreground transition-colors focus-visible:outline-2 focus-visible:outline-accent"
          >
            <M3Check size={14} />
            Acknowledge All
          </button>
        )}
      </div>

      {/* Material 3 Filter Chips */}
      <div className="flex gap-1 overflow-x-auto pb-1 text-xs">
        {[
          { id: 'all', label: `All (${alerts.length})` },
          { id: 'unack', label: `Unacknowledged (${openCount})` },
          { id: 'critical', label: `Critical (${criticalCount})` },
          { id: 'warning', label: `Warning (${warningCount})` },
        ].map((chip) => (
          <button
            key={chip.id}
            onClick={() => setFilter(chip.id as FilterSeverity)}
            className={`rounded-lg px-2.5 py-1 font-medium transition-colors border text-[11px] shrink-0 focus-visible:outline-2 focus-visible:outline-accent ${
              filter === chip.id
                ? 'border-accent bg-accent-soft text-accent font-bold shadow-xs'
                : 'border-border/40 bg-panel text-muted-foreground hover:text-foreground hover:bg-muted/50'
            }`}
          >
            {chip.label}
          </button>
        ))}
      </div>

      {/* Alerts Stream */}
      <div className="max-h-[280px] overflow-y-auto space-y-2 pr-1">
        {filteredAlerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-6 text-center rounded-lg bg-panel border border-dashed border-border/40">
            <M3CheckCircle size={28} className="text-emerald-500 mb-1.5" />
            <p className="text-xs font-semibold text-foreground">No alerts match filter</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">System monitoring operating within normal parameters.</p>
          </div>
        ) : (
          filteredAlerts.map((a) => {
            const meta = SEV_META[a.severity]
            const Icon = meta.icon
            const acked = isAcked(a)

            return (
              <div
                key={a.id}
                className={`group flex items-start gap-3 rounded-lg border p-3 transition-colors ${
                  acked
                    ? 'border-border/20 bg-panel/50 opacity-60'
                    : 'border-border/40 bg-card hover:bg-panel/80 shadow-xs'
                }`}
              >
                <div className={`grid size-7 shrink-0 place-items-center rounded-md ${meta.badgeClass}`}>
                  <Icon size={16} />
                </div>

                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className={`text-xs ${meta.textClass}`}>{meta.label}</span>
                    <span className="font-mono text-[10px] text-muted-foreground">{relativeTime(a.ts)}</span>
                  </div>

                  <p className="text-xs text-foreground font-medium leading-snug">{a.message}</p>

                  <div className="flex items-center justify-between pt-0.5 text-[11px]">
                    <span className="font-mono text-muted-foreground text-[10px]">{a.tag}</span>
                    <button
                      onClick={() => toggleAck(a.id)}
                      className={`text-[10px] font-medium transition-colors ${
                        acked
                          ? 'text-muted-foreground hover:text-foreground'
                          : 'text-accent hover:underline font-bold'
                      }`}
                    >
                      {acked ? 'Acknowledged ✓' : 'Acknowledge'}
                    </button>
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
