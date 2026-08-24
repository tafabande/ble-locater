import type { PipelineStage } from '../../lib/simulation'
import { M3CheckCircle, M3Warning } from '../common/MaterialIcon'

interface Props {
  pipeline: PipelineStage[]
}

const STATUS_COLOR: Record<PipelineStage['status'], string> = {
  ok: 'var(--status-online)',
  warn: 'var(--status-stale)',
  error: 'var(--status-lost)',
}

export function PipelineStatus({ pipeline }: Props) {
  const worst = pipeline.some((s) => s.status === 'error')
    ? 'error'
    : pipeline.some((s) => s.status === 'warn')
    ? 'warn'
    : 'ok'

  return (
    <div className="rounded-xl border border-border/40 bg-card p-4 sm:p-5 shadow-xs">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold">Processing Pipeline</h2>
          <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">
            Raw BLE → 3D position → geofence · end-to-end
          </p>
        </div>
        <span
          className="flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium"
          style={{ background: 'var(--accent-soft)', color: STATUS_COLOR[worst] }}
        >
          {worst === 'ok' ? <M3CheckCircle size={14} /> : <M3Warning size={14} />}
          {worst === 'ok' ? 'Healthy' : worst === 'warn' ? 'Degraded' : 'Attention'}
        </span>
      </div>

      <div className="flex gap-1.5 overflow-x-auto pb-1">
        {pipeline.map((s, i) => (
          <div key={s.id} className="flex items-center gap-1.5">
            <div className="min-w-[104px] rounded-md border border-border bg-panel px-2.5 py-2">
              <div className="flex items-center gap-1.5">
                <span
                  className="size-1.5 shrink-0 rounded-full"
                  style={{
                    background: STATUS_COLOR[s.status],
                    animation: s.status !== 'ok' ? 'pulse-dot 1.2s ease-in-out infinite' : undefined,
                  }}
                />
                <span className="truncate text-[11px] font-medium">{s.label}</span>
              </div>
              <div className="mt-1 truncate font-mono text-[10px] text-muted-foreground">{s.detail}</div>
              <div className="mt-0.5 font-mono text-[10px] tabular-nums text-muted-foreground">{s.latencyMs} ms</div>
            </div>
            {i < pipeline.length - 1 && (
              <svg viewBox="0 0 12 12" className="size-3 shrink-0 text-border" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M2 6h7M6 3l3 3-3 3" />
              </svg>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
