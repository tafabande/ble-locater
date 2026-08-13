import type { ConnStatus } from '../lib/datasource'

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
    <div className="grid min-h-[420px] place-items-center rounded-[var(--radius)] border border-dashed border-border bg-card p-8">
      <div className="max-w-md text-center">
        <div className="relative mx-auto mb-5 grid size-14 place-items-center rounded-full bg-panel">
          {connecting && (
            <span
              className="absolute inset-0 rounded-full border-2 border-accent"
              style={{ animation: 'ping-ring 1.8s ease-out infinite' }}
            />
          )}
          <span
            className="size-3 rounded-full"
            style={{ background: connecting ? 'var(--status-stale)' : 'var(--status-lost)' }}
          />
        </div>

        <h2 className="font-serif text-lg font-semibold">
          {connecting ? 'Connecting to anchor mesh…' : 'No live data source'}
        </h2>
        <p className="mx-auto mt-2 max-w-sm text-sm text-muted-foreground">
          {connecting
            ? 'Polling the ESP32 web server for real-time positioning packets.'
            : 'Could not reach the anchor mesh web server. Check that a node is powered on, joined to the WiFi, and serving the positioning API.'}
        </p>

        <div className="mx-auto mt-5 w-full max-w-sm rounded-md border border-border bg-panel p-3 text-left font-mono text-[11px]">
          <div className="flex justify-between">
            <span className="text-muted-foreground">GET</span>
            <span className="truncate pl-2 text-foreground">{endpoint}</span>
          </div>
          {error && (
            <div className="mt-1 flex justify-between">
              <span className="text-muted-foreground">error</span>
              <span className="pl-2" style={{ color: 'var(--status-lost)' }}>
                {error}
              </span>
            </div>
          )}
        </div>

        {!connecting && (
          <div className="mt-5 flex items-center justify-center gap-2">
            <button
              onClick={onRetry}
              className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90 focus:ring-2 focus:ring-ring"
            >
              Retry connection
            </button>
            <button
              onClick={onDemo}
              className="rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
            >
              Switch to Demo
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
