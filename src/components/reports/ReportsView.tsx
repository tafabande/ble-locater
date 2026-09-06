import { useState, useMemo } from 'react'
import type { SimState, Tag } from '../../lib/simulation'
import type { Mode, ConnStatus } from '../../lib/datasource'
import type { UserRole } from '../../lib/rbac'
import {
  M3Reports,
  M3Download,
  M3CheckCircle,
  M3Refresh,
  M3BarChart,
  M3Tag,
  M3ShieldAlert,
  M3Beacon,
  M3Walk,
} from '../common/MaterialIcon'

interface Props {
  sim?: SimState
  mode?: Mode
  onMode?: (m: Mode) => void
  connStatus?: ConnStatus | null
  endpoint?: string
  role?: UserRole
}

export function ReportsView({
  sim,
  mode = 'demo',
  endpoint = '/api/state',
}: Props) {
  const [activeTab, setActiveTab] = useState<'overview' | 'movement' | 'occupancy' | 'events'>('overview')
  const [selectedTagId, setSelectedTagId] = useState<string>('')
  const [eventSearch, setEventSearch] = useState('')
  const [eventFilter, setEventFilter] = useState<'all' | 'critical' | 'warning' | 'info'>('all')

  const tags = sim?.tags ?? []
  const anchors = sim?.anchors ?? []
  const alerts = sim?.alerts ?? []
  const events = sim?.events ?? []
  const geofences = sim?.geofences ?? []

  const onlineTags = tags.filter((t: Tag) => t.status !== 'lost')
  const totalTags = tags.length
  const alertsCount = alerts.length

  // Set default selected tag if not set
  const activeTag = tags.find((t: Tag) => t.id === selectedTagId) || tags[0]

  // Zone Occupancy Breakdown
  const zoneOccupancy = useMemo(() => {
    const map = new Map<string, Tag[]>()
    for (const tag of tags) {
      const z = tag.zone || 'Unassigned'
      if (!map.has(z)) map.set(z, [])
      map.get(z)!.push(tag)
    }
    return Array.from(map.entries()).map(([zoneName, zoneTags]) => ({
      name: zoneName,
      count: zoneTags.length,
      tags: zoneTags,
      percentage: totalTags > 0 ? Math.round((zoneTags.length / totalTags) * 100) : 0,
    }))
  }, [tags, totalTags])

  // Combined and filtered event audit trail
  const filteredEvents = useMemo(() => {
    const list = [
      ...alerts.map((a: any) => ({
        id: a.id || `alert-${a.ts}`,
        ts: a.ts,
        type: (a.kind || 'Alert').toUpperCase(),
        tag: a.tag || 'SYSTEM',
        severity: a.severity || 'warning',
        message: a.message,
      })),
      ...events.map((e: any, idx: number) => ({
        id: e.id || `evt-${idx}-${e.ts}`,
        ts: e.ts,
        type: (e.kind || 'Event').toUpperCase(),
        tag: e.tag || 'SYSTEM',
        severity: e.severity || 'info',
        message: e.message,
      })),
    ]

    list.sort((a, b) => b.ts - a.ts)

    return list.filter((item) => {
      const matchSearch =
        !eventSearch ||
        item.message?.toLowerCase().includes(eventSearch.toLowerCase()) ||
        item.tag?.toLowerCase().includes(eventSearch.toLowerCase()) ||
        item.type?.toLowerCase().includes(eventSearch.toLowerCase())

      const matchFilter =
        eventFilter === 'all' || item.severity === eventFilter

      return matchSearch && matchFilter
    })
  }, [alerts, events, eventSearch, eventFilter])

  // Total trail points recorded across all tags
  const totalTrailPoints = useMemo(() => {
    return tags.reduce((acc, t) => acc + (t.trail?.length || 0), 0)
  }, [tags])

  const handleExportJSON = () => {
    const reportData = {
      export_timestamp: new Date().toISOString(),
      system_mode: mode,
      backend_endpoint: endpoint,
      summary: {
        total_tags: totalTags,
        online_tags: onlineTags.length,
        total_anchors: anchors.length,
        geofences_count: geofences.length,
        total_trail_records: totalTrailPoints,
        total_alerts: alertsCount,
      },
      zone_distribution: zoneOccupancy.map((z) => ({
        zone: z.name,
        tag_count: z.count,
        tag_ids: z.tags.map((t) => t.id),
      })),
      tag_histories: tags.map((t) => ({
        id: t.id,
        label: t.label,
        zone: t.zone,
        battery: t.battery,
        status: t.status,
        nearest_anchor: t.nearest,
        coordinates: { x: t.x, y: t.y, floor: t.floor },
        trail_points_count: t.trail?.length || 0,
        trail: t.trail,
      })),
      audit_events: filteredEvents,
    }

    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `spatial_activity_audit_${mode}_${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleExportCSV = () => {
    const headers = ['Timestamp', 'ISO_Time', 'Event_Type', 'Severity', 'Tag_ID', 'Details']
    const rows = filteredEvents.map((e) => [
      e.ts,
      new Date(e.ts).toISOString(),
      `"${e.type}"`,
      e.severity,
      `"${e.tag}"`,
      `"${(e.message || '').replace(/"/g, '""')}"`,
    ])

    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `activity_event_log_${mode}_${Date.now()}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl bg-card p-6 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="grid size-11 place-items-center rounded-2xl bg-accent-soft text-accent">
            <M3Reports size={24} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-foreground tracking-tight">Spatial Activity & History Audit</h2>
              <span
                className={`rounded-full px-3 py-0.5 text-xs font-semibold ${
                  mode === 'live'
                    ? 'bg-emerald-500/10 text-emerald-600'
                    : 'bg-accent-soft text-accent'
                }`}
              >
                {mode === 'live' ? 'Live Telemetry' : 'Simulation History'}
              </span>
            </div>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Tag movement trails, room dwell time analytics, geofence event audits, and data log exports.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-2 rounded-xl bg-muted/60 hover:bg-muted px-4 py-2 text-xs font-semibold text-foreground transition-all cursor-pointer"
          >
            <M3Download size={15} />
            Export CSV Log
          </button>
          <button
            onClick={handleExportJSON}
            className="flex items-center gap-2 rounded-xl bg-accent hover:bg-accent/90 px-4 py-2 text-xs font-semibold text-primary-foreground transition-all shadow-sm cursor-pointer"
          >
            <M3Download size={15} />
            Export JSON Audit
          </button>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex gap-1 rounded-2xl bg-muted/40 p-1.5 text-xs overflow-x-auto">
        {[
          { id: 'overview', label: 'Activity Overview', icon: M3BarChart },
          { id: 'movement', label: 'Tag Movement History', icon: M3Walk },
          { id: 'occupancy', label: 'Room & Zone Occupancy', icon: M3Tag },
          { id: 'events', label: 'Event & Alert Logs', icon: M3Refresh },
        ].map((t) => {
          const Icon = t.icon
          const isAct = activeTab === t.id
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id as any)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl font-semibold transition-all shrink-0 cursor-pointer ${
                isAct ? 'bg-card text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Icon size={16} />
              {t.label}
            </button>
          )
        })}
      </div>

      {/* TAB 1: ACTIVITY OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* Key Metrics */}
          <div className="space-y-6 lg:col-span-8">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="rounded-2xl bg-card p-4 shadow-sm space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Tracked Tags</span>
                <div className="text-2xl font-extrabold text-foreground tabular-nums">
                  {onlineTags.length} <span className="text-xs font-normal text-muted-foreground">/ {totalTags}</span>
                </div>
                <span className="text-[11px] text-emerald-600 font-semibold">Active in field</span>
              </div>

              <div className="rounded-2xl bg-card p-4 shadow-sm space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Anchor Nodes</span>
                <div className="text-2xl font-extrabold text-accent tabular-nums">{anchors.length}</div>
                <span className="text-[11px] text-muted-foreground font-medium">Coverage stations</span>
              </div>

              <div className="rounded-2xl bg-card p-4 shadow-sm space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Trail Records</span>
                <div className="text-2xl font-extrabold text-foreground tabular-nums">{totalTrailPoints.toLocaleString()}</div>
                <span className="text-[11px] text-muted-foreground font-medium">Coordinate fixes</span>
              </div>

              <div className="rounded-2xl bg-card p-4 shadow-sm space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Audit Alerts</span>
                <div className={`text-2xl font-extrabold tabular-nums ${alertsCount > 0 ? 'text-amber-500' : 'text-emerald-600'}`}>
                  {alertsCount}
                </div>
                <span className="text-[11px] text-muted-foreground font-medium">Geofence / battery</span>
              </div>
            </div>

            {/* Zone Distribution Overview */}
            <div className="rounded-2xl bg-card p-6 space-y-4 shadow-sm">
              <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                <M3Tag size={18} className="text-accent" />
                Current Zone Occupancy Distribution
              </h3>

              <div className="space-y-3">
                {zoneOccupancy.map((zone) => (
                  <div key={zone.name} className="space-y-1.5">
                    <div className="flex justify-between text-xs font-semibold">
                      <span className="text-foreground">{zone.name}</span>
                      <span className="text-muted-foreground">
                        {zone.count} tag{zone.count !== 1 ? 's' : ''} ({zone.percentage}%)
                      </span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-muted/40">
                      <div
                        className="h-full rounded-full bg-accent transition-all duration-300"
                        style={{ width: `${Math.max(zone.percentage, 4)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Recent Audit Timeline */}
            <div className="rounded-2xl bg-card p-6 space-y-4 shadow-sm">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                  <M3BarChart size={18} className="text-accent" />
                  Latest System Activity
                </h3>
                <span className="text-xs text-muted-foreground font-medium">Recent 5 events</span>
              </div>

              <div className="space-y-2 text-xs">
                {filteredEvents.slice(0, 5).map((evt) => (
                  <div key={evt.id} className="flex items-start justify-between rounded-xl bg-muted/30 p-3">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-foreground">{evt.tag}</span>
                        <span className="text-[10px] text-muted-foreground">
                          {new Date(evt.ts).toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="text-muted-foreground">{evt.message}</p>
                    </div>
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold ${
                        evt.severity === 'critical'
                          ? 'bg-rose-500/10 text-rose-600'
                          : evt.severity === 'warning'
                          ? 'bg-amber-500/10 text-amber-600'
                          : 'bg-accent-soft text-accent'
                      }`}
                    >
                      {evt.type}
                    </span>
                  </div>
                ))}
                {filteredEvents.length === 0 && (
                  <div className="py-6 text-center text-xs text-muted-foreground">
                    No recent events recorded in this session.
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Sidebar Telemetry Summary */}
          <div className="space-y-6 lg:col-span-4">
            <div className="rounded-2xl bg-card p-6 space-y-4 shadow-sm">
              <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                <M3CheckCircle size={16} className="text-emerald-600" />
                Data Source Status
              </h3>

              <div className="space-y-2 text-xs">
                <div className="flex justify-between items-center rounded-xl bg-muted/30 p-2.5">
                  <span className="text-muted-foreground">Operating Mode</span>
                  <span className="font-bold text-foreground">
                    {mode === 'live' ? 'Live Telemetry Stream' : 'Synthetic Demonstration'}
                  </span>
                </div>

                <div className="flex justify-between items-center rounded-xl bg-muted/30 p-2.5">
                  <span className="text-muted-foreground">Active Anchors</span>
                  <span className="font-bold text-accent">{anchors.length} Stations</span>
                </div>

                <div className="flex justify-between items-center rounded-xl bg-muted/30 p-2.5">
                  <span className="text-muted-foreground">Restricted Geofences</span>
                  <span className="font-bold text-foreground">{geofences.length} Zones Defined</span>
                </div>

                <div className="flex justify-between items-center rounded-xl bg-muted/30 p-2.5">
                  <span className="text-muted-foreground">Telemetry Endpoint</span>
                  <span className="font-mono text-foreground text-[11px] truncate max-w-[130px]">{endpoint}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: TAG MOVEMENT HISTORY */}
      {activeTab === 'movement' && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* Tag Selector & Details */}
          <div className="space-y-6 lg:col-span-4">
            <div className="rounded-2xl bg-card p-6 space-y-4 shadow-sm">
              <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                <M3Tag size={18} className="text-accent" />
                Select Tracked Tag
              </h3>

              <div className="space-y-1.5">
                {tags.map((t: Tag) => {
                  const isSel = (activeTag?.id === t.id)
                  return (
                    <button
                      key={t.id}
                      onClick={() => setSelectedTagId(t.id)}
                      className={`w-full flex items-center justify-between p-3 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                        isSel
                          ? 'bg-accent text-primary-foreground shadow-xs'
                          : 'bg-muted/30 hover:bg-muted/60 text-foreground'
                      }`}
                    >
                      <div className="text-left">
                        <div>{t.label || t.id}</div>
                        <div className={`text-[10px] ${isSel ? 'text-primary-foreground/80' : 'text-muted-foreground'}`}>
                          Zone: {t.zone || 'Unassigned'} • Floor {t.floor}
                        </div>
                      </div>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full ${
                        isSel ? 'bg-black/20 text-white' : 'bg-emerald-500/10 text-emerald-600'
                      }`}>
                        {t.battery}%
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Active Tag Trajectory Trail */}
          <div className="space-y-6 lg:col-span-8">
            {activeTag ? (
              <div className="rounded-2xl bg-card p-6 space-y-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                      <M3Walk size={18} className="text-accent" />
                      Trajectory History: {activeTag.label || activeTag.id}
                    </h3>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Current Position: X: {activeTag.x.toFixed(2)}m, Y: {activeTag.y.toFixed(2)}m (Floor {activeTag.floor})
                    </p>
                  </div>
                  <span className="rounded-full bg-accent-soft px-3 py-1 text-xs font-bold text-accent">
                    {activeTag.trail?.length || 0} Trail Points
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="rounded-xl bg-muted/40 p-3.5 space-y-1">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Current Zone</span>
                    <div className="text-base font-bold text-foreground">{activeTag.zone || 'None'}</div>
                  </div>
                  <div className="rounded-xl bg-muted/40 p-3.5 space-y-1">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Nearest Anchor</span>
                    <div className="text-base font-bold text-accent">{activeTag.nearest || 'N/A'}</div>
                  </div>
                  <div className="rounded-xl bg-muted/40 p-3.5 space-y-1">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Battery Level</span>
                    <div className="text-base font-bold text-emerald-600">{activeTag.battery}%</div>
                  </div>
                  <div className="rounded-xl bg-muted/40 p-3.5 space-y-1">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Status</span>
                    <div className="text-base font-bold text-foreground capitalize">{activeTag.status || 'Active'}</div>
                  </div>
                </div>

                {/* Trail Points Table */}
                <div className="space-y-2">
                  <div className="text-xs font-bold text-foreground">Recent Position Waypoints</div>
                  <div className="max-h-72 overflow-y-auto rounded-xl border border-border/50">
                    <table className="w-full text-left text-xs">
                      <thead className="sticky top-0 bg-muted/60 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                        <tr>
                          <th className="p-2.5">Waypoint #</th>
                          <th className="p-2.5">X Coordinate</th>
                          <th className="p-2.5">Y Coordinate</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/40 font-mono">
                        {(activeTag.trail || []).slice().reverse().map((pt, idx) => (
                          <tr key={idx} className="hover:bg-muted/20">
                            <td className="p-2.5 font-sans font-semibold text-muted-foreground">
                              Point #{(activeTag.trail?.length || 0) - idx}
                            </td>
                            <td className="p-2.5 text-foreground">{pt.x.toFixed(3)} m</td>
                            <td className="p-2.5 text-foreground">{pt.y.toFixed(3)} m</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            ) : (
              <div className="rounded-2xl bg-card p-12 text-center text-xs text-muted-foreground shadow-sm">
                No tags available to display.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: OCCUPANCY & DWELL TIME */}
      {activeTab === 'occupancy' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {zoneOccupancy.map((zone) => (
              <div key={zone.name} className="rounded-2xl bg-card p-5 space-y-4 shadow-sm">
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-foreground text-sm flex items-center gap-2">
                    <M3Beacon size={16} className="text-accent" />
                    {zone.name}
                  </h4>
                  <span className="rounded-full bg-accent-soft px-2.5 py-0.5 text-xs font-bold text-accent">
                    {zone.count} Active
                  </span>
                </div>

                <div className="space-y-2">
                  <span className="text-[11px] text-muted-foreground font-medium">Tags in Room:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {zone.tags.map((t) => (
                      <span
                        key={t.id}
                        className="rounded-lg bg-muted/50 px-2.5 py-1 text-xs font-semibold text-foreground"
                      >
                        {t.label || t.id}
                      </span>
                    ))}
                    {zone.tags.length === 0 && (
                      <span className="text-xs text-muted-foreground italic">No tags currently present</span>
                    )}
                  </div>
                </div>

                <div className="pt-2 border-t border-border/40 flex justify-between text-xs text-muted-foreground">
                  <span>Facility Share:</span>
                  <span className="font-bold text-foreground">{zone.percentage}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 4: EVENT & ALERT LOGS */}
      {activeTab === 'events' && (
        <div className="rounded-2xl bg-card p-6 space-y-4 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
              <M3ShieldAlert size={18} className="text-accent" />
              Event & Geofence Audit Feed
            </h3>

            <div className="flex items-center gap-2 text-xs">
              <input
                type="text"
                value={eventSearch}
                onChange={(e) => setEventSearch(e.target.value)}
                placeholder="Search event logs..."
                className="rounded-xl bg-muted/40 border border-border/50 px-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-accent"
              />
              <select
                value={eventFilter}
                onChange={(e) => setEventFilter(e.target.value as any)}
                className="rounded-xl bg-muted/40 border border-border/50 px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
              >
                <option value="all">All Severities</option>
                <option value="critical">Critical Only</option>
                <option value="warning">Warning Only</option>
                <option value="info">Info Only</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto rounded-xl border border-border/50">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/60 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="p-3">Time</th>
                  <th className="p-3">Type</th>
                  <th className="p-3">Tag / Entity</th>
                  <th className="p-3">Severity</th>
                  <th className="p-3">Message</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {filteredEvents.map((evt) => (
                  <tr key={evt.id} className="hover:bg-muted/20">
                    <td className="p-3 whitespace-nowrap text-muted-foreground font-mono text-[11px]">
                      {new Date(evt.ts).toLocaleTimeString()}
                    </td>
                    <td className="p-3 font-semibold text-foreground">{evt.type}</td>
                    <td className="p-3 font-mono text-accent font-semibold">{evt.tag}</td>
                    <td className="p-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                          evt.severity === 'critical'
                            ? 'bg-rose-500/10 text-rose-600'
                            : evt.severity === 'warning'
                            ? 'bg-amber-500/10 text-amber-600'
                            : 'bg-muted text-muted-foreground'
                        }`}
                      >
                        {evt.severity}
                      </span>
                    </td>
                    <td className="p-3 text-foreground">{evt.message}</td>
                  </tr>
                ))}
                {filteredEvents.length === 0 && (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-muted-foreground">
                      No matching events found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
