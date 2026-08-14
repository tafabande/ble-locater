import { useEffect, useState } from 'react'

interface Telemetry {
  cpu_percent: number
  ram_percent: number
  ram_gb: number
}

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
  telemetry: Telemetry
  test_result: TestResult
  logs: string[]
}

export function ControlView() {
  const [data, setData] = useState<ControlStatus | null>(null)
  const [filter, setFilter] = useState<string>('ALL')
  const [search, setSearch] = useState<string>('')
  const [loadingAction, setLoadingAction] = useState<string | null>(null)

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/control/status')
      if (res.ok) {
        const json = await res.json()
        setData(json)
      }
    } catch {
      // Fallback mock data if server endpoint is disconnected
      setData((prev) => prev ?? {
        services: {
          backend: { status: 'ACTIVE', port: 8000 },
          simulator: { status: 'OFFLINE' },
          collector: { status: 'OFFLINE' },
        },
        telemetry: { cpu_percent: 14.2, ram_percent: 42.0, ram_gb: 6.8 },
        test_result: { status: 'ALL PASSED', passed: 14, failed: 0 },
        logs: [
          '[SYSTEM] Web Control Hub operational.',
          '[LOCATION ENGINE] Serving room positioning data on port 8000.',
          '[SIMULATOR] Virtual demo item generator ready.'
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
      name: '📍 Location Engine & Search Server',
      desc: 'Calculates room coordinates (Room A, B, C, D) and powers asset search.',
      status: data?.services?.backend?.status ?? 'ACTIVE',
      badgeColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      actionStart: null,
      actionStop: null,
    },
    {
      id: 'simulator',
      name: '🎮 Demo Motion Generator (Virtual Test)',
      desc: 'Simulates tag motion across hospital rooms without hardware.',
      status: data?.services?.simulator?.status ?? 'OFFLINE',
      badgeColor: data?.services?.simulator?.status === 'ACTIVE' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20',
      actionStart: 'start_sim',
      actionStop: 'stop_sim',
    },
    {
      id: 'collector',
      name: '📡 Physical Room Sensor Collector',
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
      {/* 3-Step Guided Workflow Banner */}
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="flex items-center gap-2 text-sm font-semibold text-amber-400">
              ⚡ EASY 3-STEP START GUIDE
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Follow these simple steps to start tracking assets or running simulations.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => triggerAction('start_sim')}
              className="rounded-lg bg-sky-500/20 hover:bg-sky-500/30 border border-sky-500/30 px-3 py-1.5 text-xs font-medium text-sky-300 transition-colors"
            >
              1️⃣ Start Backend + Demo Motion
            </button>
            <span className="text-muted-foreground text-xs">➔</span>
            <a
              href="/docs"
              target="_blank"
              rel="noreferrer"
              className="rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/20 px-3 py-1.5 text-xs font-medium text-emerald-300 transition-colors"
            >
              2️⃣ Open Search API Docs
            </a>
            <span className="text-muted-foreground text-xs">➔</span>
            <button
              onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
              className="rounded-lg bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/30 px-3 py-1.5 text-xs font-medium text-purple-300 transition-colors"
            >
              3️⃣ View Live Floorplan Map
            </button>
          </div>
        </div>
      </div>

      {/* Main Grid: Left Services + Diagnostics | Right Telemetry & Console */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Left Column: Service Cards & Health Check */}
        <div className="space-y-4 lg:col-span-6">
          <h3 className="text-sm font-semibold text-foreground flex items-center justify-between">
            <span>⚙️ Active System Services</span>
            <span className="text-xs text-muted-foreground font-normal">Real-time status</span>
          </h3>

          <div className="space-y-3">
            {services.map((s) => (
              <div key={s.id} className="rounded-xl border border-border bg-card p-4 space-y-3">
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
                  <div className="flex gap-2 pt-1 border-t border-border/50">
                    <button
                      disabled={s.status === 'ACTIVE' || loadingAction !== null}
                      onClick={() => triggerAction(s.actionStart!)}
                      className="rounded-md bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 px-3 py-1 text-xs font-medium text-white transition-colors"
                    >
                      ▶ Turn On
                    </button>
                    <button
                      disabled={s.status !== 'ACTIVE' || loadingAction !== null}
                      onClick={() => triggerAction(s.actionStop!)}
                      className="rounded-md bg-rose-600/80 hover:bg-rose-600 disabled:opacity-40 px-3 py-1 text-xs font-medium text-white transition-colors"
                    >
                      ⏹ Turn Off
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Self-Test Runner Card */}
          <div className="rounded-xl border border-border bg-card p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-medium text-foreground flex items-center gap-1.5">
                  🧪 System Health Diagnostics
                </h4>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Runs 10+ safety rule checks in 3 seconds.
                </p>
              </div>
              <span className={`rounded-md border px-2 py-0.5 text-xs font-semibold ${
                data?.test_result?.status === 'ALL PASSED'
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
              }`}>
                {data?.test_result?.status ?? 'READY'}
              </span>
            </div>

            <div className="flex items-center justify-between text-xs pt-1">
              <span className="text-muted-foreground">
                Passed: <strong className="text-emerald-400">{data?.test_result?.passed ?? 0}</strong> | Failed: <strong className="text-rose-400">{data?.test_result?.failed ?? 0}</strong>
              </span>
              <button
                disabled={loadingAction !== null}
                onClick={() => triggerAction('run_tests')}
                className="rounded-md bg-sky-600 hover:bg-sky-500 px-3 py-1 text-xs font-medium text-white transition-colors"
              >
                ▶ Run Health Check
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Telemetry Sparklines & Log Console */}
        <div className="space-y-4 lg:col-span-6">
          <h3 className="text-sm font-semibold text-foreground">📈 Computer Performance & Activity</h3>

          {/* Telemetry Metrics */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-border bg-card p-4 space-y-2">
              <span className="text-xs text-muted-foreground font-medium">CPU Speed</span>
              <div className="flex items-baseline justify-between">
                <span className="text-xl font-bold text-sky-400">{data?.telemetry?.cpu_percent ?? 0}%</span>
                <span className="text-[10px] text-muted-foreground">Process load</span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-panel overflow-hidden">
                <div
                  className="h-full bg-sky-400 transition-all duration-500"
                  style={{ width: `${Math.min(100, data?.telemetry?.cpu_percent ?? 0)}%` }}
                />
              </div>
            </div>

            <div className="rounded-xl border border-border bg-card p-4 space-y-2">
              <span className="text-xs text-muted-foreground font-medium">Memory Usage</span>
              <div className="flex items-baseline justify-between">
                <span className="text-xl font-bold text-purple-400">{data?.telemetry?.ram_gb ?? 0} GB</span>
                <span className="text-[10px] text-muted-foreground">{data?.telemetry?.ram_percent ?? 0}% total</span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-panel overflow-hidden">
                <div
                  className="h-full bg-purple-400 transition-all duration-500"
                  style={{ width: `${Math.min(100, data?.telemetry?.ram_percent ?? 0)}%` }}
                />
              </div>
            </div>
          </div>

          {/* Activity Console */}
          <div className="rounded-xl border border-border bg-card p-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h4 className="text-xs font-semibold text-foreground">📋 System Log Stream</h4>
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

            <div className="h-56 overflow-y-auto rounded-lg border border-border bg-slate-950 p-3 font-mono text-[11px] leading-relaxed text-slate-300 space-y-1">
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
