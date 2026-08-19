import { useEffect, useState, useRef } from 'react'

interface AnchorNode {
  id: string
  label: string
  x: number
  y: number
  z?: number
  txPower?: number
  channel?: number
  host?: boolean
}

interface TagItem {
  id: string
  label: string
  x: number
  y: number
  z?: number
}

interface FurnitureItem {
  id: string
  type: string
  label: string
  x: number
  y: number
  w: number
  h: number
  rotation?: number
  icon?: string
  color?: string
}

interface RoomDimensions {
  width: number
  height: number
  depth: number
  unit: string
}

interface Props {
  onClose: () => void
  onSaved?: () => void
}

type DomainCategory = 'warehouse' | 'office' | 'campus' | 'storeroom' | 'healthcare' | 'custom'

const DOMAIN_PALETTES: Record<DomainCategory, { label: string; icon: string; items: Array<{ type: string; label: string; w: number; h: number; icon: string; bg: string }> }> = {
  warehouse: {
    label: 'Warehouse & Logistics',
    icon: '📦',
    items: [
      { type: 'pallet_rack', label: 'High Pallet Rack', w: 3.0, h: 1.2, icon: '🏗️', bg: '#0284c7' },
      { type: 'forklift_bay', label: 'Forklift Dock', w: 2.2, h: 1.5, icon: '🚜', bg: '#d97706' },
      { type: 'loading_bay', label: 'Loading Dock', w: 3.5, h: 2.0, icon: '🚚', bg: '#059669' },
      { type: 'conveyor', label: 'Staging Conveyor', w: 4.0, h: 1.0, icon: '📦', bg: '#7c3aed' },
      { type: 'sorting_table', label: 'Sorting Station', w: 2.5, h: 1.2, icon: '🏷️', bg: '#db2777' }
    ]
  },
  office: {
    label: 'Corporate Office',
    icon: '🏢',
    items: [
      { type: 'workstation', label: 'Desk Workstation', w: 2.5, h: 2.0, icon: '🖥️', bg: '#2563eb' },
      { type: 'executive_desk', label: 'Executive Suite', w: 2.0, h: 1.2, icon: '💼', bg: '#4f46e5' },
      { type: 'conference_table', label: 'Boardroom Table', w: 3.5, h: 1.5, icon: '📊', bg: '#0d9488' },
      { type: 'credenza', label: 'Storage Credenza', w: 2.0, h: 0.8, icon: '🗄️', bg: '#d97706' },
      { type: 'divider', label: 'Partition Screen', w: 3.0, h: 0.2, icon: '🧱', bg: '#64748b' }
    ]
  },
  campus: {
    label: 'Campus & University',
    icon: '🏫',
    items: [
      { type: 'student_pod', label: 'Student Pod Desk', w: 2.0, h: 1.5, icon: '🎓', bg: '#2563eb' },
      { type: 'server_rack', label: 'IT Server Rack', w: 1.0, h: 1.2, icon: '🗄️', bg: '#dc2626' },
      { type: 'lab_bench', label: 'Lab Workbench', w: 3.0, h: 1.2, icon: '🔬', bg: '#059669' },
      { type: 'podium', label: 'Lectern Podium', w: 1.0, h: 0.8, icon: '🎙️', bg: '#d97706' },
      { type: 'bookshelf', label: 'Library Shelf', w: 3.5, h: 0.8, icon: '📚', bg: '#9333ea' }
    ]
  },
  storeroom: {
    label: 'Storeroom & Retail',
    icon: '🏬',
    items: [
      { type: 'storage_shelf', label: 'Storage Shelving', w: 2.0, h: 0.8, icon: '📦', bg: '#0284c7' },
      { type: 'checkout', label: 'Checkout Counter', w: 2.5, h: 1.0, icon: '💳', bg: '#059669' },
      { type: 'display_island', label: 'Display Isle', w: 3.0, h: 1.5, icon: '🛍️', bg: '#db2777' },
      { type: 'pallet_jack', label: 'Pallet Jack Bay', w: 1.5, h: 0.8, icon: '🛒', bg: '#ea580c' }
    ]
  },
  healthcare: {
    label: 'Healthcare & Clinic',
    icon: '🏥',
    items: [
      { type: 'icu_bed', label: 'ICU Bed', w: 2.0, h: 1.2, icon: '🛏️', bg: '#2563eb' },
      { type: 'patient_bed', label: 'Patient Bed', w: 2.0, h: 1.2, icon: '🛌', bg: '#059669' },
      { type: 'crash_cart', label: 'Crash Cart', w: 1.0, h: 0.8, icon: '🛒', bg: '#dc2626' },
      { type: 'nurses_desk', label: 'Nurses Station', w: 2.5, h: 1.2, icon: '🏥', bg: '#7c3aed' }
    ]
  },
  custom: {
    label: 'Custom Objects',
    icon: '🛠️',
    items: [
      { type: 'custom_rect', label: 'Custom Rect Object', w: 2.0, h: 1.0, icon: '📦', bg: '#475569' },
      { type: 'custom_wall', label: 'Custom Partition', w: 2.5, h: 0.2, icon: '🧱', bg: '#64748b' }
    ]
  }
}

