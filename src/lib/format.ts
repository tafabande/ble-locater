import type { TagStatus } from './simulation'

export const STATUS_META: Record<TagStatus, { label: string; color: string; dot: string }> = {
  online: { label: 'Online', color: 'var(--status-online)', dot: 'bg-status-online' },
  stale: { label: 'Stale', color: 'var(--status-stale)', dot: 'bg-status-stale' },
  lost: { label: 'Lost', color: 'var(--status-lost)', dot: 'bg-status-lost' },
}

export function batteryColor(pct: number): string {
  if (pct < 20) return 'var(--status-lost)'
  if (pct < 45) return 'var(--status-stale)'
  return 'var(--status-online)'
}

export function relativeTime(ts: number): string {
  const s = Math.round((Date.now() - ts) / 1000)
  if (s < 60) return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  return `${h}h ago`
}

export function clockTime(ts: number): string {
  const d = new Date(ts)
  return `${d.getHours().toString().padStart(2, '0')}:${d
    .getMinutes()
    .toString()
    .padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`
}
