/* Hallmark · pre-emit critique: P5 H5 E5 S5 R5 V5 */
import { useRef, useState } from 'react'
import { FLOORS, STOREY_HEIGHT, type MapItem, type SimState } from '../../lib/simulation'
import { STATUS_META } from '../../lib/format'

interface Props {
  sim: SimState
  mapItems: MapItem[]
  activeFloor: number
  selected: string | null
  onSelect: (id: string | null) => void
  focus: string | null
  gridSpacing?: number
}

const VB = { x: -125, y: -150, w: 250, h: 300 }
const SX = 0.95 // horizontal projection scale
const SZ = 1.7 // vertical (height) projection scale
type Cam = { yaw: number; pitch: number; zoom: number; px: number; py: number }
const DEFAULT_CAM: Cam = { yaw: -0.72, pitch: 0.5, zoom: 1.35, px: 0, py: 12 }

const poly = (...pts: { X: number; Y: number }[]) => pts.map((p) => `${p.X.toFixed(2)},${p.Y.toFixed(2)}`).join(' ')

export function BuildingView3D({ sim, mapItems, activeFloor, selected, onSelect, focus, gridSpacing = 4 }: Props) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [hover, setHover] = useState<string | null>(null)
  const [cam, setCam] = useState<Cam>(DEFAULT_CAM)
  const drag = useRef<{ x: number; y: number; mode: 'orbit' | 'pan' } | null>(null)
  const active = hover ?? selected

  // world (floor %, z units) → screen, using the current camera yaw/pitch
  const iso = (x: number, y: number, z = 0) => {
    const nx = x - 50
    const ny = y - 50
    const c = Math.cos(cam.yaw)
    const s = Math.sin(cam.yaw)
    const rx = nx * c - ny * s
    const ry = nx * s + ny * c
    return { X: rx * SX, Y: ry * cam.pitch - z * SZ, depth: ry }
  }

  // ---- navigation --------------------------------------------------------
  const svgDelta = (dx: number, dy: number) => {
    const r = svgRef.current!.getBoundingClientRect()
    return { dx: (dx / r.width) * VB.w, dy: (dy / r.height) * VB.h }
  }
  const onPointerDown = (e: React.PointerEvent) => {
    drag.current = { x: e.clientX, y: e.clientY, mode: e.shiftKey || e.button === 2 ? 'pan' : 'orbit' }
    ;(e.currentTarget as Element).setPointerCapture?.(e.pointerId)
  }
  const onPointerMove = (e: React.PointerEvent) => {
    if (!drag.current) return
    const dx = e.clientX - drag.current.x
    const dy = e.clientY - drag.current.y
    drag.current.x = e.clientX
    drag.current.y = e.clientY
    const mode = drag.current.mode
    setCam((c) => {
      if (mode === 'pan') {
        const d = svgDelta(dx, dy)
        return { ...c, px: c.px + d.dx, py: c.py + d.dy }
      }
      return { ...c, yaw: c.yaw + dx * 0.012, pitch: Math.max(0.12, Math.min(0.85, c.pitch - dy * 0.004)) }
    })
  }
  const onPointerUp = () => (drag.current = null)
  const onWheel = (e: React.WheelEvent) => {
    setCam((c) => ({ ...c, zoom: Math.max(0.6, Math.min(4, c.zoom * (e.deltaY < 0 ? 1.12 : 0.89))) }))
  }

  const handleZoomIn = () => setCam((c) => ({ ...c, zoom: Math.min(3.5, Math.round(c.zoom * 1.25 * 100) / 100) }))
  const handleZoomOut = () => setCam((c) => ({ ...c, zoom: Math.max(0.6, Math.round(c.zoom * 0.8 * 100) / 100) }))

  // ---- focus isolation (search) -----------------------------------------
  const focusTag = sim.tags.find((t) => t.id === focus)
  const focusAnchor = sim.anchors.find((a) => a.id === focus)
  const usedAnchorIds = focusTag ? new Set(focusTag.readings.filter((r) => r.used).map((r) => r.anchorId)) : null
  const tagVisible = (t: SimState['tags'][number]) =>
    focusTag ? t.id === focusTag.id : focusAnchor ? t.readings.some((r) => r.used && r.anchorId === focusAnchor.id) : true
  const anchorVisible = (id: string) =>
    focusTag ? usedAnchorIds!.has(id) : focusAnchor ? id === focusAnchor.id : true

  const activeTag = sim.tags.find((t) => t.id === active) ?? focusTag ?? null

  // Extruded box footprint at a given z base.
  const prism = (item: MapItem, zBase: number, ht: number, top: string, side: string, edge: string, op: number) => {
    const { x, y, w, h } = item
    const b = [iso(x, y, zBase), iso(x + w, y, zBase), iso(x + w, y + h, zBase), iso(x, y + h, zBase)]
    const t = [iso(x, y, zBase + ht), iso(x + w, y, zBase + ht), iso(x + w, y + h, zBase + ht), iso(x, y + h, zBase + ht)]
    return (
      <g key={item.id} stroke={edge} strokeWidth="0.2" strokeLinejoin="round" opacity={op}>
        <polygon points={poly(b[1], b[2], t[2], t[1])} fill={side} />
        <polygon points={poly(b[2], b[3], t[3], t[2])} fill={side} fillOpacity="0.82" />
        <polygon points={poly(t[0], t[1], t[2], t[3])} fill={top} />
      </g>
    )
  }

  return (
    <div className="relative overflow-hidden rounded-2xl bg-panel shadow-sm">
      <svg
        ref={svgRef}
        viewBox={`${VB.x} ${VB.y} ${VB.w} ${VB.h}`}
        className="block w-full cursor-grab touch-none active:cursor-grabbing"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerUp}
        onWheel={onWheel}
        onContextMenu={(e) => e.preventDefault()}
        onClick={() => onSelect(null)}
      >
        <g transform={`translate(${cam.px} ${cam.py}) scale(${cam.zoom})`}>
          {FLOORS.map((f) => {
            const zBase = f.id * STOREY_HEIGHT
            const dim = activeFloor === f.id ? 1 : 0.26
            const grp = mapItems.filter((m) => m.kind !== 'door')
            const geo = [...grp].sort(
              (a, b) => iso(a.x + a.w / 2, a.y + a.h / 2).depth - iso(b.x + b.w / 2, b.y + b.h / 2).depth
            )
            const slab = [iso(4, 4, zBase), iso(96, 4, zBase), iso(96, 96, zBase), iso(4, 96, zBase)]
            const floorTags = sim.tags.filter((t) => t.floor === f.id && tagVisible(t))
            const floorAnchors = sim.anchors.filter((a) => a.floor === f.id && anchorVisible(a.id))

            return (
              <g key={f.id}>
                <polygon points={poly(...slab)} fill="var(--muted)" fillOpacity={0.5 * dim} stroke="var(--border)" strokeWidth="0.4" opacity={dim} />
                
                {/* 3D Graph Paper Point Grid */}
                {Array.from({ length: Math.floor(80 / (gridSpacing * 1.8)) }).flatMap((_, ix) =>
                  Array.from({ length: Math.floor(80 / (gridSpacing * 1.8)) }).map((_, iy) => {
                    const gx = 10 + ix * (gridSpacing * 1.8)
                    const gy = 10 + iy * (gridSpacing * 1.8)
                    const pt = iso(gx, gy, zBase)
                    return (
                      <circle
                        key={`dot-${ix}-${iy}`}
                        cx={pt.X}
                        cy={pt.Y}
                        r="0.38"
                        fill="var(--muted-foreground)"
                        opacity={0.35 * dim}
                      />
                    )
                  })
                )}

                {/* Storey Name Label Pill */}
                <g transform={`translate(${iso(4, 96, zBase).X - 18}, ${iso(4, 96, zBase).Y + 1})`}>
                  <rect x="0" y="0" width="16" height="4.5" rx="1" fill="var(--card)" fillOpacity="0.9" stroke="var(--border)" strokeWidth="0.2" opacity={dim} />
                  <text x="8" y="3.2" fontSize="2.8" fontWeight="600" textAnchor="middle" fill="var(--foreground)" fontFamily="var(--font-sans)" opacity={dim}>
                    {f.name}
                  </text>
                </g>

                {sim.geofences.map((z) => {
                  const p = [iso(z.x, z.y, zBase), iso(z.x + z.w, z.y, zBase), iso(z.x + z.w, z.y + z.h, zBase), iso(z.x, z.y + z.h, zBase)]
                  return (
                    <polygon key={z.id} points={poly(...p)} fill={z.restricted ? 'var(--status-lost)' : 'var(--accent)'} fillOpacity={(z.restricted ? 0.12 : 0.05) * dim} stroke={z.restricted ? 'var(--status-lost)' : 'var(--border)'} strokeWidth="0.3" strokeDasharray={z.restricted ? '1.2 0.8' : undefined} opacity={dim} />
                  )
                })}

                {mapItems.filter((m) => m.kind === 'door').map((m) => {
                  const p = [iso(m.x, m.y, zBase), iso(m.x + m.w, m.y, zBase), iso(m.x + m.w, m.y + m.h, zBase), iso(m.x, m.y + m.h, zBase)]
                  return <polygon key={m.id} points={poly(...p)} fill="none" stroke="var(--accent)" strokeWidth="0.3" strokeDasharray="0.8 0.6" opacity={dim} />
                })}

                {geo.map((m) =>
                  m.kind === 'wall'
                    ? prism(m, zBase, 8, 'var(--muted)', 'var(--muted-foreground)', 'var(--foreground)', dim)
                    : prism(m, zBase, 4, 'var(--card)', 'var(--muted)', 'var(--muted-foreground)', dim)
                )}

                {floorAnchors.map((a) => {
                  const top = iso(a.x, a.y, zBase + a.z)
                  const foot = iso(a.x, a.y, zBase)
                  const hl = focusAnchor?.id === a.id
                  return (
                    <g key={a.id} opacity={dim}>
                      <line x1={top.X} y1={top.Y} x2={foot.X} y2={foot.Y} stroke="var(--muted-foreground)" strokeWidth="0.15" strokeDasharray="0.6 0.6" opacity="0.6" />
                      <rect x={top.X - 1.2} y={top.Y - 1.2} width="2.4" height="2.4" rx="0.5" fill={hl ? 'var(--accent)' : 'var(--card)'} stroke="var(--foreground)" strokeWidth="0.3" />
                      {activeFloor === f.id && (
                        <g transform={`translate(${top.X + 1.8}, ${top.Y - 2.5})`}>
                          <rect x="0" y="0" width={a.id.length * 1.5 + 1} height="2.8" rx="0.6" fill="var(--card)" fillOpacity="0.9" stroke="var(--border)" strokeWidth="0.2" />
                          <text x="0.8" y="2.0" fontSize="2.0" fontWeight="600" fill="var(--foreground)" fontFamily="var(--font-mono)">
                            {a.id}
                          </text>
                        </g>
                      )}
                    </g>
                  )
                })}

                {activeTag && activeTag.floor === f.id &&
                  activeTag.readings.filter((r) => r.used).map((r) => {
                    const a = sim.anchors.find((an) => an.id === r.anchorId)
                    if (!a) return null
                    const p1 = iso(a.x, a.y, zBase + a.z)
                    const p2 = iso(activeTag.x, activeTag.y, zBase)
                    return <line key={r.anchorId} x1={p1.X} y1={p1.Y} x2={p2.X} y2={p2.Y} stroke="var(--accent)" strokeWidth="0.3" strokeDasharray="1 0.8" opacity="0.85" />
                  })}

                {floorTags.map((t) => {
                  const p = iso(t.x, t.y, zBase)
                  const isActive = active === t.id || focus === t.id
                  const color = t.violating ? 'var(--status-lost)' : STATUS_META[t.status].color
                  const rx = t.uncertainty * 3.2
                  return (
                    <g key={t.id} opacity={dim} onMouseEnter={() => setHover(t.id)} onMouseLeave={() => setHover(null)} onClick={(e) => { e.stopPropagation(); onSelect(selected === t.id ? null : t.id) }} className="cursor-pointer">
                      <ellipse cx={p.X} cy={p.Y} rx={rx} ry={rx * cam.pitch} fill={color} fillOpacity={isActive ? 0.14 : 0.06} stroke={color} strokeWidth="0.15" strokeOpacity={isActive ? 0.5 : 0.25} />
                      {(t.status === 'online' || t.violating) && (
                        <circle cx={p.X} cy={p.Y} r="1.6" fill={color} opacity="0.5">
                          <animate attributeName="r" from="1.2" to="4" dur={t.violating ? '1.2s' : '2s'} repeatCount="indefinite" />
                          <animate attributeName="opacity" from="0.5" to="0" dur={t.violating ? '1.2s' : '2s'} repeatCount="indefinite" />
                        </circle>
                      )}
                      <circle cx={p.X} cy={p.Y} r={isActive ? 2.2 : 1.6} fill={color} stroke="var(--card)" strokeWidth="0.4" />
                      
                      {/* High contrast 3D Tag label pill */}
                      <g transform={`translate(${p.X}, ${p.Y - 3.8})`}>
                        <rect x={-(t.label.length * 1.0 + 1)} y="-2.2" width={t.label.length * 2.0 + 2} height="3.2" rx="0.8" fill="var(--card)" fillOpacity="0.95" stroke={color} strokeWidth="0.3" />
                        <text x="0" y="0" fontSize="2.2" textAnchor="middle" fill="var(--foreground)" fontFamily="var(--font-sans)" fontWeight="700">
                          {t.label}
                        </text>
                      </g>
                    </g>
                  )
                })}
              </g>
            )
          })}
        </g>
      </svg>

      {/* Floating 3D Controls HUD for Mobile */}
      <div className="absolute right-2 top-2 flex flex-col gap-1.5 z-20">
        <button
          onClick={handleZoomIn}
          title="Zoom In"
          className="grid size-8 place-items-center rounded-xl bg-card/95 font-bold text-foreground shadow-md backdrop-blur hover:bg-muted focus-visible:outline-2 focus-visible:outline-accent active:scale-95 transition-all cursor-pointer"
        >
          +
        </button>
        <button
          onClick={handleZoomOut}
          title="Zoom Out"
          className="grid size-8 place-items-center rounded-xl bg-card/95 font-bold text-foreground shadow-md backdrop-blur hover:bg-muted focus-visible:outline-2 focus-visible:outline-accent active:scale-95 transition-all cursor-pointer"
        >
          −
        </button>
        <button
          onClick={() => setCam(DEFAULT_CAM)}
          title="Reset Orbit View"
          className="grid size-8 place-items-center rounded-xl bg-card/95 text-xs font-bold text-accent shadow-md backdrop-blur hover:bg-muted focus-visible:outline-2 focus-visible:outline-accent active:scale-95 transition-all cursor-pointer"
        >
          ⟲
        </button>
      </div>

      {activeTag && (
        <div className="pointer-events-none absolute bottom-3 left-3 rounded-2xl bg-card/95 p-3.5 font-mono text-[11px] shadow-lg backdrop-blur max-w-[calc(100%-1.5rem)] space-y-1">
          <div className="font-bold text-foreground flex items-center gap-1.5">
            <span className="size-2 rounded-full" style={{ background: STATUS_META[activeTag.status].color }} />
            TAG-{activeTag.id} · {activeTag.label}
          </div>
          <div className="text-muted-foreground text-[10px]">x {activeTag.x.toFixed(1)} · y {activeTag.y.toFixed(1)} · fl {activeTag.floor + 1}</div>
          <div className="text-muted-foreground text-[10px]">σ {activeTag.uncertainty} m · {activeTag.zone}</div>
          {activeTag.violating && <div className="text-rose-600 font-bold text-[10px]">⚠ Geofence breach</div>}
        </div>
      )}

      <div className="pointer-events-none absolute left-3 top-3 hidden sm:block rounded-xl bg-card/85 px-3 py-1 font-mono text-[10px] text-muted-foreground backdrop-blur shadow-xs">
        drag orbit · scroll zoom · shift-drag pan
      </div>
    </div>
  )
}
