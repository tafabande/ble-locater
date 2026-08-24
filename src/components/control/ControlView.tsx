import { useEffect, useState } from 'react'
import { canAccess, type UserRole } from '../../lib/rbac'

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
      setData((prev) => prev ?? {
        services: {
          backend: { status: 'OFFLINE', port: 8000 },
          simulator: { status: 'OFFLINE' },
          collector: { status: 'OFFLINE' },
        },
        test_result: { status: 'UNKNOWN', passed: 0, failed: 0 },
        logs: [
          '[ERROR] Could not contact the Python API. Start the stack from control.py.',
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
      badgeColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      actionStart: null,
      actionStop: null,
    },
    {
      id: 'simulator',
      name: 'Demo Motion Generator',
      desc: 'Simulates tag motion across indoor facility rooms without hardware.',
      status: data?.services?.simulator?.status ?? 'OFFLINE',
      badgeColor: data?.services?.simulator?.status === 'ACTIVE' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20',
      actionStart: 'start_sim',
      actionStop: 'stop_sim',
    },
    {
      id: 'collector',
      name: 'Physical Sensor Collector',
      desc: 'Reads real Bluetooth signals from USB hardware mounted on room walls.',
      status: data?.services?.collector?.status ?? 'OFFLINE',
      badgeColor: data?.services?.collector?.status === 'ACTIVE' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20',
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
          <h3 className="text-sm font-semibold text-foreground flex items-center justify-between">
            <span>⚙️ Active System Services</span>
            <span className="text-xs text-muted-foreground font-normal">Real-time status</span>
          </h3>

          {!canOperate && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs font-medium text-amber-200">
              Viewer role can inspect service state and logs. Operator or Admin role is required to start and stop services.
            </div>
          )}

          <div className="space-y-3">
            {services.map((s) => (
              <div key={s.id} className="rounded-xl border border-border/40 bg-card p-4 space-y-3 shadow-xs">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-medium text-foreground">{s.name}</h4>
                    <p className="text-xs text-muted-foreground mt-0.5">{s.desc}</p>
                  </div>
                  <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${s.badgeColor}`}>
                    {s.status}
                  </span>
                </div>

                {s.actionStart && (
                  <div className="flex gap-2 pt-1 border-t border-border/30">
                    <button
                      disabled={!canOperate || s.status === 'ACTIVE' || loadingAction !== null}
                      onClick={() => triggerAction(s.actionStart!)}
                      className="rounded-md bg-accent hover:bg-accent/90 disabled:opacity-40 px-3 py-1 text-xs font-medium text-primary-foreground transition-colors focus-visible:outline-2 focus-visible:outline-accent"
                    >
                      Start
                    </button>
                    <button
                      disabled={!canOperate || s.status !== 'ACTIVE' || loadingAction !== null}
                      onClick={() => triggerAction(s.actionStop!)}
                      className="rounded-md bg-panel border border-border hover:bg-muted disabled:opacity-40 px-3 py-1 text-xs font-medium text-foreground transition-colors focus-visible:outline-2 focus-visible:outline-accent"
                    >
                      Stop
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Self-Test Runner Card */}
          <div className="rounded-xl border border-border/40 bg-card p-4 space-y-3 shadow-xs">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-medium text-foreground flex items-center gap-1.5">
                  System Health Check
                </h4>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Runs a short backend self-test and reports pass/fail counts.
                </p>
              </div>
              <span className={`rounded-md border px-2 py-0.5 text-xs font-semibold ${
                data?.test_result?.status === 'ALL PASSED'
                  ? 'bg-accent-soft text-accent border-accent/20'
                  : 'bg-panel text-muted-foreground border-border'
              }`}>
                {data?.test_result?.status ?? 'READY'}
              </span>
            </div>

            <div className="flex items-center justify-between text-xs pt-1">
              <span className="text-muted-foreground">
                Passed: <strong className="text-accent">{data?.test_result?.passed ?? 0}</strong> | Failed: <strong className="text-foreground">{data?.test_result?.failed ?? 0}</strong>
              </span>
              <button
                disabled={!canOperate || loadingAction !== null}
                onClick={() => triggerAction('run_tests')}
                className="rounded-md bg-accent hover:bg-accent/90 px-3 py-1 text-xs font-medium text-primary-foreground transition-colors focus-visible:outline-2 focus-visible:outline-accent"
              >
                Run Health Check
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Activity Console */}
        <div className="space-y-4 lg:col-span-6">
          <h3 className="text-sm font-semibold text-foreground">Activity Log</h3>

          {/* Activity Console */}
          <div className="rounded-xl border border-border/40 bg-card p-4 space-y-3 shadow-xs">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h4 className="text-xs font-semibold text-foreground">Activity Stream</h4>
              <div className="flex items-center gap-2">
                <select
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  className="rounded-md border border-border bg-panel px-2 py-0.5 text-[11px] text-foreground focus:outline-none"
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
                  className="rounded-md border border-border bg-panel px-2 py-0.5 text-[11px] text-foreground placeholder:text-muted-foreground w-28 focus:outline-none"
                />
              </div>
            </div>

            <div className="h-80 overflow-y-auto rounded-lg border border-border bg-slate-950 p-3 font-mono text-[11px] leading-relaxed text-slate-300 space-y-1">
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
                        ? 'text-sky-400'
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