export function RoomDesignWizard({ onClose, onSaved }: Props) {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1)
  const [facilityDomain, setFacilityDomain] = useState<DomainCategory>('warehouse')
  const [roomName, setRoomName] = useState('Multi-Zone Facility Workspace')
  const [dims, setDims] = useState<RoomDimensions>({ width: 12.0, height: 10.0, depth: 3.5, unit: 'meters' })
  const [furniture, setFurniture] = useState<FurnitureItem[]>([])
  const [anchors, setAnchors] = useState<AnchorNode[]>([])
  const [tags, setTags] = useState<TagItem[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedType, setSelectedType] = useState<'furniture' | 'anchor' | 'tag' | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [view3D, setView3D] = useState(false)

  // Custom Object Inputs
  const [customName, setCustomName] = useState('Custom Storage Rack')
  const [customW, setCustomW] = useState(2.0)
  const [customH, setCustomH] = useState(1.0)
  const [customIcon, setCustomIcon] = useState('📦')

  const canvasRef = useRef<HTMLDivElement>(null)
  const [dragItem, setDragItem] = useState<{ id: string; type: 'furniture' | 'anchor' | 'tag'; startX: number; startY: number; origX: number; origY: number } | null>(null)

  // Fetch initial schematic from API
  useEffect(() => {
    fetch('/api/schematic')
      .then((res) => res.json())
      .then((data) => {
        if (data.name) setRoomName(data.name)
        if (data.facility_type && DOMAIN_PALETTES[data.facility_type as DomainCategory]) {
          setFacilityDomain(data.facility_type as DomainCategory)
        }
        if (data.dimensions) {
          setDims({
            width: data.dimensions.width || 12.0,
            height: data.dimensions.height || 10.0,
            depth: data.dimensions.depth || 3.5,
            unit: data.dimensions.unit || 'meters'
          })
        }
        if (data.furniture) setFurniture(data.furniture)
        if (data.anchors) setAnchors(data.anchors)
        if (data.tags) setTags(data.tags)
      })
      .catch(() => {
        // Fallback default dataset
        setAnchors([
          { id: 'ANCHOR_01', label: 'Anchor 01', x: 0.5, y: 0.5, z: 3.0, host: true },
          { id: 'ANCHOR_02', label: 'Anchor 02', x: 11.5, y: 0.5, z: 3.0 },
          { id: 'ANCHOR_03', label: 'Anchor 03', x: 0.5, y: 9.5, z: 3.0 },
          { id: 'ANCHOR_04', label: 'Anchor 04', x: 11.5, y: 9.5, z: 3.0 }
        ])
        setFurniture([
          { id: 'rack_1', type: 'pallet_rack', label: 'Storage Rack A', x: 2.0, y: 6.5, w: 3.0, h: 1.2, rotation: 0, icon: '🏗️' },
          { id: 'dock_1', type: 'loading_bay', label: 'Loading Dock #1', x: 2.0, y: 1.5, w: 3.5, h: 2.0, rotation: 0, icon: '🚚' }
        ])
      })
  }, [])

  // Drag handlers
  const handlePointerDown = (id: string, type: 'furniture' | 'anchor' | 'tag', e: React.PointerEvent) => {
    e.stopPropagation()
    setSelectedId(id)
    setSelectedType(type)

    let origX = 0
    let origY = 0
    if (type === 'furniture') {
      const item = furniture.find((f) => f.id === id)
      if (item) { origX = item.x; origY = item.y }
    } else if (type === 'anchor') {
      const item = anchors.find((a) => a.id === id)
      if (item) { origX = item.x; origY = item.y }
    } else if (type === 'tag') {
      const item = tags.find((t) => t.id === id)
      if (item) { origX = item.x; origY = item.y }
    }

    setDragItem({ id, type, startX: e.clientX, startY: e.clientY, origX, origY })
  }

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!dragItem || !canvasRef.current) return
    const rect = canvasRef.current.getBoundingClientRect()
    const dx = ((e.clientX - dragItem.startX) / rect.width) * dims.width
    const dy = ((e.clientY - dragItem.startY) / rect.height) * dims.height

    const newX = Math.max(0, Math.min(dims.width, Math.round((dragItem.origX + dx) * 10) / 10))
    const newY = Math.max(0, Math.min(dims.height, Math.round((dragItem.origY + dy) * 10) / 10))

    if (dragItem.type === 'furniture') {
      setFurniture((prev) => prev.map((f) => (f.id === dragItem.id ? { ...f, x: newX, y: newY } : f)))
    } else if (dragItem.type === 'anchor') {
      setAnchors((prev) => prev.map((a) => (a.id === dragItem.id ? { ...a, x: newX, y: newY } : a)))
    } else if (dragItem.type === 'tag') {
      setTags((prev) => prev.map((t) => (t.id === dragItem.id ? { ...t, x: newX, y: newY } : t)))
    }
  }

  const handlePointerUp = () => setDragItem(null)

  // Canvas click to plant elements
  const handleCanvasClick = (e: React.MouseEvent) => {
    if (dragItem || !canvasRef.current) return
    const rect = canvasRef.current.getBoundingClientRect()
    const clickX = Math.round((((e.clientX - rect.left) / rect.width) * dims.width) * 10) / 10
    const clickY = Math.round((((e.clientY - rect.top) / rect.height) * dims.height) * 10) / 10

    if (step === 3) {
      const newId = `ANCHOR_${String(anchors.length + 1).padStart(2, '0')}`
      const newAnchor: AnchorNode = {
        id: newId,
        label: `Anchor ${anchors.length + 1}`,
        x: clickX,
        y: clickY,
        z: dims.depth,
        txPower: -77.8,
        channel: 37,
        host: anchors.length === 0
      }
      setAnchors((prev) => [...prev, newAnchor])
      setSelectedId(newId)
      setSelectedType('anchor')
    } else if (step === 4) {
      const newId = `TAG_${String(tags.length + 1).padStart(2, '0')}`
      const newTag: TagItem = {
        id: newId,
        label: `Moving Asset ${tags.length + 1}`,
        x: clickX,
        y: clickY,
        z: 0.8
      }
      setTags((prev) => [...prev, newTag])
      setSelectedId(newId)
      setSelectedType('tag')
    }
  }

  // Add item from active domain palette
  const addFurniture = (pal: { type: string; label: string; w: number; h: number; icon: string; bg: string }) => {
    const newId = `${pal.type}_${Date.now().toString().slice(-4)}`
    const newItem: FurnitureItem = {
      id: newId,
      type: pal.type,
      label: pal.label,
      x: Math.round((dims.width / 2) * 10) / 10,
      y: Math.round((dims.height / 2) * 10) / 10,
      w: pal.w,
      h: pal.h,
      rotation: 0,
      icon: pal.icon,
      color: pal.bg
    }
    setFurniture((prev) => [...prev, newItem])
    setSelectedId(newId)
    setSelectedType('furniture')
  }

  // Add custom user-defined object
  const addCustomObject = () => {
    const newId = `custom_${Date.now().toString().slice(-4)}`
    const newItem: FurnitureItem = {
      id: newId,
      type: 'custom_object',
      label: customName || 'Custom Item',
      x: Math.round((dims.width / 2) * 10) / 10,
      y: Math.round((dims.height / 2) * 10) / 10,
      w: customW,
      h: customH,
      rotation: 0,
      icon: customIcon || '📦',
      color: '#475569'
    }
    setFurniture((prev) => [...prev, newItem])
    setSelectedId(newId)
    setSelectedType('furniture')
  }

  // Delete selected element
  const deleteSelected = () => {
    if (!selectedId) return
    if (selectedType === 'furniture') setFurniture((prev) => prev.filter((f) => f.id !== selectedId))
    else if (selectedType === 'anchor') setAnchors((prev) => prev.filter((a) => a.id !== selectedId))
    else if (selectedType === 'tag') setTags((prev) => prev.filter((t) => t.id !== selectedId))
    setSelectedId(null)
    setSelectedType(null)
  }

  // Rotate selected furniture item
  const rotateSelected = (deg: number) => {
    if (!selectedId || selectedType !== 'furniture') return
    setFurniture((prev) => prev.map((f) => (f.id === selectedId ? { ...f, rotation: ((f.rotation || 0) + deg) % 360 } : f)))
  }

  // Save layout to API
  const saveSchematic = async () => {
    setIsSaving(true)
    setMessage(null)
    const payload = {
      name: roomName,
      facility_type: facilityDomain,
      dimensions: dims,
      furniture,
      anchors,
      tags,
      rooms: [
        { id: 'room_main', name: roomName, x: 0, y: 0, w: dims.width, h: dims.height, restricted: false }
      ]
    }

    try {
      const res = await fetch('/api/schematic', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setMessage('✅ Room schematic & node layout saved to system API!')
      if (onSaved) onSaved()
      setTimeout(() => onClose(), 1200)
    } catch (e: any) {
      setMessage(`❌ Failed to save schematic: ${e.message}`)
    } finally {
      setIsSaving(false)
    }
  }

  const selectedFurniture = selectedType === 'furniture' ? furniture.find((f) => f.id === selectedId) : null
  const selectedAnchor = selectedType === 'anchor' ? anchors.find((a) => a.id === selectedId) : null
  const selectedTag = selectedType === 'tag' ? tags.find((t) => t.id === selectedId) : null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="relative w-full max-w-5xl rounded-2xl bg-card shadow-2xl overflow-hidden text-foreground flex flex-col max-h-[90vh]">
        {/* Header Bar */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border/40 bg-card">
          <div>
            <h2 className="text-base font-bold text-foreground flex items-center gap-2">
              🛠️ Universal 3D Room & Facility Designer
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Select facility domain (Warehouse, Office, Campus, Storeroom), drag & drop objects, plant BLE nodes, and save API layout.
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-full p-2 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Stepper Bar */}
        <div className="grid grid-cols-4 gap-1 p-2 bg-panel border-b border-border/40 text-xs font-semibold text-center">
          {[
            { id: 1, title: '1. Facility & 3D Dims' },
            { id: 2, title: '2. Drag & Drop Objects' },
            { id: 3, title: '3. Plant BLE Anchors' },
            { id: 4, title: '4. Mobile Asset Tags' }
          ].map((s) => (
            <button
              key={s.id}
              onClick={() => setStep(s.id as any)}
              className={`py-2 rounded-lg transition-all ${
                step === s.id
                  ? 'bg-accent text-primary-foreground shadow-xs font-bold'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
              }`}
            >
              {s.title}
            </button>
          ))}
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 flex-1 overflow-hidden">
          {/* Controls & Palette Sidebar */}
          <div className="lg:col-span-4 p-5 space-y-4 border-r border-border/40 overflow-y-auto bg-card">
            {step === 1 && (
              <div className="space-y-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-accent">Step 1: Facility Type & 3D Dimensions</h3>
                
                {/* Facility Category Selector */}
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Select Facility Domain</label>
                  <div className="grid grid-cols-2 gap-1.5">
                    {(Object.keys(DOMAIN_PALETTES) as DomainCategory[]).map((cat) => (
                      <button
                        key={cat}
                        onClick={() => setFacilityDomain(cat)}
                        className={`flex items-center gap-1.5 p-2 rounded-lg text-xs font-medium transition-all ${
                          facilityDomain === cat
                            ? 'bg-accent text-primary-foreground font-bold shadow-xs'
                            : 'bg-panel text-muted-foreground hover:text-foreground'
                        }`}
                      >
                        <span>{DOMAIN_PALETTES[cat].icon}</span>
                        <span className="truncate">{DOMAIN_PALETTES[cat].label}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-1.5 pt-1">
                  <label className="text-xs font-medium text-muted-foreground">Facility / Room Label</label>
                  <input
                    value={roomName}
                    onChange={(e) => setRoomName(e.target.value)}
                    className="w-full rounded-lg bg-panel px-3 py-2 text-xs border-0 shadow-xs focus:outline-none"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3 pt-1">
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-muted-foreground">Width X ({dims.width}m)</label>
                    <input
                      type="number"
                      step="0.5"
                      min="3"
                      max="50"
                      value={dims.width}
                      onChange={(e) => setDims((d) => ({ ...d, width: parseFloat(e.target.value) || 12 }))}
                      className="w-full rounded-lg bg-panel px-3 py-2 text-xs border-0 shadow-xs focus:outline-none"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-muted-foreground">Length Y ({dims.height}m)</label>
                    <input
                      type="number"
                      step="0.5"
                      min="3"
                      max="50"
                      value={dims.height}
                      onChange={(e) => setDims((d) => ({ ...d, height: parseFloat(e.target.value) || 10 }))}
                      className="w-full rounded-lg bg-panel px-3 py-2 text-xs border-0 shadow-xs focus:outline-none"
                    />
                  </div>
                </div>

                <div className="space-y-1 pt-1">
                  <label className="text-xs font-medium text-muted-foreground">3D Ceiling Height Z ({dims.depth}m)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="2"
                    max="10"
                    value={dims.depth}
                    onChange={(e) => setDims((d) => ({ ...d, depth: parseFloat(e.target.value) || 3.5 }))}
                    className="w-full rounded-lg bg-panel px-3 py-2 text-xs border-0 shadow-xs focus:outline-none"
                  />
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-accent">
                    {DOMAIN_PALETTES[facilityDomain].icon} {DOMAIN_PALETTES[facilityDomain].label} Palette
                  </h3>
                </div>
                <p className="text-xs text-muted-foreground">
                  Click objects below to add them to the floorplan canvas. Drag to position.
                </p>

                {/* Preset Objects List */}
                <div className="grid grid-cols-2 gap-2 pt-1">
                  {DOMAIN_PALETTES[facilityDomain].items.map((pal) => (
                    <button
                      key={pal.type}
                      onClick={() => addFurniture(pal)}
                      className="flex items-center gap-2 rounded-lg bg-panel hover:bg-muted/80 p-2.5 text-xs text-left transition-all shadow-xs"
                    >
                      <span className="text-base">{pal.icon}</span>
                      <div>
                        <div className="font-semibold text-foreground">{pal.label}</div>
                        <div className="text-[10px] text-muted-foreground">{pal.w}m × {pal.h}m</div>
                      </div>
                    </button>
                  ))}
                </div>

                {/* Custom Object Creator Section */}
                <div className="rounded-xl bg-panel p-3.5 space-y-2 border-t border-border/30 text-xs mt-3">
                  <div className="font-bold text-foreground flex items-center gap-1.5">
                    <span>🛠️ Add Custom Object</span>
                  </div>
                  <input
                    value={customName}
                    onChange={(e) => setCustomName(e.target.value)}
                    placeholder="Object label..."
                    className="w-full rounded-md bg-card px-2.5 py-1 text-xs border-0"
                  />
                  <div className="grid grid-cols-3 gap-2">
                    <input
                      type="number"
                      step="0.2"
                      value={customW}
                      onChange={(e) => setCustomW(parseFloat(e.target.value) || 1)}
                      placeholder="W (m)"
                      className="rounded-md bg-card px-2 py-1 text-xs border-0"
                    />
                    <input
                      type="number"
                      step="0.2"
                      value={customH}
                      onChange={(e) => setCustomH(parseFloat(e.target.value) || 1)}
                      placeholder="H (m)"
                      className="rounded-md bg-card px-2 py-1 text-xs border-0"
                    />
                    <input
                      value={customIcon}
                      onChange={(e) => setCustomIcon(e.target.value)}
                      placeholder="Icon"
                      className="rounded-md bg-card px-2 py-1 text-xs border-0 text-center"
                    />
                  </div>
                  <button
                    onClick={addCustomObject}
                    className="w-full rounded-md bg-accent hover:bg-accent/90 text-primary-foreground py-1.5 font-semibold transition-colors shadow-xs"
                  >
                    + Add Custom Item to Room
                  </button>
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-accent">Step 3: Plant Fixed BLE Anchor Nodes</h3>
                <p className="text-xs text-muted-foreground">Click directly on the floorplan canvas to plant fixed receiver nodes (Anchors), or drag existing nodes.</p>
                <div className="rounded-lg bg-panel p-3 text-xs space-y-1.5">
                  <div className="font-semibold text-foreground">Active Planted Nodes: {anchors.length}</div>
                  <div className="text-[11px] text-muted-foreground">Minimum 3 nodes required for 2D/3D trilateration solver.</div>
                </div>
              </div>
            )}

            {step === 4 && (
              <div className="space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-accent">Step 4: Mobile Asset Tags</h3>
                <p className="text-xs text-muted-foreground">Click on the floorplan canvas to plant mobile asset tags or tracking badges.</p>
                <div className="rounded-lg bg-panel p-3 text-xs space-y-1.5">
                  <div className="font-semibold text-foreground">Configured Mobile Tags: {tags.length}</div>
                  <div className="text-[11px] text-muted-foreground">Tags transmit telemetry packets to installed anchors.</div>
                </div>
              </div>
            )}

            {/* Selected Element Inspector */}
            {selectedId && (
              <div className="rounded-xl bg-panel p-3.5 space-y-2.5 text-xs shadow-xs border-t border-border/30">
                <div className="flex items-center justify-between font-bold text-accent">
                  <span>Selected Element Properties</span>
                  <button onClick={deleteSelected} className="text-rose-400 hover:text-rose-300 font-normal text-[11px]">🗑️ Delete</button>
                </div>
                {selectedFurniture && (
                  <div className="space-y-2">
                    <label className="text-[11px] text-muted-foreground">Item Label</label>
                    <input
                      value={selectedFurniture.label}
                      onChange={(e) => {
                        const val = e.target.value
                        setFurniture((prev) => prev.map((f) => (f.id === selectedId ? { ...f, label: val } : f)))
                      }}
                      className="w-full rounded-md bg-card px-2.5 py-1 text-xs border-0"
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-[10px] text-muted-foreground block">Width W ({selectedFurniture.w}m)</label>
                        <input
                          type="number"
                          step="0.2"
                          value={selectedFurniture.w}
                          onChange={(e) => {
                            const val = parseFloat(e.target.value) || 1.0
                            setFurniture((prev) => prev.map((f) => (f.id === selectedId ? { ...f, w: val } : f)))
                          }}
                          className="w-full rounded-md bg-card px-2 py-1 text-xs border-0"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-muted-foreground block">Height H ({selectedFurniture.h}m)</label>
                        <input
                          type="number"
                          step="0.2"
                          value={selectedFurniture.h}
                          onChange={(e) => {
                            const val = parseFloat(e.target.value) || 1.0
                            setFurniture((prev) => prev.map((f) => (f.id === selectedId ? { ...f, h: val } : f)))
                          }}
                          className="w-full rounded-md bg-card px-2 py-1 text-xs border-0"
                        />
                      </div>
                    </div>
                    <div className="flex items-center justify-between pt-1">
                      <span className="text-[11px] text-muted-foreground">Rotation: {selectedFurniture.rotation || 0}°</span>
                      <button
                        onClick={() => rotateSelected(45)}
                        className="rounded-md bg-card hover:bg-muted px-2.5 py-1 text-[11px] font-semibold"
                      >
                        🔄 Rotate +45°
                      </button>
                    </div>
                  </div>
                )}
                {selectedAnchor && (
                  <div className="space-y-2">
                    <label className="text-[11px] text-muted-foreground">Anchor Node ID</label>
                    <input
                      value={selectedAnchor.id}
                      onChange={(e) => {
                        const val = e.target.value
                        setAnchors((prev) => prev.map((a) => (a.id === selectedId ? { ...a, id: val, label: val } : a)))
                      }}
                      className="w-full rounded-md bg-card px-2.5 py-1 text-xs border-0 font-mono"
                    />
                    <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-muted-foreground">
                      <div>X: {selectedAnchor.x}m</div>
                      <div>Y: {selectedAnchor.y}m</div>
                    </div>
                  </div>
                )}
                {selectedTag && (
                  <div className="space-y-2">
                    <label className="text-[11px] text-muted-foreground">Tag Asset ID</label>
                    <input
                      value={selectedTag.id}
                      onChange={(e) => {
                        const val = e.target.value
                        setTags((prev) => prev.map((t) => (t.id === selectedId ? { ...t, id: val, label: val } : t)))
                      }}
                      className="w-full rounded-md bg-card px-2.5 py-1 text-xs border-0 font-mono"
                    />
                    <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-muted-foreground">
                      <div>X: {selectedTag.x}m</div>
                      <div>Y: {selectedTag.y}m</div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Interactive Canvas Container */}
          <div className="lg:col-span-8 p-5 flex flex-col bg-background space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-foreground flex items-center gap-2">
                <span>📍 Interactive Facility Floorplan Grid</span>
                <span className="text-[11px] text-muted-foreground">({dims.width}m × {dims.height}m × {dims.depth}m)</span>
              </span>
              <button
                onClick={() => setView3D(!view3D)}
                className="rounded-lg bg-panel hover:bg-muted px-3 py-1 text-xs font-semibold transition-colors"
              >
                {view3D ? '📷 2D Floorplan View' : '🧊 3D Isometric View'}
              </button>
            </div>

            {/* Interactive Canvas */}
            <div
              ref={canvasRef}
              onClick={handleCanvasClick}
              onPointerMove={handlePointerMove}
              onPointerUp={handlePointerUp}
              className={`relative flex-1 min-h-[360px] rounded-xl bg-card border-0 shadow-sm overflow-hidden select-none cursor-crosshair ${
                view3D ? 'perspective-1000' : ''
              }`}
              style={{
                backgroundImage: 'radial-gradient(var(--border) 1px, transparent 1px)',
                backgroundSize: '20px 20px'
              }}
            >
              {/* Render Objects / Furniture */}
              {furniture.map((f) => {
                const left = (f.x / dims.width) * 100
                const top = (f.y / dims.height) * 100
                const width = (f.w / dims.width) * 100
                const height = (f.h / dims.height) * 100
                const isSelected = selectedId === f.id

                return (
                  <div
                    key={f.id}
                    onPointerDown={(e) => handlePointerDown(f.id, 'furniture', e)}
                    style={{
                      left: `${left}%`,
                      top: `${top}%`,
                      width: `${width}%`,
                      height: `${height}%`,
                      transform: `rotate(${f.rotation || 0}deg)`
                    }}
                    className={`absolute rounded-lg bg-accent-soft p-1 transition-all flex flex-col items-center justify-center text-center cursor-move ${
                      isSelected ? 'ring-2 ring-accent shadow-md z-20' : 'z-10'
                    }`}
                  >
                    <span className="text-xs">{f.icon || '📦'}</span>
                    <span className="text-[9px] font-semibold truncate max-w-full text-foreground">{f.label}</span>
                  </div>
                )
              })}

              {/* Render Fixed Anchor Nodes */}
              {anchors.map((a) => {
                const left = (a.x / dims.width) * 100
                const top = (a.y / dims.height) * 100
                const isSelected = selectedId === a.id

                return (
                  <div
                    key={a.id}
                    onPointerDown={(e) => handlePointerDown(a.id, 'anchor', e)}
                    style={{ left: `${left}%`, top: `${top}%` }}
                    className={`absolute -translate-x-1/2 -translate-y-1/2 cursor-move z-30 flex flex-col items-center ${
                      isSelected ? 'scale-125' : ''
                    }`}
                  >
                    <div className="relative flex size-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-[10px] font-bold shadow-md">
                      A
                      <span className="absolute -inset-1 rounded-full border border-primary/40 animate-ping" />
                    </div>
                    <span className="mt-0.5 rounded bg-black/80 px-1 py-0.5 font-mono text-[9px] text-white whitespace-nowrap shadow-xs">
                      {a.id}
                    </span>
                  </div>
                )
              })}

              {/* Render Mobile Asset Tags */}
              {tags.map((t) => {
                const left = (t.x / dims.width) * 100
                const top = (t.y / dims.height) * 100
                const isSelected = selectedId === t.id

                return (
                  <div
                    key={t.id}
                    onPointerDown={(e) => handlePointerDown(t.id, 'tag', e)}
                    style={{ left: `${left}%`, top: `${top}%` }}
                    className={`absolute -translate-x-1/2 -translate-y-1/2 cursor-move z-30 flex flex-col items-center ${
                      isSelected ? 'scale-125' : ''
                    }`}
                  >
                    <div className="flex size-6 items-center justify-center rounded-full bg-amber-500 text-black text-[10px] font-bold shadow-md">
                      🏷️
                    </div>
                    <span className="mt-0.5 rounded bg-black/80 px-1 py-0.5 font-mono text-[9px] text-amber-300 whitespace-nowrap shadow-xs">
                      {t.id}
                    </span>
                  </div>
                )
              })}
            </div>

            {/* Helper Instructions Footer */}
            <div className="flex items-center justify-between text-[11px] text-muted-foreground px-1">
              <span>💡 Step {step}: Click canvas to plant elements or drag objects into position.</span>
              <span>Planted Anchors: {anchors.length} | Objects: {furniture.length}</span>
            </div>
          </div>
        </div>

        {/* Footer Actions Bar */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-border/40 bg-card">
          {message ? (
            <span className="text-xs font-medium text-emerald-400">{message}</span>
          ) : (
            <span className="text-xs text-muted-foreground">Changes update the live positioning engine upon deployment.</span>
          )}

          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="rounded-lg bg-panel hover:bg-muted px-4 py-2 text-xs font-semibold text-foreground transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={saveSchematic}
              disabled={isSaving}
              className="rounded-lg bg-accent hover:bg-accent/90 px-5 py-2 text-xs font-semibold text-primary-foreground shadow-sm transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {isSaving ? 'Deploying to System...' : '💾 Deploy & Save Facility Layout'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
