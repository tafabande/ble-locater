import { useState } from 'react'
import TypeIt from 'typeit-react'
import type { ConnStatus, Mode } from '../lib/datasource'
import type { SimState } from '../lib/simulation'
import { M3Error, M3Refresh } from './common/MaterialIcon'

interface Props {
  mode: Mode
  connStatus: ConnStatus | null
  error: string | null
  endpoint: string
  sim: SimState
  onRetry: () => void
  onSwitchDemo: () => void
}

export function ErrorDiagnosticBanner({ mode, connStatus, error, endpoint, sim, onRetry, onSwitchDemo }: Props) {
  const [expanded, setExpanded] = useState(false)

  const isLiveError = mode === 'live' && (connStatus === 'error' || Boolean(error))
  const criticalAlerts = sim.alerts.filter((a) => a.severity === 'critical' && !a.acknowledged)
  const lostTags = sim.tags.filter((t) => t.status === 'lost')
  const hasPipelineErrors = sim.pipeline.some((p) => p.status === 'error')

  // Nothing to warn about if everything is operating nominally in Demo mode or Live connected.
  if (!isLiveError && criticalAlerts.length === 0 && !hasPipelineErrors) {
    return null
  }

  const errorMsg = isLiveError
    ? error || `Cannot connect to live server at ${endpoint}`
    : criticalAlerts.length > 0
    ? criticalAlerts[0].message
    : 'One or more telemetry pipeline stages reported execution anomalies.'

  return (
    <div className="mb-6 overflow-hidden rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-foreground shadow-xs backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="grid size-8 shrink-0 place-items-center rounded-lg bg-rose-500/20 text-rose-600">
            <M3Error size={20} />
          </div>
          <div>
            <h3 className="text-sm font-semibold tracking-tight text-rose-600">
              {isLiveError
                ? 'System Alert: Live Hardware Endpoint Error'
                : criticalAlerts.length > 0
                ? `System Alert: ${criticalAlerts.length} Critical System Event(s)`
                : 'System Alert: Pipeline Processing Warning'}
            </h3>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {errorMsg}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {isLiveError && (
            <>
              <button
                onClick={onRetry}
                className="flex items-center gap-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-primary-foreground transition-colors hover:bg-accent/90 focus-visible:outline-2 focus-visible:outline-accent"
              >
                <M3Refresh size={14} />
                Retry API
              </button>
              <button
                onClick={onSwitchDemo}
                className="rounded-lg border border-border/40 bg-panel px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted focus-visible:outline-2 focus-visible:outline-accent"
              >
                Use Simulation Engine
              </button>
            </>
          )}

          <button
            onClick={() => setExpanded(!expanded)}
            className="rounded-md border border-red-300/80 bg-red-100/60 px-2.5 py-1.5 text-xs font-mono text-red-800 hover:bg-red-200 dark:border-red-800 dark:bg-red-900/60 dark:text-red-200"
          >
            {expanded ? 'Hide Diagnostics ▲' : 'Show Diagnostics ▼'}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="mt-4 border-t border-red-200/80 pt-3 dark:border-red-900/50">
          <div className="grid grid-cols-1 gap-3 font-mono text-[11px] sm:grid-cols-3">
            <div className="rounded bg-white/70 p-2.5 dark:bg-red-900/30">
              <span className="font-bold text-red-900 dark:text-red-100">MODE & STATUS</span>
              <div className="mt-1">Mode: {mode.toUpperCase()}</div>
              <div>Connection: {connStatus ?? 'N/A'}</div>
              <div>Target URL: {endpoint}</div>
            </div>

            <div className="rounded bg-white/70 p-2.5 dark:bg-red-900/30">
              <span className="font-bold text-red-900 dark:text-red-100">TAG & MESH STATUS</span>
              <div className="mt-1">Active Tags: {sim.tags.length - lostTags.length} / {sim.tags.length}</div>
              <div>Lost Signals: {lostTags.length}</div>
              <div>Anchors Online: {sim.anchors.length}</div>
            </div>

            <div className="rounded bg-white/70 p-2.5 dark:bg-red-900/30">
              <span className="font-bold text-red-900 dark:text-red-100">PIPELINE STAGES</span>
              <div className="mt-1 space-y-0.5">
                {sim.pipeline.map((p) => (
                  <div key={p.id} className="flex justify-between">
                    <span>{p.label}:</span>
                    <span className={p.status === 'ok' ? 'text-green-700 dark:text-green-400' : 'text-red-700 font-bold dark:text-red-300'}>
                      {p.status.toUpperCase()} ({p.latencyMs}ms)
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
