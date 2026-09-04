import type { Tag } from '../../lib/simulation'
import { STATUS_META, batteryColor, relativeTime } from '../../lib/format'

interface Props {
  tags: Tag[]
  selected: string | null
  onSelect: (id: string | null) => void
}

export function TagList({ tags, selected, onSelect }: Props) {
  return (
    <div className="rounded-2xl bg-card p-4 sm:p-5 shadow-sm space-y-3">
      <div className="flex items-center justify-between pb-1">
        <h2 className="text-sm font-bold text-foreground tracking-tight">Tag Roster</h2>
        <span className="font-mono text-xs font-semibold text-muted-foreground">{tags.length} devices</span>
      </div>
      <div className="max-h-[320px] overflow-y-auto space-y-1">
        {tags.map((t) => {
          const meta = STATUS_META[t.status]
          const isSel = selected === t.id
          return (
            <button
              key={t.id}
              onClick={() => onSelect(isSel ? null : t.id)}
              className={`flex w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-left transition-all focus-visible:outline-2 focus-visible:outline-accent cursor-pointer ${
                isSel ? 'bg-accent-soft shadow-xs' : 'hover:bg-muted/50'
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
                  <span className="truncate text-sm font-semibold">{t.label}</span>
                  <span className="font-mono text-[11px] tabular-nums text-muted-foreground">{t.readings[0].rssi} dBm</span>
                </span>
                <span className="flex items-center justify-between gap-2 mt-0.5">
                  <span className="font-mono text-[10px] text-muted-foreground">
                    TAG-{t.id} · {t.zone} · {t.nearest}
                  </span>
                  <span className="flex items-center gap-1 font-mono text-[10px] tabular-nums font-semibold" style={{ color: batteryColor(t.battery) }}>
                    {Math.round(t.battery)}%
                  </span>
                </span>
              </span>
            </button>
          )
        })}
      </div>
      <div className="pt-2 font-mono text-[10px] text-muted-foreground">
        Last packet: {tags.length ? relativeTime(Date.now() - tags[0].lastSeen) : '—'}
      </div>
    </div>
  )
}
