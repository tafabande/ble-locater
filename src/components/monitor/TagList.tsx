import type { Tag } from '../../lib/simulation'
import { STATUS_META, batteryColor, relativeTime } from '../../lib/format'

interface Props {
  tags: Tag[]
  selected: string | null
  onSelect: (id: string | null) => void
}

export function TagList({ tags, selected, onSelect }: Props) {
  return (
    <div className="rounded-[var(--radius)] border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold">Tag Roster</h2>
        <span className="font-mono text-[11px] text-muted-foreground">{tags.length} devices</span>
      </div>
      <div className="max-h-[320px] overflow-y-auto">
        {tags.map((t) => {
          const meta = STATUS_META[t.status]
          const isSel = selected === t.id
          return (
            <button
              key={t.id}
              onClick={() => onSelect(isSel ? null : t.id)}
              className={`flex w-full items-center gap-3 border-b border-border px-4 py-2.5 text-left transition-colors last:border-0 ${
                isSel ? 'bg-accent-soft' : 'hover:bg-muted'
              }`}
            >
              <span
                className="size-2 shrink-0 rounded-full"
                style={{
                  background: meta.color,
                  animation: t.status === 'online' ? 'pulse-dot 1.8s ease-in-out infinite' : undefined,
                }}
              />
              <span className="min-w-0 flex-1">
                <span className="flex items-baseline justify-between gap-2">
                  <span className="truncate text-sm font-medium">{t.label}</span>
                  <span className="font-mono text-[11px] tabular-nums text-muted-foreground">{t.readings[0].rssi} dBm</span>
                </span>
                <span className="flex items-center justify-between gap-2">
                  <span className="font-mono text-[10px] text-muted-foreground">
                    TAG-{t.id} · {t.zone} · {t.nearest}
                  </span>
                  <span className="flex items-center gap-1 font-mono text-[10px] tabular-nums" style={{ color: batteryColor(t.battery) }}>
                    {Math.round(t.battery)}%
                  </span>
                </span>
              </span>
            </button>
          )
        })}
      </div>
      <div className="border-t border-border px-4 py-2 font-mono text-[10px] text-muted-foreground">
        Last packet: {tags.length ? relativeTime(Date.now() - tags[0].lastSeen) : '—'}
      </div>
    </div>
  )
}
