import type { MapItem, SimState } from '../../lib/simulation'
import { SpatialView } from './SpatialView'
import { TagDetail } from './TagDetail'

interface Props {
  sim: SimState
  mapItems: MapItem[]
  selected: string | null
  onSelect: (id: string | null) => void
  focus: string | null
  onFocus: (id: string | null) => void
}

export function MonitorView({ sim, mapItems, selected, onSelect, focus, onFocus }: Props) {
  const selectedTag = sim.tags.find((t) => t.id === selected) ?? null

  // Floor-first: the spatial view is the hero. A detail panel only appears when
  // the end user actually picks something on the floor (or via search).
  return (
    <div className={`grid grid-cols-1 gap-6 ${selectedTag ? 'xl:grid-cols-[1fr_360px]' : ''}`}>
      <SpatialView sim={sim} mapItems={mapItems} selected={selected} onSelect={onSelect} focus={focus} onFocus={onFocus} />
      {selectedTag && (
        <div className="space-y-6">
          <TagDetail tag={selectedTag} anchors={sim.anchors} />
        </div>
      )}
    </div>
  )
}
