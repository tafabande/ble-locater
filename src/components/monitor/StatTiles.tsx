import type { SimState } from '../../lib/simulation'

interface Props {
  sim: SimState
}

export function StatTiles({ sim }: Props) {
  const count = sim.tags.length || 1
  const online = sim.tags.filter((t) => t.status === 'online').length
  const anchorsOnline = sim.anchors.length
  const avgBattery = Math.round(sim.tags.reduce((a, t) => a + t.battery, 0) / count)
  const meanSigma = Math.round((sim.tags.reduce((a, t) => a + t.uncertainty, 0) / count) * 10) / 10
  const breaches = sim.tags.filter((t) => t.violating).length

  const tiles: { label: string; value: string; sub: string; accent?: boolean; mono?: boolean; danger?: boolean }[] = [
    { label: 'Tags online', value: `${online}`, sub: `of ${sim.tags.length} tracked`, accent: true },
    { label: 'Anchors up', value: `${anchorsOnline}/${anchorsOnline}`, sub: 'mesh nominal' },
    { label: 'Geofence breach', value: `${breaches}`, sub: breaches ? 'active violation' : 'all clear', danger: breaches > 0 },
    { label: 'Mean σ', value: `${meanSigma} m`, sub: 'position uncertainty', mono: true },
    { label: 'Packets / sec', value: `${sim.packetsPerSec}`, sub: 'aggregate ingest' },
    { label: 'Avg battery', value: `${avgBattery}%`, sub: 'fleet mean' },
  ]

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
      {tiles.map((t) => (
        <div
          key={t.label}
          className="rounded-2xl bg-card p-4 sm:p-5 shadow-sm hover:shadow-md transition-all duration-200 flex flex-col justify-between group"
        >
          <div>
            <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{t.label}</div>
            <div
              className="mt-2 text-3xl font-extrabold tabular-nums tracking-tight"
              style={{ color: t.danger ? 'var(--status-lost)' : t.accent ? 'var(--accent)' : 'var(--foreground)' }}
            >
              {t.value}
            </div>
          </div>
          <div className="mt-2 text-xs font-medium text-muted-foreground/80">{t.sub}</div>
        </div>
      ))}
    </div>
  )
}
