import type { ReactNode } from 'react'
import TypeIt from 'typeit-react'
import { clockTime } from '../lib/format'
import type { ConnStatus, Mode } from '../lib/datasource'
import { ROLE_LABELS, canAccess, type UserRole } from '../lib/rbac'
import { SearchBar, type SearchItem } from './SearchBar'
import { M3Monitor, M3Operations, M3Training, M3Reports, M3Admin } from './common/MaterialIcon'

export type View = 'monitor' | 'control' | 'training' | 'admin' | 'reports'

interface Props {
  view: View
  onView: (v: View) => void
  role: UserRole
  onRole: (v: UserRole) => void
  mode: Mode
  onMode: (m: Mode) => void
  connStatus: ConnStatus | null
  now: number
  hostSsid: string
  online: number
  total: number
  searchItems: SearchItem[]
  focus: string | null
  onFocus: (id: string | null) => void
  children: ReactNode
}

const NAV: { id: View; label: string; minRole: UserRole; icon: ReactNode }[] = [
  {
    id: 'monitor',
    label: 'Live Monitor',
    minRole: 'viewer',
    icon: <M3Monitor size={18} />,
  },
  {
    id: 'control',
    label: 'Operations',
    minRole: 'operator',
    icon: <M3Operations size={18} />,
  },
  {
    id: 'training',
    label: 'ML Training',
    minRole: 'operator',
    icon: <M3Training size={18} />,
  },
  {
    id: 'reports',
    label: 'Reports & Debug',
    minRole: 'viewer',
    icon: <M3Reports size={18} />,
  },
  {
    id: 'admin',
    label: 'Admin',
    minRole: 'admin',
    icon: <M3Admin size={18} />,
  },
]

export function AppShell({ view, onView, role, onRole, mode, onMode, connStatus, now, hostSsid, online, total, searchItems, focus, onFocus, children }: Props) {
  const visibleNav = NAV.filter((n) => canAccess(role, n.minRole))
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Sidebar (desktop) / top bar (mobile) */}
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-60 flex-col border-r border-border/40 bg-card shadow-xs lg:flex">
        <Brand />
        <div className="px-3 pt-4">
          <ModeToggle mode={mode} onMode={onMode} />
        </div>
        <nav className="flex flex-1 flex-col gap-1 px-3 py-4">
          {visibleNav.map((n) => (
            <NavButton key={n.id} active={view === n.id} onClick={() => onView(n.id)} icon={n.icon} label={n.label} />
          ))}
        </nav>
        <RoleSwitcher role={role} onRole={onRole} />
        <HostStatus mode={mode} connStatus={connStatus} ssid={hostSsid} online={online} total={total} />
      </aside>

      {/* Mobile top nav */}
      <div className="sticky top-0 z-20 flex items-center justify-between border-b border-border/40 bg-card px-4 py-3 lg:hidden">
        <Brand compact />
        <div className="flex gap-1 rounded-full bg-panel p-0.5">
          {visibleNav.map((n) => (
            <button
              key={n.id}
              onClick={() => onView(n.id)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                view === n.id ? 'bg-accent text-primary-foreground' : 'text-muted-foreground'
              }`}
            >
              {n.label}
            </button>
          ))}
        </div>
      </div>

      <main className="lg:pl-60">
        <TopBar now={now} view={view} role={role} mode={mode} onMode={onMode} connStatus={connStatus} searchItems={searchItems} focus={focus} onFocus={onFocus} />
        <div className="mx-auto max-w-[1500px] px-4 py-6 sm:px-6 lg:px-8">{children}</div>
      </main>
    </div>
  )
}

function RoleSwitcher({ role, onRole }: { role: UserRole; onRole: (r: UserRole) => void }) {
  return (
    <div className="border-t border-border/40 px-5 py-4">
      <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Access role</label>
      <select
        value={role}
        onChange={(e) => onRole(e.target.value as UserRole)}
        className="w-full rounded-md border-0 bg-panel px-2.5 py-1.5 text-xs text-foreground shadow-xs focus:outline-2 focus:outline-accent"
        title="Demonstration RBAC role for dissertation access control"
      >
        {(Object.keys(ROLE_LABELS) as UserRole[]).map((r) => (
          <option key={r} value={r}>{ROLE_LABELS[r]}</option>
        ))}
      </select>
    </div>
  )
}

function ModeToggle({ mode, onMode }: { mode: Mode; onMode: (m: Mode) => void }) {
  return (
    <div className="grid grid-cols-2 gap-0.5 rounded-lg bg-panel p-0.5 shadow-xs">
      {(['demo', 'live'] as const).map((m) => (
        <button
          key={m}
          onClick={() => onMode(m)}
          className={`flex items-center justify-center gap-1.5 rounded-md py-1.5 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-accent ${
            mode === m ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <span
            className="size-1.5 rounded-full"
            style={{ background: m === 'demo' ? 'var(--accent)' : 'var(--status-online)' }}
          />
          {m === 'demo' ? 'Simulation' : 'Live'}
        </button>
      ))}
    </div>
  )
}

const CONN_META: Record<ConnStatus, { label: string; color: string }> = {
  connecting: { label: 'Connecting', color: 'var(--status-stale)' },
  connected: { label: 'Connected', color: 'var(--status-online)' },
  error: { label: 'Offline', color: 'var(--status-lost)' },
}

