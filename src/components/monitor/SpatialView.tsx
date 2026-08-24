import { useState } from 'react'
import { FLOORS, type MapItem, type SimState } from '../../lib/simulation'
import { STATUS_META } from '../../lib/format'
import { FloorPlan } from './FloorPlan'
import { BuildingView3D } from './BuildingView3D'
import { M3Layers, M3Grid } from '../common/MaterialIcon'

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
  const [gridSpacing, setGridSpacing] = useState<number>(4)

  const focusedTag = sim.tags.find((t) => t.id === focus)

  // keep the active floor in sync with whatever the operator focuses via search
  const focusTag = sim.tags.find((t) => t.id === focus)
  const focusAnchor = sim.anchors.find((a) => a.id === focus)
  const focusFloor = focusTag?.floor ?? focusAnchor?.floor
  const activeFloor = focusFloor ?? floor
  const floorName = FLOORS.find((f) => f.id === activeFloor)?.name ?? 'Ground'

  return (
    <div className="rounded-xl border border-border/40 bg-card p-4 sm:p-5 shadow-xs space-y-4">
      {/* Mobile-First Header Toolbar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-foreground">Facility 1 · {floorName}</h2>
            <span className="rounded-full bg-accent-soft px-2 py-0.5 font-mono text-[10px] font-bold text-accent">
              {dim.toUpperCase()} Mode
            </span>
          </div>
          <p className="mt-0.5 font-mono text-[11px] text-muted-foreground truncate">
            {focus
              ? `Isolated: ${focus} — obstacle-aware NLOS solve`
              : dim === '3d'
              ? `${FLOORS.length} storeys · touch & drag to orbit`
              : `${mapItems.filter((m) => m.kind !== 'door').length} obstacles · ${sim.anchors.filter((a) => a.floor === activeFloor).length} anchors on floor`}
          </p>
        </div>

        {/* Toolbar Controls */}
        <div className="flex flex-wrap items-center gap-2">
          <Legend />

          {/* Graph Paper Dot Grid Spacing Control */}
          <div className="flex items-center gap-0.5 rounded-lg border border-border/40 bg-panel p-0.5 shrink-0">
            <span className="px-2 font-mono text-[10px] font-bold text-muted-foreground">DOT GRID</span>
            {[2, 4, 8, 12].map((spacing) => (
              <button
                key={spacing}
                onClick={() => setGridSpacing(spacing)}
                className={`rounded-md px-2 py-0.5 font-mono text-[10px] font-bold transition-colors ${
                  gridSpacing === spacing ? 'bg-accent text-primary-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {spacing}m
              </button>
            ))}
          </div>

          {/* Scrollable Mobile Floor Picker */}
          <div className="flex items-center gap-0.5 rounded-lg border border-border/40 bg-panel p-0.5 max-w-full overflow-x-auto">
            {FLOORS.map((f) => (
              <button
                key={f.id}
                onClick={() => setFloor(f.id)}
                disabled={focusFloor !== undefined}
                className={`rounded-md px-2.5 py-1 text-xs font-semibold transition-colors shrink-0 whitespace-nowrap disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-accent ${
                  activeFloor === f.id ? 'bg-card text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {f.name}
              </button>
            ))}
          </div>

          {/* 2D / 3D Mode Toggle */}
          <div className="flex items-center gap-0.5 rounded-lg border border-border/40 bg-panel p-0.5 shrink-0">
            {(['2d', '3d'] as const).map((d) => (
              <button
                key={d}
                onClick={() => setDim(d)}
                className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-semibold transition-colors whitespace-nowrap focus-visible:outline-2 focus-visible:outline-accent ${
                  dim === d ? 'bg-accent text-primary-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {d === '2d' ? <M3Grid size={13} /> : <M3Layers size={13} />}
                {d === '2d' ? '2D Plan' : '3D Orbit'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {dim === '2d' ? (
        <FloorPlan sim={sim} mapItems={mapItems} floor={activeFloor} selected={selected} onSelect={onSelect} focus={focus} onFocus={onFocus} gridSpacing={gridSpacing} />
      ) : (
        <BuildingView3D sim={sim} mapItems={mapItems} activeFloor={activeFloor} selected={selected} onSelect={onSelect} focus={focus} gridSpacing={gridSpacing} />
      )}

      {focusedTag && (
        <p className="text-xs text-muted-foreground">
          Showing <span className="font-medium text-foreground">{focusedTag.label}</span> and its solving anchors only. Clear the
          search pill to show all nodes.
        </p>
      )}
    </div>
  )
}

function Legend() {
  return (
    <div className="hidden items-center gap-3 font-mono text-[10px] text-muted-foreground lg:flex">
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
