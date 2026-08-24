import { useState } from 'react'
import type { ConnStatus, Mode } from '../lib/datasource'
import type { SimState } from '../lib/simulation'
import { M3Error, M3Refresh } from './common/MaterialIcon'

/* Hallmark · component: ErrorDiagnosticBanner · genre: modern-minimal · theme: cobalt
 * states: default · hover · focus · active · disabled · loading · error · success
 * contrast: pass (46–50)
 */

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

  if (!isLiveError && criticalAlerts.length === 0 && !hasPipelineErrors) {
    return null
  }

  const errorMsg = isLiveError
    ? error || `Cannot connect to live server at ${endpoint}`
    : criticalAlerts.length > 0
    ? criticalAlerts[0].message
    : 'One or more telemetry pipeline stages reported execution anomalies.'

  return (
    <div className="mb-4 overflow-hidden rounded-xl border border-rose-500/30 bg-rose-500/10 p-3.5 text-foreground shadow-xs backdrop-blur transition-all">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="grid size-7 shrink-0 place-items-center rounded-lg bg-rose-500/20 text-rose-600">
            <M3Error size={18} />
          </div>
          <div>
            <h3 className="text-xs font-semibold tracking-tight text-rose-600 flex items-center gap-2">
              <span>
                {isLiveError
                  ? 'System Alert: Live Hardware Endpoint Error'
                  : criticalAlerts.length > 0
                  ? `System Alert: ${criticalAlerts.length} Critical System Event(s)`
                  : 'System Alert: Pipeline Processing Warning'}
              </span>
              <span className="rounded bg-rose-500/20 px-1.5 py-0.5 font-mono text-[10px] text-rose-700 dark:text-rose-300">
                [LIVE TELEMETRY LOGGED]
              </span>
            </h3>
            <p className="mt-0.5 font-mono text-[11px] text-muted-foreground truncate max-w-xl">
              {errorMsg}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {isLiveError && (
            <>
              <button
                onClick={onRetry}
                className="flex items-center gap-1 rounded-md bg-accent px-2.5 py-1 text-xs font-semibold text-primary-foreground transition-colors hover:bg-accent/90 focus-visible:outline-2 focus-visible:outline-accent"
              >
                <M3Refresh size={13} />
                Retry API
              </button>
              <button
                onClick={onSwitchDemo}
                className="rounded-md border border-border/40 bg-panel px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-muted focus-visible:outline-2 focus-visible:outline-accent"
              >
                Use Simulation Engine
              </button>
            </>
          )}

          <button
            onClick={() => setExpanded(!expanded)}
            className="rounded-md border border-rose-300/80 bg-rose-100/60 px-2.5 py-1 text-xs font-mono text-rose-800 hover:bg-rose-200 dark:border-rose-800 dark:bg-rose-900/60 dark:text-rose-200 transition-colors"
          >
            {expanded ? 'Hide Diagnostics ▲' : 'Show Diagnostics ▼'}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="mt-3 border-t border-rose-200/80 pt-3 dark:border-rose-900/50">
          <div className="grid grid-cols-1 gap-3 font-mono text-[11px] sm:grid-cols-3">
            <div className="rounded-lg bg-background/80 p-2.5 border border-border/40 shadow-xs">
              <span className="font-bold text-rose-700 dark:text-rose-300 block mb-1">MODE & STATUS</span>
              <div>Mode: {mode.toUpperCase()}</div>
              <div>Connection: {connStatus ?? 'N/A'}</div>
              <div className="truncate">Target URL: {endpoint}</div>
            </div>

            <div className="rounded-lg bg-background/80 p-2.5 border border-border/40 shadow-xs">
              <span className="font-bold text-rose-700 dark:text-rose-300 block mb-1">TAG & MESH STATUS</span>
              <div>Active Tags: {sim.tags.length - lostTags.length} / {sim.tags.length}</div>
              <div>Lost Signals: {lostTags.length}</div>
              <div>Anchors Online: {sim.anchors.length}</div>
            </div>

            <div className="rounded-lg bg-background/80 p-2.5 border border-border/40 shadow-xs">
              <span className="font-bold text-rose-700 dark:text-rose-300 block mb-1">PIPELINE STAGES</span>
              <div className="space-y-0.5">
                {sim.pipeline.map((p) => (
                  <div key={p.id} className="flex justify-between">
                    <span>{p.label}:</span>
                    <span className={p.status === 'ok' ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 font-bold dark:text-rose-300'}>
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

