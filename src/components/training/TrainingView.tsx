import { useEffect, useState } from 'react'
import { canAccess, type UserRole } from '../../lib/rbac'

interface ModelMetrics {
  exists: boolean
  algorithm: string
  mae_meters?: number
  rmse?: number
  r2_score?: number
  accuracy?: number
  f1_score?: number
}

interface TournamentEntry {
  name: string
  mae: number
  rmse: number
  r2: number
  med_ae?: number
}

interface TrainingStatus {
  job: {
    status: 'IDLE' | 'TRAINING' | 'COMPLETED' | 'ERROR'
    progress: number
    message: string
  }
  last_trained_timestamp?: number | null
  available_models: {
    distance_estimator: ModelMetrics
    zone_classifier: ModelMetrics
  }
  tournament_leaderboard?: TournamentEntry[]
  top_features?: Record<string, number>
  datasets: { name: string; rows: number; type: string }[]
  logs?: string[]
}

const API_BASE = ''

export function TrainingView({ role }: { role: UserRole }) {
  const [data, setData] = useState<TrainingStatus | null>(null)
  const [algorithm, setAlgorithm] = useState<string>('SuperLearner')
  const [lr, setLr] = useState<number>(0.08)
  const [trees, setTrees] = useState<number>(250)
  const [dataset, setDataset] = useState<string>('observations.csv')
  const [submitting, setSubmitting] = useState(false)
  const [reloading, setReloading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [isBackendOffline, setIsBackendOffline] = useState(false)
  const [isRetrying, setIsRetrying] = useState(false)
  const canTrain = canAccess(role, 'admin')

  const fetchTrainingStatus = async () => {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 1200)

    try {
      const res = await fetch(`${API_BASE}/api/training/status`, {
        signal: controller.signal,
        headers: { accept: 'application/json' },
      })
      clearTimeout(timer)
      if (res.ok) {
        const json = await res.json()
        setData(json)
        setIsBackendOffline(false)
        if (json.job?.status === 'COMPLETED' && json.job?.message) {
          setSuccessMessage(json.job.message)
        } else if (json.job?.status === 'ERROR' && json.job?.message) {
          setErrorMessage(json.job.message)
        }
      }
    } catch {
      clearTimeout(timer)
      setIsBackendOffline(true)
      setData((prev) => prev ?? {
        job: { status: 'ERROR', progress: 0, message: 'Python Location Engine is not reachable on port 8000.' },
        available_models: {
          distance_estimator: { exists: false, algorithm: 'Unavailable' },
          zone_classifier: { exists: false, algorithm: 'Unavailable' }
        },
        datasets: [],
        logs: ['[ERROR] Could not contact the Python API. Start Stack from control.py, then retry.']
      })
    }
  }

  useEffect(() => {
    fetchTrainingStatus()
    const iv = setInterval(fetchTrainingStatus, 2000)
    return () => clearInterval(iv)
  }, [])

  const startTournament = async () => {
    if (!canTrain) {
      setErrorMessage('Admin role required to start ML training.')
      return
    }
    setSubmitting(true)
    setErrorMessage(null)
    setSuccessMessage(null)

    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 4000)

    try {
      const res = await fetch(`${API_BASE}/api/training/run`, {
        method: 'POST',
        signal: controller.signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          algorithm,
          learning_rate: lr,
          n_estimators: trees,
          dataset,
        }),
      })
      clearTimeout(timer)

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}))
        throw new Error(errJson.detail || `Server returned HTTP ${res.status}`)
      }

      setIsBackendOffline(false)
      await fetchTrainingStatus()
    } catch (e: any) {
      clearTimeout(timer)
      console.error('Training submission error:', e)
      const msg = e?.message || ''
      if (e?.name === 'AbortError' || msg.includes('Failed to fetch') || msg.includes('NetworkError') || msg.includes('fetch')) {
        setIsBackendOffline(true)
        setErrorMessage(null)
      } else {
        setErrorMessage(msg || 'Failed to trigger training run.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  const reloadModels = async () => {
    if (!canTrain) {
      setErrorMessage('Admin role required to reload trained model files.')
      return
    }
    setReloading(true)
    try {
      const res = await fetch(`${API_BASE}/api/models/reload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      if (res.ok) {
        const json = await res.json()
        setSuccessMessage(json.message || 'Models hot-reloaded into live tracking engine.')
        await fetchTrainingStatus()
      } else {
        const errJson = await res.json().catch(() => ({}))
        setErrorMessage(errJson.detail || 'Failed to reload models.')
      }
    } catch (e: any) {
      setErrorMessage('Could not contact backend to reload models.')
    } finally {
      setReloading(false)
    }
  }

  const handleRetryConnection = async () => {
    setIsRetrying(true)
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 2000)
    try {
      const res = await fetch(`${API_BASE}/api/training/status`, { signal: controller.signal })
      clearTimeout(timer)
      if (res.ok) {
        setIsBackendOffline(false)
        setErrorMessage(null)
        const json = await res.json()
        setData(json)
        await startTournament()
      } else {
        setIsBackendOffline(true)
      }
    } catch {
      clearTimeout(timer)
      setIsBackendOffline(true)
    } finally {
      setIsRetrying(false)
    }
  }

  const jobStatus = data?.job?.status ?? 'IDLE'
  const isTraining = jobStatus === 'TRAINING' || submitting

  const formatTimestamp = (ts?: number | null) => {
    if (!ts) return null
    const d = new Date(ts * 1000)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' (' + d.toLocaleDateString() + ')'
  }

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="rounded-xl bg-purple-500/10 p-5 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-purple-300 flex items-center gap-2">
              👑 AI Studio — SuperLearner & End-to-End ML Pipeline
            </h2>
            <p className="text-xs text-muted-foreground mt-1 max-w-2xl">
              Engineers 60 temporal & RSSI features, evaluates base model tournaments (CatBoost, XGBoost, LightGBM, RandomForest), and trains the Stacking SuperLearner Ensemble for sub-meter positioning accuracy.
            </p>
            {data?.last_trained_timestamp && (
              <div className="mt-2 text-xs text-purple-200/80 flex items-center gap-2 font-mono">
                <span className="size-1.5 rounded-full bg-emerald-400" />
                <span>Last Updated From Python Trainer: <strong>{formatTimestamp(data.last_trained_timestamp)}</strong></span>
              </div>
            )}
          </div>

          {/* Controls & Job State Badge */}
          <div className="flex items-center gap-2">
            <button
              onClick={reloadModels}
              disabled={reloading || !canTrain}
              title="Hot-reload the latest models saved on disk directly into the active positioning engine"
              className="rounded-lg bg-purple-500/15 hover:bg-purple-500/25 px-3 py-1.5 text-xs font-semibold text-purple-200 transition-colors flex items-center gap-1.5 shadow-xs disabled:opacity-50"
            >
              <span className={reloading ? 'animate-spin' : ''}>🔄</span>
              {reloading ? 'Reloading...' : 'Reload Active Models'}
            </button>

            {jobStatus === 'TRAINING' && (
              <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-xs font-semibold text-amber-400 animate-pulse flex items-center gap-1.5">
                <span className="size-2 rounded-full bg-amber-400 animate-ping" />
                ⚡ EXECUTING PIPELINE ({data?.job?.progress ?? 0}%)
              </span>
            )}
            {jobStatus === 'COMPLETED' && (
              <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
                ✅ PIPELINE COMPLETED
              </span>
            )}
            {jobStatus === 'ERROR' && (
              <span className="rounded-full border border-rose-500/30 bg-rose-500/10 px-3 py-1 text-xs font-semibold text-rose-400 flex items-center gap-1.5">
                ❌ PIPELINE ERROR
              </span>
            )}
            {jobStatus === 'IDLE' && (
              <span className="rounded-full border border-purple-500/30 bg-purple-500/10 px-3 py-1 text-xs font-semibold text-purple-300">
                READY TO LAUNCH
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Success Notification Banner */}
      {successMessage && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 flex items-center justify-between gap-3 text-xs text-emerald-300">
          <div className="flex items-center gap-2">
            <span className="text-lg">🎉</span>
            <div>
              <strong className="font-semibold block text-emerald-200">Operation Successful</strong>
              <span>{successMessage}</span>
            </div>
          </div>
          <button
            onClick={() => setSuccessMessage(null)}
            className="rounded-md bg-emerald-500/20 hover:bg-emerald-500/30 px-2.5 py-1 font-semibold text-emerald-300 transition-colors"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Backend Offline Interactive Prompt Card */}
      {isBackendOffline && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-5 space-y-3">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <span className="text-2xl p-1.5 bg-amber-500/20 rounded-lg">⚡</span>
              <div>
                <h3 className="text-sm font-semibold text-amber-200 flex items-center gap-2">
                  Location Engine Backend (Port 8000) is Offline
                </h3>
                <p className="text-xs text-amber-300/80 mt-1 max-w-xl">
                  The ML training pipeline requires <strong>Service #1 (Location Engine API)</strong> to be active on port 8000. Start it in <code className="bg-amber-950/60 text-amber-200 px-1.5 py-0.5 rounded font-mono text-[11px]">control.py</code> or click <strong>"Start Stack"</strong> in the console.
                </p>
              </div>
            </div>
            <button
              onClick={() => setIsBackendOffline(false)}
              className="text-xs text-amber-400/60 hover:text-amber-200 transition-colors"
            >
              ✕ Dismiss
            </button>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-amber-500/20">
            <div className="flex items-center gap-2 text-xs text-amber-300/90">
              <span className="inline-block size-2 rounded-full bg-amber-400 animate-ping" />
              <span>Ready to connect once the service is started:</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleRetryConnection}
                disabled={isRetrying}
                className="rounded-lg bg-amber-500 hover:bg-amber-400 text-amber-950 font-semibold px-4 py-2 text-xs flex items-center gap-2 transition-all shadow-sm disabled:opacity-50"
              >
                <span className={isRetrying ? 'animate-spin' : ''}>🔄</span>
                {isRetrying ? 'Checking Port 8000...' : 'Start / Retry Connection'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Error Notification Banner */}
      {errorMessage && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 flex items-center justify-between gap-3 text-xs text-rose-300">
          <div className="flex items-center gap-2">
            <span className="text-lg">❌</span>
            <div>
              <strong className="font-semibold block text-rose-200">Pipeline Execution Status</strong>
              <span>{errorMessage}</span>
            </div>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="rounded-md bg-rose-500/20 hover:bg-rose-500/30 px-2.5 py-1 font-semibold text-rose-300 transition-colors"
          >
            Clear Message
          </button>
        </div>
      )}

      {/* Main Grid: Controls vs Evaluation & Metrics */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Left Column: Model Training Configuration */}
        <div className="space-y-4 lg:col-span-6">
          <div className="rounded-xl bg-card p-5 space-y-4 shadow-xs">
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <span>⚙️ Pipeline & Ensemble Settings</span>
            </h3>

            {!canTrain && (
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs font-medium text-amber-200">
                Operator can review training state and logs. Admin role is required to start training or reload models.
              </div>
            )}

            {/* Algorithm Selector */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Architecture / Stacking Ensemble</label>
              <div className="grid grid-cols-2 gap-2">
                {['SuperLearner', 'CatBoost', 'XGBoost', 'LightGBM', 'RandomForest'].map((algo) => (
                  <button
                    key={algo}
                    disabled={isTraining || !canTrain}
                    onClick={() => setAlgorithm(algo)}
                    className={`rounded-lg border px-3 py-2 text-xs font-medium transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed ${
                      algorithm === algo
                        ? 'border-purple-500/50 bg-purple-500/10 text-purple-300 font-bold shadow-sm'
                        : 'border-border bg-panel text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {algo === 'SuperLearner' ? '👑 SuperLearner (Stacking)' : algo}
                  </button>
                ))}
              </div>
            </div>

            {/* Dataset Selector */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Observation Dataset</label>
              <select
                disabled={isTraining || !canTrain}
                value={dataset}
                onChange={(e) => setDataset(e.target.value)}
                className="w-full rounded-lg border border-border bg-panel px-3 py-2 text-xs text-foreground focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {(data?.datasets ?? []).map((ds) => (
                  <option key={ds.name} value={ds.name}>
                    {ds.name} ({ds.rows.toLocaleString()} samples - {ds.type})
                  </option>
                ))}
              </select>
            </div>

            {/* Hyperparameter Inputs */}
            <div className="grid grid-cols-2 gap-3 pt-1">
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">Learning Rate ({lr})</label>
                <input
                  type="range"
                  disabled={isTraining || !canTrain}
                  min="0.01"
                  max="0.30"
                  step="0.01"
                  value={lr}
                  onChange={(e) => setLr(parseFloat(e.target.value))}
                  className="w-full accent-purple-400 disabled:opacity-50 disabled:cursor-not-allowed"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">Trees / Estimators ({trees})</label>
                <input
                  type="range"
                  disabled={isTraining || !canTrain}
                  min="50"
                  max="1000"
                  step="50"
                  value={trees}
                  onChange={(e) => setTrees(parseInt(e.target.value))}
                  className="w-full accent-purple-400 disabled:opacity-50 disabled:cursor-not-allowed"
                />
              </div>
            </div>

            {/* Action Triggers with States */}
            <div className="space-y-2 pt-2">
              <button
                disabled={isTraining || !canTrain}
                onClick={startTournament}
                className="w-full rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-purple-900/60 disabled:hover:bg-purple-900/60 px-4 py-2.5 text-xs font-semibold text-white transition-all flex items-center justify-center gap-2 shadow-sm"
              >
                {submitting ? (
                  <>
                    <span className="size-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Connecting to Python Engine...
                  </>
                ) : isTraining ? (
                  <>
                    <span className="size-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Executing SuperLearner Pipeline ({data?.job?.progress ?? 0}%)...
                  </>
                ) : (
                  '👑 Launch Complete SuperLearner Pipeline & Tournament'
                )}
              </button>
            </div>

            {/* Live Progress Bar */}
            {isTraining && (
              <div className="space-y-2 pt-2 rounded-lg border border-purple-500/20 bg-purple-500/5 p-3">
                <div className="flex justify-between text-xs">
                  <span className="text-purple-200 font-medium">{data?.job?.message || 'Processing...'}</span>
                  <span className="text-purple-300 font-bold">{data?.job?.progress ?? 0}%</span>
                </div>
                <div className="h-2 w-full rounded-full bg-panel overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-purple-500 to-indigo-400 transition-all duration-500"
                    style={{ width: `${Math.max(5, data?.job?.progress ?? 0)}%` }}
                  />
                </div>
              </div>
            )}
            <div className="rounded-lg border border-border bg-slate-950 p-3">
              <div className="mb-2 flex items-center justify-between">
                <h4 className="text-xs font-semibold text-slate-200">Training Log</h4>
                <span className="text-[11px] text-slate-500">{data?.logs?.length ?? 0} recent entries</span>
              </div>
              <div className="max-h-40 space-y-1 overflow-y-auto font-mono text-[11px] leading-relaxed text-slate-300">
                {(data?.logs ?? ['Waiting for backend status...']).map((line, i) => (
                  <div
                    key={`${line}-${i}`}
                    className={line.includes('[ERROR]') ? 'text-rose-400' : line.includes('[TRAINING]') ? 'text-purple-300' : 'text-slate-300'}
                  >
                    {line}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Model Metrics & Evaluation */}
        <div className="space-y-4 lg:col-span-6">
          <h3 className="text-sm font-semibold text-foreground">📊 Champion ML Model Performance</h3>

          {/* Distance Estimator Card */}
          <div className="rounded-xl bg-card p-4 space-y-3 shadow-xs">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-medium text-foreground">📏 Distance Estimator Model</h4>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Algorithm: <strong className="text-sky-300">{data?.available_models?.distance_estimator?.algorithm}</strong>
                </p>
              </div>
              <span className="rounded-md bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-xs font-semibold text-emerald-400">
                ACTIVE
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2 pt-1 border-t border-border/50 text-center">
              <div className="rounded-lg bg-panel p-2">
                <span className="text-[10px] text-muted-foreground block">Mean Error (MAE)</span>
                <span className="text-sm font-bold text-emerald-400">
                  {data?.available_models?.distance_estimator?.mae_meters} m
                </span>
              </div>
              <div className="rounded-lg bg-panel p-2">
                <span className="text-[10px] text-muted-foreground block">RMSE Error</span>
                <span className="text-sm font-bold text-sky-400">
                  {data?.available_models?.distance_estimator?.rmse} m
                </span>
              </div>
              <div className="rounded-lg bg-panel p-2">
                <span className="text-[10px] text-muted-foreground block">R² Score</span>
                <span className="text-sm font-bold text-purple-400">
                  {data?.available_models?.distance_estimator?.r2_score}
                </span>
              </div>
            </div>
          </div>

          {/* Zone Classifier Card */}
          <div className="rounded-xl bg-card p-4 space-y-3 shadow-xs">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-medium text-foreground">🏢 Room/Zone Classifier</h4>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Algorithm: <strong className="text-purple-300">{data?.available_models?.zone_classifier?.algorithm}</strong>
                </p>
              </div>
              <span className="rounded-md bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-xs font-semibold text-emerald-400">
                ACTIVE
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-1 border-t border-border/50 text-center">
              <div className="rounded-lg bg-panel p-2">
                <span className="text-[10px] text-muted-foreground block">Zone Precision</span>
                <span className="text-sm font-bold text-emerald-400">
                  {((data?.available_models?.zone_classifier?.accuracy ?? 0) * 100).toFixed(1)}%
                </span>
              </div>
              <div className="rounded-lg bg-panel p-2">
                <span className="text-[10px] text-muted-foreground block">F1-Score</span>
                <span className="text-sm font-bold text-purple-400">
                  {data?.available_models?.zone_classifier?.f1_score}
                </span>
              </div>
            </div>
          </div>

          {/* Tournament Top Leaderboard */}
          {data?.tournament_leaderboard && data.tournament_leaderboard.length > 0 && (
            <div className="rounded-xl bg-card p-4 space-y-2.5 shadow-xs">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                🏆 Top SuperLearner Tournament Models
              </h4>
              <div className="space-y-1.5 max-h-36 overflow-y-auto text-xs">
                {data.tournament_leaderboard.slice(0, 4).map((m, idx) => (
                  <div key={m.name} className="flex items-center justify-between p-1.5 rounded-lg bg-panel">
                    <span className="font-medium text-foreground flex items-center gap-1.5">
                      <span className="text-purple-400 font-bold">#{idx + 1}</span> {m.name}
                    </span>
                    <div className="flex items-center gap-3 text-muted-foreground font-mono text-[11px]">
                      <span>MAE: <strong className="text-emerald-400">{m.mae.toFixed(3)}m</strong></span>
                      <span>R²: <strong className="text-purple-300">{m.r2.toFixed(2)}</strong></span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
