import { useEffect, useState } from 'react'
import { canAccess, type UserRole } from '../../lib/rbac'
import { M3Settings } from '../common/MaterialIcon'

interface TestResult {
  status: string
  passed: number
  failed: number
}

interface ControlStatus {
  services: {
    backend: { status: string; port: number }
    simulator: { status: string }
    collector: { status: string }
  }
  test_result: TestResult
  logs: string[]
}

export function ControlView({ role }: { role: UserRole }) {
  const [data, setData] = useState<ControlStatus | null>(null)
  const [filter, setFilter] = useState<string>('ALL')
  const [search, setSearch] = useState<string>('')
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const canOperate = canAccess(role, 'operator')

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/control/status')
      if (res.ok) {
        const json = await res.json()
        setData(json)
      }
    } catch {
      fetch('/api/service/autostart', { method: 'POST' }).catch(() => {})
      setData((prev) => prev ?? {
        services: {
          backend: { status: 'INITIALIZING', port: 8000 },
          simulator: { status: 'OFFLINE' },
          collector: { status: 'OFFLINE' },
        },
        test_result: { status: 'INITIALIZING', passed: 0, failed: 0 },
        logs: [
          '[SYSTEM] Location Engine API is auto-starting in background (Port 8000)...',
        ]
      })
    }
  }

  useEffect(() => {
    fetchStatus()
    const iv = setInterval(fetchStatus, 2500)
    return () => clearInterval(iv)
  }, [])

  const triggerAction = async (action: string) => {
    if (!canOperate) return
    setLoadingAction(action)
    try {
      await fetch('/api/control/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      })
      await fetchStatus()
    } catch (e) {
      console.error(e)
    } finally {
      setLoadingAction(null)
    }
  }

  const services = [
    {
      id: 'backend',
      name: 'Location Engine API',
      desc: 'Calculates room coordinates (Room A, B, C, D) and powers asset search.',
      status: data?.services?.backend?.status ?? 'ACTIVE',
      badgeColor: 'bg-emerald-500/10 text-emerald-500',
      actionStart: null,
      actionStop: null,
    },
    {
      id: 'simulator',
      name: 'Demo Motion Generator',
      desc: 'Simulates tag motion across indoor facility rooms without hardware.',
      status: data?.services?.simulator?.status ?? 'OFFLINE',
      badgeColor: data?.services?.simulator?.status === 'ACTIVE' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-rose-500/10 text-rose-500',
      actionStart: 'start_sim',
      actionStop: 'stop_sim',
    },
    {
      id: 'collector',
      name: 'Physical Sensor Collector',
      desc: 'Reads real Bluetooth signals from USB hardware mounted on room walls.',
      status: data?.services?.collector?.status ?? 'OFFLINE',
      badgeColor: data?.services?.collector?.status === 'ACTIVE' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-rose-500/10 text-rose-500',
      actionStart: 'start_collector',
      actionStop: 'stop_collector',
    },
  ]

  const filteredLogs = (data?.logs ?? []).filter((line) => {
    if (filter !== 'ALL' && !line.includes(`[${filter}]`)) return false
    if (search && !line.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  return (
    <div className="space-y-6">
      {/* Main Grid: Left Services & Health Check | Right Activity Console */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Left Column: Service Cards & Health Check */}
        <div className="space-y-4 lg:col-span-6">
          <div className="flex items-center justify-between pb-1">
            <h3 className="text-sm font-bold text-foreground flex items-center gap-2 tracking-tight">
              <M3Settings size={18} className="text-accent" />
              <span>Active System Services</span>
            </h3>
            <span className="text-xs text-muted-foreground font-medium">Real-time status</span>
          </div>

          {!canOperate && (
            <div className="rounded-2xl bg-amber-500/10 p-4 text-xs font-semibold text-amber-300">
              Viewer role can inspect service state and logs. Operator or Admin role is required to start and stop services.
            </div>
          )}

          <div className="space-y-3">
            {services.map((s) => (
              <div key={s.id} className="rounded-2xl bg-card p-5 space-y-3.5 shadow-sm hover:shadow-md transition-all duration-200">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-bold text-foreground tracking-tight">{s.name}</h4>
                    <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{s.desc}</p>
                  </div>
                  <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${s.badgeColor}`}>
                    {s.status}
                  </span>
                </div>

                {s.actionStart && (
                  <div className="flex gap-2 pt-2">
                    <button
                      disabled={!canOperate || s.status === 'ACTIVE' || loadingAction !== null}
                      onClick={() => triggerAction(s.actionStart!)}
                      className="rounded-xl bg-accent hover:bg-accent/90 disabled:opacity-40 px-3.5 py-1.5 text-xs font-semibold text-primary-foreground transition-all focus-visible:outline-2 focus-visible:outline-accent cursor-pointer shadow-xs"
                    >
                      Start
                    </button>
                    <button
                      disabled={!canOperate || s.status !== 'ACTIVE' || loadingAction !== null}
                      onClick={() => triggerAction(s.actionStop!)}
                      className="rounded-xl bg-muted/40 hover:bg-muted disabled:opacity-40 px-3.5 py-1.5 text-xs font-semibold text-foreground transition-all focus-visible:outline-2 focus-visible:outline-accent cursor-pointer"
                    >
                      Stop
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Self-Test Runner Card */}
          <div className="rounded-2xl bg-card p-5 space-y-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-foreground tracking-tight">
                  System Health Check
                </h4>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Runs a short backend self-test and reports pass/fail counts.
                </p>
              </div>
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${
                data?.test_result?.status === 'ALL PASSED'
                  ? 'bg-emerald-500/10 text-emerald-500'
                  : 'bg-muted text-muted-foreground'
              }`}>
                {data?.test_result?.status ?? 'READY'}
              </span>
            </div>

            <div className="flex items-center justify-between text-xs pt-1">
              <span className="text-muted-foreground font-medium">
                Passed: <strong className="text-accent font-bold">{data?.test_result?.passed ?? 0}</strong> | Failed: <strong className="text-foreground font-bold">{data?.test_result?.failed ?? 0}</strong>
              </span>
              <button
                disabled={!canOperate || loadingAction !== null}
                onClick={() => triggerAction('run_tests')}
                className="rounded-xl bg-accent hover:bg-accent/90 px-3.5 py-1.5 text-xs font-semibold text-primary-foreground transition-all focus-visible:outline-2 focus-visible:outline-accent cursor-pointer shadow-xs"
              >
                Run Health Check
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Activity Console */}
        <div className="space-y-4 lg:col-span-6">
          <h3 className="text-sm font-bold text-foreground tracking-tight pb-1">Activity Log</h3>

          {/* Activity Console */}
          <div className="rounded-2xl bg-card p-5 space-y-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Activity Stream</h4>
              <div className="flex items-center gap-2">
                <select
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  className="rounded-xl bg-muted/40 px-3 py-1 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-accent"
                >
                  <option value="ALL">All Categories</option>
                  <option value="SYSTEM">SYSTEM</option>
                  <option value="SIMULATOR">SIMULATOR</option>
                  <option value="COLLECTOR">COLLECTOR</option>
                  <option value="TESTS">TESTS</option>
                </select>
                <input
                  type="text"
                  placeholder="Search logs..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="rounded-xl bg-muted/40 px-3 py-1 text-xs text-foreground placeholder:text-muted-foreground w-32 focus:outline-none focus:ring-2 focus:ring-accent"
                />
              </div>
            </div>

            <div className="h-80 overflow-y-auto rounded-2xl bg-slate-950 p-4 font-mono text-[11px] leading-relaxed text-slate-300 space-y-1 shadow-inner">
              {filteredLogs.length === 0 ? (
                <span className="text-slate-500 italic">No log entries matching filter.</span>
              ) : (
                filteredLogs.map((log, i) => (
                  <div
                    key={i}
                    className={
                      log.includes('[ERROR]')
                        ? 'text-rose-400 font-semibold'
                        : log.includes('[SIMULATOR]')
                        ? 'text-emerald-400'
                        : log.includes('[TESTS]')
                        ? 'text-teal-400'
                        : 'text-slate-300'
                    }
                  >
                    {log}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