function ConnBadge({ mode, connStatus }: { mode: Mode; connStatus: ConnStatus | null }) {
  if (mode === 'demo') {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-panel px-2.5 py-1 text-[11px] font-medium shadow-xs">
        <span className="size-1.5 rounded-full bg-accent" />
        Simulation data
      </span>
    )
  }
  const m = CONN_META[connStatus ?? 'connecting']
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-panel px-2.5 py-1 text-[11px] font-medium shadow-xs">
      <span
        className="size-1.5 rounded-full"
        style={{ background: m.color, animation: connStatus === 'connecting' ? 'pulse-dot 1.2s ease-in-out infinite' : undefined }}
      />
      Live · {m.label}
    </span>
  )
}

function Brand({ compact }: { compact?: boolean }) {
  return (
    <div className={`flex items-center gap-2.5 ${compact ? '' : 'border-b border-border/40 px-5 py-5'}`}>
      <div className="grid size-8 place-items-center rounded-md bg-accent text-primary-foreground">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="size-4">
          <circle cx="12" cy="12" r="3" />
          <path d="M6.5 6.5a7.8 7.8 0 000 11M17.5 6.5a7.8 7.8 0 010 11" opacity="0.9" />
        </svg>
      </div>
      <div className="leading-tight">
        <div className="font-serif text-[17px] font-semibold tracking-tight">FleetView</div>
        {!compact && <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">BLE · RTLS</div>}
      </div>
    </div>
  )
}

function NavButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: ReactNode; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-accent ${
        active ? 'bg-accent-soft text-accent' : 'text-muted-foreground hover:bg-muted hover:text-foreground'
      }`}
    >
      {icon}
      {label}
    </button>
  )
}

function HostStatus({ mode, connStatus, ssid, online, total }: { mode: Mode; connStatus: ConnStatus | null; ssid: string; online: number; total: number }) {
  const isLive = mode === 'live'
  const dead = isLive && connStatus !== 'connected'
  const color = dead ? 'var(--status-lost)' : 'var(--status-online)'
  const label = mode === 'demo' ? 'Simulated web server' : connStatus === 'connected' ? 'Web server live' : 'Web server unreachable'
  return (
    <div className="border-t border-border/40 px-5 py-4">
      <div className="mb-2 flex items-center gap-2">
        <span className="relative flex size-2">
          {!dead && <span className="absolute inline-flex size-full rounded-full opacity-60" style={{ background: color, animation: 'ping-ring 2s ease-out infinite' }} />}
          <span className="relative inline-flex size-2 rounded-full" style={{ background: color }} />
        </span>
        <span className="text-xs font-medium text-foreground">{label}</span>
      </div>
      <dl className="space-y-1 font-mono text-[11px] text-muted-foreground">
        <div className="flex justify-between">
          <dt>Host SSID</dt>
          <dd className="text-foreground">{ssid}</dd>
        </div>
        <div className="flex justify-between">
          <dt>Served from</dt>
          <dd className="text-foreground">ANCHOR-N1</dd>
        </div>
        <div className="flex justify-between">
          <dt>Tags</dt>
          <dd className="text-foreground">
            {online}/{total} active
          </dd>
        </div>
      </dl>
    </div>
  )
}

function TopBar({ now, view, role, mode, onMode, connStatus, searchItems, focus, onFocus }: { now: number; view: View; role: UserRole; mode: Mode; onMode: (m: Mode) => void; connStatus: ConnStatus | null; searchItems: SearchItem[]; focus: string | null; onFocus: (id: string | null) => void }) {
  return (
    <header className="flex items-center justify-between gap-4 border-b border-border/40 bg-background/80 px-4 py-4 backdrop-blur sm:px-6 lg:px-8">
      <div className="min-w-0">
        <h1 className="truncate font-serif text-xl font-semibold tracking-tight sm:text-2xl">
          {view === 'monitor' ? 'Indoor Positioning' : view === 'control' ? 'Operations' : view === 'training' ? 'ML Training' : view === 'reports' ? 'Reports' : 'Administration'}
        </h1>
        <p className="mt-0.5 hidden text-sm text-muted-foreground sm:block">
          {view === 'monitor' ? (
            <TypeIt
              key="monitor"
              options={{ speed: 30, cursor: false, waitUntilVisible: false }}
            >
              Real-time BLE tag movement across anchor mesh · 60 FPS Trilateration
            </TypeIt>
          ) : (
            `Signed in as ${ROLE_LABELS[role]}`
          )}
        </p>
      </div>
      <div className="flex items-center gap-3">
        <SearchBar items={searchItems} focus={focus} onFocus={onFocus} />
        <ConnBadge mode={mode} connStatus={connStatus} />
        {/* Mobile mode switch (sidebar toggle is hidden below lg) */}
        <div className="lg:hidden">
          <ModeToggle mode={mode} onMode={onMode} />
        </div>
        <div className="hidden text-right xl:block">
          <div className="font-mono text-lg font-medium tabular-nums">{clockTime(now)}</div>
          <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">Local · UTC+0</div>
        </div>
      </div>
    </header>
  )
}
