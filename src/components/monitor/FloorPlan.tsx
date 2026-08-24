import { useState } from 'react'
import type { MapItem, SimState } from '../../lib/simulation'
import { STATUS_META } from '../../lib/format'
import { M3Search, M3Refresh } from '../common/MaterialIcon'

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
  const [zoom, setZoom] = useState<number>(1)
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 })

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

  const handleZoomIn = () => setZoom((z) => Math.min(3, Math.round((z + 0.35) * 100) / 100))
  const handleZoomOut = () => setZoom((z) => Math.max(1, Math.round((z - 0.35) * 100) / 100))
  const handleResetZoom = () => {
    setZoom(1)
    setPan({ x: 0, y: 0 })
  }

  // Compute viewBox dynamically based on zoom and pan
  const viewBoxSize = 100 / zoom
  const vbX = Math.max(0, Math.min(100 - viewBoxSize, pan.x + (50 - viewBoxSize / 2)))
  const vbY = Math.max(0, Math.min(100 - viewBoxSize, pan.y + (50 - viewBoxSize / 2)))
  const actualVb = zoom === 1 ? '0 0 100 100' : `${vbX} ${vbY} ${viewBoxSize} ${viewBoxSize}`

  return (
    <div className="relative overflow-hidden rounded-xl border border-border/40 bg-panel shadow-xs">
      <svg viewBox={actualVb} className="block w-full touch-manipulation" onClick={() => onSelect(null)}>
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
              fill={z.restricted ? 'url(#restricted)' : 'var(--card)'}
              fillOpacity={z.restricted ? 1 : 0.6}
              stroke={z.restricted ? 'var(--status-lost)' : 'var(--border)'}
              strokeWidth="0.3"
              strokeDasharray={z.restricted ? '1 0.8' : undefined}
            />
            {/* High-Contrast Mobile Room Label Pill */}
            <rect
              x={z.x + 1}
              y={z.y + 1.2}
              width={z.name.length * 1.5 + (z.restricted ? 3.5 : 2)}
              height="3.2"
              rx="0.8"
              fill="var(--card)"
              fillOpacity="0.9"
              stroke="var(--border)"
              strokeWidth="0.15"
            />
            <text
              x={z.x + 2}
              y={z.y + 3.4}
              fontSize="2"
              fontWeight="600"
              fill={z.restricted ? 'var(--status-lost)' : 'var(--foreground)'}
              fontFamily="var(--font-sans)"
            >
              {z.restricted ? '⚠ ' : ''}
              {z.name}
            </text>
          </g>
        ))}

        {/* static map geometry: furniture, doors, walls */}
        {mapItems.map((m) => {
          if (m.kind === 'door') {
            return <rect key={m.id} x={m.x} y={m.y} width={m.w} height={m.h} fill="var(--panel)" stroke="var(--accent)" strokeWidth="0.25" strokeDasharray="0.5 0.5" />
          }
          if (m.kind === 'furniture') {
            return (
              <g key={m.id}>
                <rect x={m.x} y={m.y} width={m.w} height={m.h} rx="0.4" fill="url(#furn)" stroke="var(--muted-foreground)" strokeWidth="0.2" />
                <rect x={m.x} y={m.y} width={m.w} height={m.h} rx="0.4" fill="var(--muted)" fillOpacity="0.35" />
                {m.w > 8 && (
                  <g>
                    <rect x={m.x + m.w / 2 - (m.label.length * 0.7)} y={m.y + m.h / 2 - 1.2} width={m.label.length * 1.4} height="2.4" rx="0.6" fill="var(--card)" fillOpacity="0.85" />
                    <text x={m.x + m.w / 2} y={m.y + m.h / 2 + 0.5} fontSize="1.4" fontWeight="500" textAnchor="middle" fill="var(--muted-foreground)" fontFamily="var(--font-sans)">
                      {m.label}
                    </text>
                  </g>
                )}
              </g>
            )
          }
          return <rect key={m.id} x={m.x} y={m.y} width={m.w} height={m.h} rx="0.2" fill="var(--foreground)" fillOpacity="0.75" />
        })}

        {/* trilateration links for the active/focused tag */}
        {activeTag &&
          activeTag.readings
            .filter((r) => r.used)
            .map((r) => {
              const a = sim.anchors.find((an) => an.id === r.anchorId)
              if (!a) return null
              return <line key={r.anchorId} x1={activeTag.x} y1={activeTag.y} x2={a.x} y2={a.y} stroke="var(--accent)" strokeWidth="0.25" strokeDasharray="0.6 0.6" opacity="0.85" />
            })}

        {/* uncertainty radii */}
        {visTags.map((t) => (
          <circle
            key={`u-${t.id}`}
            cx={t.x}
            cy={t.y}
            r={t.uncertainty * M2U}
            fill={t.violating ? 'var(--status-lost)' : 'var(--accent)'}
            fillOpacity={active === t.id || focus === t.id ? 0.14 : 0.06}
            stroke={t.violating ? 'var(--status-lost)' : 'var(--accent)'}
            strokeWidth="0.12"
            strokeOpacity={active === t.id || focus === t.id ? 0.6 : 0.25}
          />
        ))}

        {/* anchors with mobile touch target and high-contrast labels */}
        {visAnchors.map((a) => {
          const hl = focusAnchor?.id === a.id
          return (
            <g key={a.id} className="cursor-pointer" onClick={(e) => { e.stopPropagation(); onSelect(selected === a.id ? null : a.id) }}>
              {/* Invisible 44px+ mobile touch hit target */}
              <circle cx={a.x} cy={a.y} r="4.2" fill="transparent" />
              <rect x={a.x - 1.2} y={a.y - 1.2} width="2.4" height="2.4" rx="0.5" fill={hl ? 'var(--accent)' : 'var(--card)'} stroke="var(--foreground)" strokeWidth="0.3" />
              <circle cx={a.x} cy={a.y} r="0.6" fill={hl ? 'var(--primary-foreground)' : 'var(--foreground)'} />
              
              {/* Label backdrop pill */}
              <rect x={a.x + 1.6} y={a.y - 2.6} width={a.id.length * 1.3 + (a.host ? 2.5 : 1)} height="2.6" rx="0.6" fill="var(--card)" fillOpacity="0.9" stroke="var(--border)" strokeWidth="0.15" />
              <text x={a.x + 2} y={a.y - 0.8} fontSize="1.5" fontWeight="600" fill="var(--foreground)" fontFamily="var(--font-mono)">
                {a.id}{a.host ? ' ⧉' : ''}
              </text>
            </g>
          )
        })}

        {/* trails */}
        {visTags.map((t) =>
          t.trail.length > 1 ? (
            <polyline key={`tr-${t.id}`} points={t.trail.map((p) => `${p.x},${p.y}`).join(' ')} fill="none" stroke={STATUS_META[t.status].color} strokeWidth="0.25" strokeLinecap="round" opacity={active === t.id || focus ? 0.6 : 0.2} />
          ) : null
        )}

        {/* tags with 44px touch targets and high contrast labels */}
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
            >
              {/* Invisible 44px+ mobile touch hit target */}
              <circle cx={t.x} cy={t.y} r="4.2" fill="transparent" />

              {(t.status === 'online' || t.violating) && (
                <circle cx={t.x} cy={t.y} r="1.4" fill={color} opacity="0.5">
                  <animate attributeName="r" from="1.2" to={t.violating ? '4.2' : '3.4'} dur={t.violating ? '1.2s' : '2s'} repeatCount="indefinite" />
                  <animate attributeName="opacity" from="0.5" to="0" dur={t.violating ? '1.2s' : '2s'} repeatCount="indefinite" />
                </circle>
              )}
              <circle cx={t.x} cy={t.y} r={isActive ? 1.8 : 1.3} fill={color} stroke="var(--card)" strokeWidth="0.35" />
              
              {/* Always show high-contrast mobile pill label for active or all tags */}
              <g transform={`translate(${t.x}, ${t.y - (isActive ? 3.6 : 3.0)})`}>
                <rect x={-(t.label.length * 0.8 + 0.8)} y="-1.8" width={t.label.length * 1.6 + 1.6} height="2.6" rx="0.7" fill="var(--card)" fillOpacity="0.95" stroke={color} strokeWidth="0.25" />
                <text x="0" y="0" fontSize="1.5" textAnchor="middle" fill="var(--foreground)" fontFamily="var(--font-sans)" fontWeight="700">
                  {t.label}
                </text>
              </g>
            </g>
          )
        })}
      </svg>

      {/* Floating Mobile Zoom & Pan Controls HUD */}
      <div className="absolute right-2 top-2 flex flex-col gap-1.5 z-20">
        <button
          onClick={handleZoomIn}
          title="Zoom In"
          className="grid size-8 place-items-center rounded-lg border border-border/50 bg-card/90 font-bold text-foreground shadow-sm backdrop-blur hover:bg-muted focus-visible:outline-2 focus-visible:outline-accent active:scale-95 transition-transform"
        >
          +
        </button>
        <button
          onClick={handleZoomOut}
          disabled={zoom <= 1}
          title="Zoom Out"
          className="grid size-8 place-items-center rounded-lg border border-border/50 bg-card/90 font-bold text-foreground shadow-sm backdrop-blur disabled:opacity-40 hover:bg-muted focus-visible:outline-2 focus-visible:outline-accent active:scale-95 transition-transform"
        >
          −
        </button>
        {zoom > 1 && (
          <button
            onClick={handleResetZoom}
            title="Reset Zoom"
            className="grid size-8 place-items-center rounded-lg border border-border/50 bg-card/90 text-xs font-bold text-accent shadow-sm backdrop-blur hover:bg-muted focus-visible:outline-2 focus-visible:outline-accent active:scale-95 transition-transform"
          >
            ⟲
          </button>
        )}
      </div>

      {activeTag && (
        <div className="pointer-events-none absolute bottom-2 left-2 rounded-xl border border-border/40 bg-card/95 p-2.5 font-mono text-[11px] shadow-md backdrop-blur max-w-[calc(100%-1rem)]">
          <div className="font-semibold text-foreground flex items-center gap-1.5">
            <span className="size-2 rounded-full" style={{ background: STATUS_META[activeTag.status].color }} />
            <span>TAG-{activeTag.id}</span>
            <span className="text-muted-foreground">• {activeTag.label}</span>
          </div>
          <div className="text-muted-foreground text-[10px] mt-0.5">
            x {activeTag.x.toFixed(1)} · y {activeTag.y.toFixed(1)} · {activeTag.zone}
          </div>
          <div className="text-muted-foreground text-[10px]">
            nearest {activeTag.nearest} · {activeTag.readings[0].rssi} dBm · σ {activeTag.uncertainty}m
          </div>
          {activeTag.violating && <div className="text-rose-600 font-bold text-[10px] mt-0.5">⚠ Geofence breach</div>}
        </div>
      )}
    </div>
  )
}
