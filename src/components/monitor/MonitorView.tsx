import { useState } from 'react'
import type { MapItem, SimState } from '../../lib/simulation'
import { canAccess, type UserRole } from '../../lib/rbac'
import { SpatialView } from './SpatialView'
import { TagDetail } from './TagDetail'
import { RoomDesignWizard } from '../admin/RoomDesignWizard'

interface Props {
  sim: SimState
  mapItems: MapItem[]
  selected: string | null
  onSelect: (id: string | null) => void
  focus: string | null
  onFocus: (id: string | null) => void
  role?: UserRole
}

export function MonitorView({ sim, mapItems, selected, onSelect, focus, onFocus, role = 'admin' }: Props) {
  const [showWizard, setShowWizard] = useState(false)
  const selectedTag = sim.tags.find((t) => t.id === selected) ?? null
  const isAdmin = canAccess(role, 'admin')
  const isUnoptimized = sim.anchors.length < 3

  return (
    <div className="space-y-4">
      {/* Optimization Health Check Banner */}
      {isUnoptimized && (
        <div className="rounded-xl bg-amber-500/10 p-5 shadow-xs border border-amber-500/20">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <span className="text-2xl p-1.5 bg-amber-500/20 rounded-lg">⚠️</span>
              <div>
                <h3 className="text-sm font-semibold text-amber-200">
                  {isAdmin ? 'Room Setup & Node Placement Required' : 'Live Positioning View Not Available'}
                </h3>
                <p className="text-xs text-amber-300/80 mt-1 max-w-2xl">
                  {isAdmin
                    ? 'The positioning solver requires at least 3 configured BLE anchor nodes and 3D room dimensions to achieve sub-meter trilateration accuracy.'
                    : 'The live positioning view is currently uncalibrated or undergoing room design optimization. Please contact your System Administrator to complete room setup.'}
                </p>
              </div>
            </div>

            {isAdmin ? (
              <button
                onClick={() => setShowWizard(true)}
                className="rounded-lg bg-amber-500 hover:bg-amber-400 text-amber-950 px-4 py-2 text-xs font-bold transition-all shadow-sm flex items-center gap-1.5"
              >
                🛠️ Launch Room Setup Wizard
              </button>
            ) : (
              <span className="rounded-full bg-amber-500/20 px-3 py-1 text-xs font-semibold text-amber-300">
                Contact Sysadmin
              </span>
            )}
          </div>
        </div>
      )}

      {/* Admin Quick Launcher Bar */}
      {isAdmin && !isUnoptimized && (
        <div className="flex justify-end">
          <button
            onClick={() => setShowWizard(true)}
            className="rounded-lg bg-card hover:bg-panel px-3 py-1.5 text-xs font-semibold text-foreground transition-all shadow-xs flex items-center gap-1.5"
          >
            🛠️ 3D Room Designer & Node Setup
          </button>
        </div>
      )}

      {/* Hero Spatial View & Detail Panel */}
      <div className={`grid grid-cols-1 gap-6 ${selectedTag ? 'xl:grid-cols-[1fr_360px]' : ''}`}>
        <SpatialView sim={sim} mapItems={mapItems} selected={selected} onSelect={onSelect} focus={focus} onFocus={onFocus} />
        {selectedTag && (
          <div className="space-y-6">
            <TagDetail tag={selectedTag} anchors={sim.anchors} />
          </div>
        )}
      </div>

      {/* Room Setup Wizard Modal */}
      {showWizard && (
        <RoomDesignWizard
          onClose={() => setShowWizard(false)}
          onSaved={() => setShowWizard(false)}
        />
      )}
    </div>
  )
}
