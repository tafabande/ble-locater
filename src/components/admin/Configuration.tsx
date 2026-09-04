import { useState } from 'react'
import type { Anchor } from '../../lib/simulation'
import type { Mode } from '../../lib/datasource'

interface Props {
  anchors: Anchor[]
  mode: Mode
  interval: number
  onInterval: (n: number) => void
  endpoint: string
  onEndpoint: (v: string) => void
}

export function Configuration({ anchors, mode, interval, onInterval, endpoint, onEndpoint }: Props) {
  const [retention, setRetention] = useState('30')
  const [geofence, setGeofence] = useState(true)
  const [smoothing, setSmoothing] = useState(true)
  const [saved, setSaved] = useState(false)

  const save = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 1800)
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.4fr_1fr]">
      {/* Anchor nodes */}
      <div className="rounded-2xl bg-card p-6 shadow-sm space-y-4">
        <div>
          <h3 className="text-sm font-bold text-foreground tracking-tight">Anchor Nodes</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">ESP32 mesh serving the positioning web server</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="font-mono text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
                <th className="px-3 py-2.5">Node</th>
                <th className="px-3 py-2.5">SSID</th>
                <th className="px-3 py-2.5">Ch</th>
                <th className="px-3 py-2.5">TX @1m</th>
                <th className="px-3 py-2.5">Role</th>
              </tr>
            </thead>
            <tbody>
              {anchors.map((a) => (
                <tr key={a.id} className="hover:bg-muted/40 transition-colors rounded-xl">
                  <td className="px-3 py-3 font-mono text-xs font-semibold text-foreground">{a.label}</td>
                  <td className="px-3 py-3 font-mono text-xs text-muted-foreground">{a.ssid}</td>
                  <td className="px-3 py-3 font-mono text-xs tabular-nums">{a.channel}</td>
                  <td className="px-3 py-3 font-mono text-xs tabular-nums">{a.txPower} dBm</td>
                  <td className="px-3 py-3">
                    {a.host ? (
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-accent-soft px-2.5 py-0.5 text-[11px] font-bold text-accent">
                        <span className="size-1.5 rounded-full bg-accent" />
                        Web host
                      </span>
                    ) : (
                      <span className="text-[11px] text-muted-foreground font-medium">Beacon</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Settings */}
      <div className="space-y-6">
        <div className="rounded-2xl bg-card p-6 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-foreground tracking-tight">Positioning</h3>
          <Field label="Refresh interval" hint="How often anchors publish positions">
            <select
              value={interval}
              onChange={(e) => onInterval(Number(e.target.value))}
              className="w-full rounded-xl bg-muted/40 px-3.5 py-2 font-mono text-xs outline-none focus:bg-card focus:ring-2 focus:ring-accent text-foreground"
            >
              <option value={800}>0.8 s · high</option>
              <option value={1500}>1.5 s · balanced</option>
              <option value={3000}>3.0 s · power save</option>
            </select>
          </Field>
          <Field label="Data retention" hint="Days of movement history kept on host">
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={retention}
                onChange={(e) => setRetention(e.target.value)}
                className="w-28 rounded-xl bg-muted/40 px-3.5 py-2 font-mono text-xs tabular-nums outline-none focus:bg-card focus:ring-2 focus:ring-accent text-foreground"
              />
              <span className="font-mono text-xs text-muted-foreground font-medium">days</span>
            </div>
          </Field>
          <Toggle label="Kalman smoothing" hint="Filter jitter from RSSI trilateration" on={smoothing} onToggle={() => setSmoothing((v) => !v)} />
          <Toggle label="Geofence alerts" hint="Notify on unauthorized zone entry" on={geofence} onToggle={() => setGeofence((v) => !v)} />
        </div>

        <div className="rounded-2xl bg-card p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-foreground tracking-tight">Live Data Source</h3>
            <span
              className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-bold"
              style={{
                background: mode === 'live' ? 'var(--accent-soft)' : 'var(--muted)',
                color: mode === 'live' ? 'var(--accent)' : 'var(--muted-foreground)',
              }}
            >
              <span className="size-1.5 rounded-full" style={{ background: mode === 'live' ? 'var(--status-online)' : 'var(--muted-foreground)' }} />
              {mode === 'live' ? 'Active' : 'Standby'}
            </span>
          </div>
          <Field label="Positioning API endpoint" hint="URL the app polls in Live mode (GET → JSON)">
            <input
              value={endpoint}
              onChange={(e) => onEndpoint(e.target.value)}
              spellCheck={false}
              className="w-full rounded-xl bg-muted/40 px-3.5 py-2 font-mono text-xs outline-none focus:bg-card focus:ring-2 focus:ring-accent text-foreground"
            />
          </Field>
          <dl className="space-y-2 font-mono text-xs">
            <Row k="mDNS" v="fleetview.local" />
            <Row k="Firmware" v="v2.4.1-rtls" />
            <Row k="Mode" v={mode === 'live' ? 'Live · polling' : 'Demo · simulated'} />
          </dl>
          <p className="rounded-xl bg-muted/30 p-3 font-mono text-[10px] leading-relaxed text-muted-foreground">
            Switch to <span className="text-foreground font-semibold">Live</span> in the sidebar to poll this endpoint. Demo mode runs a
            built-in simulation and needs no hardware.
          </p>
        </div>

        <button
          onClick={save}
          className="w-full rounded-xl bg-accent px-4 py-3 text-sm font-bold text-primary-foreground transition-all shadow-sm hover:shadow-md hover:opacity-90 focus:ring-2 focus:ring-accent cursor-pointer"
        >
          {saved ? 'Configuration saved ✓' : 'Save configuration'}
        </button>
      </div>
    </div>
  )
}

function Field({ label, hint, children }: { label: string; hint: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <label className="text-xs font-medium">{label}</label>
      <p className="mb-1.5 text-[11px] text-muted-foreground">{hint}</p>
      {children}
    </div>
  )
}

function Toggle({ label, hint, on, onToggle }: { label: string; hint: string; on: boolean; onToggle: () => void }) {
  return (
    <div className="flex items-center justify-between border-t border-border py-3 last:pb-0">
      <div>
        <div className="text-xs font-medium">{label}</div>
        <div className="text-[11px] text-muted-foreground">{hint}</div>
      </div>
      <button
        onClick={onToggle}
        role="switch"
        aria-checked={on}
        className={`relative h-5 w-9 shrink-0 rounded-full transition-colors focus-visible:outline-2 focus-visible:outline-accent ${on ? 'bg-accent' : 'bg-muted'}`}
      >
        <span className={`absolute top-0.5 size-4 rounded-full bg-white shadow transition-[left] ${on ? 'left-[18px]' : 'left-0.5'}`} />
      </button>
    </div>
  )
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between border-b border-border pb-2 last:border-0 last:pb-0">
      <dt className="text-muted-foreground">{k}</dt>
      <dd className="text-foreground">{v}</dd>
    </div>
  )
}
