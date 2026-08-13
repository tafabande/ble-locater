import { useRef, useState } from 'react'
import { DEFAULT_MAP, GEOFENCES, type MapItem, type MapItemKind } from '../../lib/simulation'

interface Props {
  mapItems: MapItem[]
  onMapItems: (items: MapItem[]) => void
}

const KIND_META: Record<MapItemKind, { label: string; att: number; w: number; h: number }> = {
  wall: { label: 'Wall', att: 8, w: 20, h: 1.6 },
  furniture: { label: 'Furniture', att: 4, w: 12, h: 6 },
  door: { label: 'Door', att: 0, w: 1.6, h: 7 },
}

let seq = 0
const newId = (k: string) => `${k}-u${seq++}`

export function FloorEditor({ mapItems, onMapItems }: Props) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [sel, setSel] = useState<string | null>(null)
  const drag = useRef<{ id: string; dx: number; dy: number } | null>(null)

  const selected = mapItems.find((m) => m.id === sel) ?? null

  // client → floor-percent coords
  const toPct = (clientX: number, clientY: number) => {
    const r = svgRef.current!.getBoundingClientRect()
    return { x: ((clientX - r.left) / r.width) * 100, y: ((clientY - r.top) / r.height) * 100 }
  }

  const onPointerDown = (e: React.PointerEvent, m: MapItem) => {
    e.stopPropagation()
    setSel(m.id)
    const p = toPct(e.clientX, e.clientY)
    drag.current = { id: m.id, dx: p.x - m.x, dy: p.y - m.y }
    ;(e.target as Element).setPointerCapture?.(e.pointerId)
  }
  const onPointerMove = (e: React.PointerEvent) => {
    if (!drag.current) return
    const p = toPct(e.clientX, e.clientY)
    onMapItems(
      mapItems.map((m) => {
        if (m.id !== drag.current!.id) return m
        const x = Math.max(0, Math.min(100 - m.w, p.x - drag.current!.dx))
        const y = Math.max(0, Math.min(100 - m.h, p.y - drag.current!.dy))
        return { ...m, x: Math.round(x * 2) / 2, y: Math.round(y * 2) / 2 }
      })
    )
  }
  const onPointerUp = () => (drag.current = null)

  const addItem = (kind: MapItemKind) => {
    const meta = KIND_META[kind]
    const item: MapItem = { id: newId(kind), kind, label: meta.label, x: 40, y: 46, w: meta.w, h: meta.h, attenuation: meta.att }
    onMapItems([...mapItems, item])
    setSel(item.id)
  }
  const patch = (p: Partial<MapItem>) => selected && onMapItems(mapItems.map((m) => (m.id === selected.id ? { ...m, ...p } : m)))
  const remove = () => { if (selected) { onMapItems(mapItems.filter((m) => m.id !== selected.id)); setSel(null) } }
  const reset = () => { onMapItems(DEFAULT_MAP); setSel(null) }

  const fill = (m: MapItem) =>
    m.kind === 'wall' ? 'var(--foreground)' : m.kind === 'door' ? 'transparent' : 'var(--muted)'

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_300px]">
      <div className="rounded-[var(--radius)] border border-border bg-card p-4 sm:p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold">Floor Editor</h3>
            <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">Drag to move · click to select · changes apply live to the map</p>
          </div>
          <div className="flex gap-1">
            {(['wall', 'furniture', 'door'] as const).map((k) => (
              <button key={k} onClick={() => addItem(k)} className="rounded-md border border-border px-2.5 py-1 text-xs font-medium transition-colors hover:bg-muted">
                + {KIND_META[k].label}
              </button>
            ))}
            <button onClick={reset} className="rounded-md border border-border px-2.5 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted">
              Reset
            </button>
          </div>
        </div>

        <div className="overflow-hidden rounded-md border border-border bg-panel">
          <svg
            ref={svgRef}
            viewBox="0 0 100 100"
            className="block w-full touch-none"
            onClick={() => setSel(null)}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerLeave={onPointerUp}
          >
            <defs>
              <pattern id="egrid" width="4" height="4" patternUnits="userSpaceOnUse">
                <path d="M4 0H0V4" fill="none" stroke="var(--border)" strokeWidth="0.12" />
              </pattern>
            </defs>
            <rect x="0" y="0" width="100" height="100" fill="url(#egrid)" />

            {/* room reference outlines */}
            {GEOFENCES.map((z) => (
              <g key={z.id}>
                <rect x={z.x} y={z.y} width={z.w} height={z.h} rx="1" fill="var(--muted)" fillOpacity="0.3" stroke="var(--border)" strokeWidth="0.2" strokeDasharray={z.restricted ? '1 0.8' : undefined} />
                <text x={z.x + 1.4} y={z.y + 3} fontSize="1.8" fill="var(--muted-foreground)" fontFamily="var(--font-mono)">{z.name}</text>
              </g>
            ))}

            {/* editable items */}
            {mapItems.map((m) => {
              const isSel = sel === m.id
              return (
                <g key={m.id} onPointerDown={(e) => onPointerDown(e, m)} className="cursor-move">
                  <rect
                    x={m.x}
                    y={m.y}
                    width={m.w}
                    height={m.h}
                    rx="0.3"
                    fill={fill(m)}
                    fillOpacity={m.kind === 'wall' ? 0.72 : m.kind === 'door' ? 0 : 0.55}
                    stroke={isSel ? 'var(--accent)' : m.kind === 'door' ? 'var(--accent)' : 'var(--muted-foreground)'}
                    strokeWidth={isSel ? 0.6 : 0.25}
                    strokeDasharray={m.kind === 'door' ? '0.6 0.5' : undefined}
                  />
                  {m.w > 7 && (
                    <text x={m.x + m.w / 2} y={m.y + m.h / 2 + 0.6} fontSize="1.5" textAnchor="middle" fill="var(--muted-foreground)" fontFamily="var(--font-mono)" pointerEvents="none">
                      {m.label}
                    </text>
                  )}
                </g>
              )
            })}
          </svg>
        </div>
      </div>

      {/* inspector */}
      <div className="rounded-[var(--radius)] border border-border bg-card p-4">
        {selected ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">{selected.label}</h3>
              <span className="rounded-full bg-muted px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{selected.kind}</span>
            </div>

            <FieldRow label="Label">
              <input value={selected.label} onChange={(e) => patch({ label: e.target.value })} className="w-full rounded-md border border-border bg-panel px-2.5 py-1.5 text-xs outline-none focus:ring-2 focus:ring-ring" />
            </FieldRow>

            <div className="grid grid-cols-2 gap-2">
              <NumRow label="X" value={selected.x} onChange={(v) => patch({ x: v })} />
              <NumRow label="Y" value={selected.y} onChange={(v) => patch({ y: v })} />
              <NumRow label="Width" value={selected.w} onChange={(v) => patch({ w: Math.max(1, v) })} />
              <NumRow label="Height" value={selected.h} onChange={(v) => patch({ h: Math.max(1, v) })} />
            </div>

            <FieldRow label="RF attenuation (dB)" hint="Signal loss when line-of-sight crosses this item">
              <input type="range" min={0} max={14} step={0.5} value={selected.attenuation} onChange={(e) => patch({ attenuation: Number(e.target.value) })} className="w-full accent-[var(--accent)]" />
              <div className="mt-1 font-mono text-xs tabular-nums text-muted-foreground">{selected.attenuation.toFixed(1)} dB</div>
            </FieldRow>

            <button onClick={remove} className="w-full rounded-md border border-border py-2 text-xs font-medium transition-colors hover:bg-muted" style={{ color: 'var(--status-lost)' }}>
              Delete item
            </button>
          </div>
        ) : (
          <div className="py-8 text-center">
            <p className="text-sm font-medium">Nothing selected</p>
            <p className="mx-auto mt-1 max-w-[200px] text-xs text-muted-foreground">Add an element or click one on the plan to edit its geometry and RF attenuation.</p>
            <dl className="mt-4 space-y-1.5 text-left font-mono text-[11px]">
              <Stat k="Walls" v={mapItems.filter((m) => m.kind === 'wall').length} />
              <Stat k="Furniture" v={mapItems.filter((m) => m.kind === 'furniture').length} />
              <Stat k="Openings" v={mapItems.filter((m) => m.kind === 'door').length} />
            </dl>
          </div>
        )}
      </div>
    </div>
  )
}

function FieldRow({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-xs font-medium">{label}</label>
      {hint && <p className="mb-1.5 text-[11px] text-muted-foreground">{hint}</p>}
      {!hint && <div className="mb-1" />}
      {children}
    </div>
  )
}

function NumRow({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <label className="block">
      <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{label}</span>
      <input
        type="number"
        step={0.5}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-1 w-full rounded-md border border-border bg-panel px-2.5 py-1.5 font-mono text-xs tabular-nums outline-none focus:ring-2 focus:ring-ring"
      />
    </label>
  )
}

function Stat({ k, v }: { k: string; v: number }) {
  return (
    <div className="flex justify-between border-b border-border pb-1.5 last:border-0">
      <dt className="text-muted-foreground">{k}</dt>
      <dd className="tabular-nums text-foreground">{v}</dd>
    </div>
  )
}
