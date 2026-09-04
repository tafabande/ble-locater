import TypeIt from 'typeit-react'
import type { ConnStatus } from '../lib/datasource'
import { M3Refresh, M3Error } from './common/MaterialIcon'

interface Props {
  status: ConnStatus
  endpoint: string
  error: string | null
  onRetry: () => void
  onDemo: () => void
}

export function ConnectionScreen({ status, endpoint, error, onRetry, onDemo }: Props) {
  const connecting = status === 'connecting'
  return (
    <div className="grid min-h-[420px] place-items-center rounded-3xl bg-card p-8 sm:p-12 shadow-xl">
      <div className="max-w-md text-center">
        <div className="relative mx-auto mb-5 grid size-14 place-items-center rounded-2xl bg-panel shadow-inner">
          {connecting ? (
            <M3Refresh size={24} className="animate-spin text-accent" />
          ) : (
            <M3Error size={24} className="text-rose-600" />
          )}
        </div>

        <h2 className="text-xl font-bold text-foreground tracking-tight">
          {connecting ? 'Connecting to anchor mesh…' : 'No live data source'}
        </h2>
        <div className="mx-auto mt-2 max-w-sm text-sm text-muted-foreground min-h-[40px] leading-relaxed">
          {connecting ? (
            <TypeIt options={{ speed: 25, cursor: false, waitUntilVisible: false }}>
              Polling the ESP32 web server for real-time positioning telemetry packets...
            </TypeIt>
          ) : (
            'Could not reach the anchor mesh web server. Check that a node is powered on, joined to the WiFi, and serving the positioning API.'
          )}
        </div>

        <div className="mx-auto mt-5 w-full max-w-sm rounded-xl bg-muted/40 p-3.5 text-left font-mono text-[11px] space-y-1">
          <div className="flex justify-between">
            <span className="text-muted-foreground font-semibold">GET</span>
            <span className="truncate pl-2 text-foreground">{endpoint}</span>
          </div>
          {error && (
            <div className="mt-1 flex justify-between">
              <span className="text-muted-foreground font-semibold">error</span>
              <span className="pl-2 text-rose-600 font-semibold">
                {error}
              </span>
            </div>
          )}
        </div>

        {!connecting && (
          <div className="mt-6 flex items-center justify-center gap-3">
            <button
              onClick={onRetry}
              className="flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-primary-foreground transition-all hover:bg-accent/90 focus-visible:outline-2 focus-visible:outline-accent shadow-sm hover:shadow-md cursor-pointer"
            >
              <M3Refresh size={14} />
              Retry Connection
            </button>
            <button
              onClick={onDemo}
              className="rounded-xl bg-muted/40 hover:bg-muted px-4 py-2.5 text-xs font-semibold text-foreground transition-all focus-visible:outline-2 focus-visible:outline-accent cursor-pointer"
            >
              Switch to Simulation
            </button>
          </div>
        )}

        <p className="mt-4 font-mono text-[11px] text-muted-foreground">
          Expected payload: <span className="text-foreground">{'{ tags: [{ id, x, y, … }] }'}</span>
        </p>
      </div>
    </div>
  )
}
