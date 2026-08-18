import { useState } from 'react'
import type { MapItem, SimState } from '../../lib/simulation'
import { STATUS_META } from '../../lib/format'

interface Props {
  sim: SimState
  mapItems: MapItem[]
  floor: number
  selected: string | null
  onSelect: (id: string | null) => void
  focus: string | null
  onFocus: (id: string | null) => void
}

const M2U = 1 / 0.28

export function FloorPlan({ sim, mapItems, floor, selected, onSelect, focus }: Props) {
  const [hover, setHover] = useState<string | null>(null)
  const active = hover ?? selected

  // restrict to the active storey
  const floorTags = sim.tags.filter((t) => t.floor === floor)
  const floorAnchors = sim.anchors.filter((a) => a.floor === floor)

  // focus isolation
  const focusTag = sim.tags.find((t) => t.id === focus)
  const focusAnchor = sim.anchors.find((a) => a.id === focus)
  const usedAnchorIds = focusTag ? new Set(focusTag.readings.filter((r) => r.used).map((r) => r.anchorId)) : null

  const visTags = focusTag
    ? floorTags.filter((t) => t.id === focusTag.id)
    : focusAnchor
    ? floorTags.filter((t) => t.readings.some((r) => r.used && r.anchorId === focusAnchor.id))
    : floorTags
  const visAnchors = focusTag
    ? floorAnchors.filter((a) => usedAnchorIds!.has(a.id))
    : focusAnchor
    ? floorAnchors.filter((a) => a.id === focusAnchor.id)
    : floorAnchors

  const activeTag = sim.tags.find((t) => t.id === active) ?? focusTag ?? null

  return (
    <div className="relative overflow-hidden rounded-md border border-border bg-panel">
      <svg viewBox="0 0 100 100" className="block w-full" onClick={() => onSelect(null)}>
        <defs>
          <pattern id="grid" width="4" height="4" patternUnits="userSpaceOnUse">
            <path d="M4 0H0V4" fill="none" stroke="var(--border)" strokeWidth="0.1" />
          </pattern>
          <pattern id="restricted" width="2.4" height="2.4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="2.4" stroke="var(--status-lost)" strokeWidth="0.35" opacity="0.35" />
          </pattern>
          <pattern id="furn" width="1.8" height="1.8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="1.8" stroke="var(--muted-foreground)" strokeWidth="0.2" opacity="0.5" />
          </pattern>
        </defs>
        <rect x="0" y="0" width="100" height="100" fill="url(#grid)" />

        {/* Uploaded Blueprint Image Overlay */}
        {localStorage.getItem('rtls_blueprint_img') && (
          <image
            href={localStorage.getItem('rtls_blueprint_img')!}
            x="0"
            y="0"
            width="100"
            height="100"
            preserveAspectRatio="none"
            opacity={Number(localStorage.getItem('rtls_blueprint_opacity')) || 0.35}
          />
        )}

        {/* geofences / rooms */}
        {sim.geofences.map((z) => (
          <g key={z.id}>
            <rect
              x={z.x}
              y={z.y}
              width={z.w}
              height={z.h}
              rx="1"
              fill={z.restricted ? 'url(#restricted)' : 'var(--muted)'}
              fillOpacity={z.restricted ? 1 : 0.4}
              stroke={z.restricted ? 'var(--status-lost)' : 'var(--border)'}
              strokeWidth="0.2"
              strokeDasharray={z.restricted ? '1 0.8' : undefined}
            />
            <text x={z.x + 1.4} y={z.y + 3} fontSize="1.9" fill={z.restricted ? 'var(--status-lost)' : 'var(--muted-foreground)'} fontFamily="var(--font-mono)">
              {z.restricted ? '⚠ ' : ''}
              {z.name}
            </text>
          </g>
        ))}

        {/* static map geometry: furniture, doors, walls */}
        {mapItems.map((m) => {
          if (m.kind === 'door') {
            return <rect key={m.id} x={m.x} y={m.y} width={m.w} height={m.h} fill="var(--panel)" stroke="var(--accent)" strokeWidth="0.2" strokeDasharray="0.5 0.5" />
          }
          if (m.kind === 'furniture') {
            return (
              <g key={m.id}>
                <rect x={m.x} y={m.y} width={m.w} height={m.h} rx="0.4" fill="url(#furn)" stroke="var(--muted-foreground)" strokeWidth="0.2" />
                <rect x={m.x} y={m.y} width={m.w} height={m.h} rx="0.4" fill="var(--muted)" fillOpacity="0.35" />
                {m.w > 8 && (
                  <text x={m.x + m.w / 2} y={m.y + m.h / 2 + 0.6} fontSize="1.5" textAnchor="middle" fill="var(--muted-foreground)" fontFamily="var(--font-mono)">
                    {m.label}
                  </text>
                )}
              </g>
            )
          }
          return <rect key={m.id} x={m.x} y={m.y} width={m.w} height={m.h} rx="0.2" fill="var(--foreground)" fillOpacity="0.72" />
        })}

        {/* trilateration links for the active/focused tag */}
        {activeTag &&
          activeTag.readings
            .filter((r) => r.used)
            .map((r) => {
              const a = sim.anchors.find((an) => an.id === r.anchorId)
              if (!a) return null
              return <line key={r.anchorId} x1={activeTag.x} y1={activeTag.y} x2={a.x} y2={a.y} stroke="var(--accent)" strokeWidth="0.18" strokeDasharray="0.6 0.6" opacity="0.7" />
            })}

        {/* uncertainty radii */}
        {visTags.map((t) => (
          <circle
            key={`u-${t.id}`}
            cx={t.x}
            cy={t.y}
            r={t.uncertainty * M2U}
            fill={t.violating ? 'var(--status-lost)' : 'var(--accent)'}
            fillOpacity={active === t.id || focus === t.id ? 0.12 : 0.05}
            stroke={t.violating ? 'var(--status-lost)' : 'var(--accent)'}
            strokeWidth="0.1"
            strokeOpacity={active === t.id || focus === t.id ? 0.5 : 0.2}
          />
        ))}

        {/* anchors */}
        {visAnchors.map((a) => {
          const hl = focusAnchor?.id === a.id
          return (
            <g key={a.id}>
              <rect x={a.x - 1.1} y={a.y - 1.1} width="2.2" height="2.2" rx="0.4" fill={hl ? 'var(--accent)' : 'var(--card)'} stroke="var(--foreground)" strokeWidth="0.22" />
              <circle cx={a.x} cy={a.y} r="0.55" fill={hl ? 'var(--primary-foreground)' : 'var(--foreground)'} />
              <text x={a.x + 1.6} y={a.y - 1.4} fontSize="1.5" fill="var(--foreground)" fontFamily="var(--font-mono)">
                {a.id}
                {a.host ? ' ⧉' : ''}
              </text>
            </g>
          )
        })}

        {/* trails */}
        {visTags.map((t) =>
          t.trail.length > 1 ? (
            <polyline key={`tr-${t.id}`} points={t.trail.map((p) => `${p.x},${p.y}`).join(' ')} fill="none" stroke={STATUS_META[t.status].color} strokeWidth="0.2" strokeLinecap="round" opacity={active === t.id || focus ? 0.5 : 0.16} />
          ) : null
        )}

        {/* tags */}
        {visTags.map((t) => {
          const isActive = active === t.id || focus === t.id
          const color = t.violating ? 'var(--status-lost)' : STATUS_META[t.status].color
          return (
            <g
              key={t.id}
              onMouseEnter={() => setHover(t.id)}
              onMouseLeave={() => setHover(null)}
              onClick={(e) => {
                e.stopPropagation()
                onSelect(selected === t.id ? null : t.id)
              }}
              className="cursor-pointer"
              style={{ transition: 'transform 1.2s linear' }}
            >
              {(t.status === 'online' || t.violating) && (
                <circle cx={t.x} cy={t.y} r="1.2" fill={color} opacity="0.5">
                  <animate attributeName="r" from="1" to={t.violating ? '4' : '3.2'} dur={t.violating ? '1.2s' : '2s'} repeatCount="indefinite" />
                  <animate attributeName="opacity" from="0.5" to="0" dur={t.violating ? '1.2s' : '2s'} repeatCount="indefinite" />
                </circle>
              )}
              <circle cx={t.x} cy={t.y} r={isActive ? 1.5 : 1.1} fill={color} stroke="var(--card)" strokeWidth="0.3" />
              {isActive && (
                <text x={t.x} y={t.y - 2.4} fontSize="1.6" textAnchor="middle" fill="var(--foreground)" fontFamily="var(--font-mono)" fontWeight="600">
                  {t.label}
                </text>
              )}
            </g>
          )
        })}
      </svg>

      {activeTag && (
        <div className="pointer-events-none absolute bottom-2 left-2 rounded-md border border-border bg-card/95 px-3 py-2 font-mono text-[11px] shadow-sm backdrop-blur">
          <div className="font-semibold text-foreground">TAG-{activeTag.id}</div>
          <div className="text-muted-foreground">
            x {activeTag.x.toFixed(1)} · y {activeTag.y.toFixed(1)} · {activeTag.zone}
          </div>
          <div className="text-muted-foreground">
            nearest {activeTag.nearest} · {activeTag.readings[0].rssi} dBm · σ {activeTag.uncertainty} m
          </div>
          {activeTag.violating && <div style={{ color: 'var(--status-lost)' }}>⚠ Geofence breach</div>}
        </div>
      )}
    </div>
  )
}
