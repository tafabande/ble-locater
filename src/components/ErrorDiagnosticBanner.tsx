import { useState } from 'react'
import type { ConnStatus, Mode } from '../lib/datasource'
import type { Alert, SimState } from '../lib/simulation'

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

  return (
    <div className="mb-6 overflow-hidden rounded-lg border border-red-200 bg-red-50/90 p-4 text-red-900 shadow-sm backdrop-blur dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-200">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex size-7 shrink-0 place-items-center rounded-full bg-red-100 text-center font-mono text-sm font-bold text-red-600 dark:bg-red-900/60 dark:text-red-300">
            !
          </span>
          <div>
            <h3 className="text-sm font-bold tracking-tight">
              {isLiveError
                ? 'Loud Alert: Live Hardware Endpoint Error'
                : criticalAlerts.length > 0
                ? `Loud Alert: ${criticalAlerts.length} Critical System Event(s)`
                : 'Loud Alert: Pipeline Processing Warning'}
            </h3>
            <p className="mt-0.5 text-xs text-red-700 dark:text-red-300">
              {isLiveError
                ? error || `Cannot connect to live server at ${endpoint}`
                : criticalAlerts.length > 0
                ? criticalAlerts[0].message
                : 'One or more telemetry pipeline stages reported execution anomalies.'}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {isLiveError && (
            <>
              <button
                onClick={onRetry}
                className="rounded-md bg-red-600 px-3 py-1.5 text-xs font-semibold text-white transition-opacity hover:opacity-90"
              >
                Retry API
              </button>
              <button
                onClick={onSwitchDemo}
                className="rounded-md border border-red-300 bg-white px-3 py-1.5 text-xs font-medium text-red-800 transition-colors hover:bg-red-100 dark:border-red-800 dark:bg-red-900/40 dark:text-red-200"
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
