import { useState } from 'react'
import { FLOORS, type MapItem, type SimState } from '../../lib/simulation'
import { STATUS_META } from '../../lib/format'
import { FloorPlan } from './FloorPlan'
import { BuildingView3D } from './BuildingView3D'

interface Props {
  sim: SimState
  mapItems: MapItem[]
  selected: string | null
  onSelect: (id: string | null) => void
  focus: string | null
  onFocus: (id: string | null) => void
}

type Dim = '2d' | '3d'

export function SpatialView({ sim, mapItems, selected, onSelect, focus, onFocus }: Props) {
  const [dim, setDim] = useState<Dim>('2d')
  const [floor, setFloor] = useState(0)
  const focusedTag = sim.tags.find((t) => t.id === focus)

  // keep the active floor in sync with whatever the operator focuses via search
  const focusTag = sim.tags.find((t) => t.id === focus)
  const focusAnchor = sim.anchors.find((a) => a.id === focus)
  const focusFloor = focusTag?.floor ?? focusAnchor?.floor
  const activeFloor = focusFloor ?? floor
  const floorName = FLOORS.find((f) => f.id === activeFloor)?.name ?? 'Ground'

  return (
    <div className="rounded-[var(--radius)] border border-border/40 bg-card p-4 sm:p-5 shadow-xs">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">Facility 1 · {floorName}</h2>
          <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">
            {focus
              ? `Isolated: ${focus} — obstacle-aware NLOS solve`
              : dim === '3d'
              ? `${FLOORS.length} storeys · drag to orbit · scroll to zoom · shift-drag to pan`
              : `${mapItems.filter((m) => m.kind !== 'door').length} obstacles mapped · ${sim.anchors.filter((a) => a.floor === activeFloor).length} anchors on floor · σ shown`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Legend />
          {/* floor picker */}
          <div className="flex gap-0.5 rounded-lg border border-border bg-panel p-0.5">
            {FLOORS.map((f) => (
              <button
                key={f.id}
                onClick={() => setFloor(f.id)}
                disabled={focusFloor !== undefined}
                className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-40 ${
                  activeFloor === f.id ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {f.name}
              </button>
            ))}
          </div>
          <div className="flex gap-0.5 rounded-lg border border-border bg-panel p-0.5">
            {(['2d', '3d'] as const).map((d) => (
              <button
                key={d}
                onClick={() => setDim(d)}
                className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                  dim === d ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {d === '2d' ? '2D Plan' : '3D View'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {dim === '2d' ? (
        <FloorPlan sim={sim} mapItems={mapItems} floor={activeFloor} selected={selected} onSelect={onSelect} focus={focus} onFocus={onFocus} />
      ) : (
        <BuildingView3D sim={sim} mapItems={mapItems} activeFloor={activeFloor} selected={selected} onSelect={onSelect} focus={focus} />
      )}

      {focusedTag && (
        <p className="mt-3 text-xs text-muted-foreground">
          Showing <span className="font-medium text-foreground">{focusedTag.label}</span> and its solving anchors only. Clear the
          search pill to show all nodes.
        </p>
      )}
    </div>
  )
}

function Legend() {
  return (
    <div className="hidden items-center gap-3 font-mono text-[10px] text-muted-foreground xl:flex">
      {(['online', 'stale', 'lost'] as const).map((s) => (
        <span key={s} className="flex items-center gap-1.5">
          <span className="size-2 rounded-full" style={{ background: STATUS_META[s].color }} />
          {STATUS_META[s].label}
        </span>
      ))}
      <span className="flex items-center gap-1.5">
        <span className="size-2 rounded-[2px] bg-foreground/70" />
        Wall
      </span>
      <span className="flex items-center gap-1.5">
        <span className="size-2 rounded-[2px] border border-muted-foreground bg-muted" />
        Furniture
      </span>
    </div>
  )
}
