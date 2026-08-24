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

interface LastResultMetrics {
  status: 'COMPLETED' | 'ERROR' | 'CANCELLED' | 'IDLE' | 'TRAINING'
  timestamp?: string
  duration?: string
  algorithm?: string
  mae_meters?: number
  rmse?: number
  r2_score?: number
  zone_accuracy?: number
  dataset?: string
  message?: string
}

interface TrainingStatus {
  job: {
    status: 'IDLE' | 'TRAINING' | 'COMPLETED' | 'ERROR' | 'CANCELLED'
    progress: number
    message: string
  }
  last_trained_timestamp?: number | null
  last_successful_run?: string | null
  last_result?: LastResultMetrics | null
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
  const [cancelling, setCancelling] = useState(false)
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
      fetch(`${API_BASE}/api/service/autostart`, { method: 'POST' }).catch(() => {})
      setData((prev) => prev ?? {
        job: { status: 'IDLE', progress: 0, message: 'Auto-starting Location Engine backend service in background...' },
        available_models: {
          distance_estimator: { exists: false, algorithm: 'Initializing...' },
          zone_classifier: { exists: false, algorithm: 'Initializing...' }
        },
        datasets: [],
        logs: ['[SYSTEM] Location Engine API is starting in background...']
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

  const cancelRun = async () => {
    if (!canTrain) {
      setErrorMessage('Admin role required to cancel pipeline run.')
      return
    }
    setCancelling(true)
    try {
      const res = await fetch(`${API_BASE}/api/training/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      if (res.ok) {
        setSuccessMessage('Pipeline execution cancelled.')
        await fetchTrainingStatus()
      } else {
        const err = await res.json().catch(() => ({}))
        setErrorMessage(err.detail || 'Failed to cancel pipeline run.')
      }
    } catch {
      setErrorMessage('Could not contact server to cancel pipeline.')
    } finally {
      setCancelling(false)
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

  const formatIsoTimestamp = (tsStr?: string | null) => {
    if (!tsStr) return null
    try {
      const d = new Date(tsStr)
      if (isNaN(d.getTime())) return tsStr
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' (' + d.toLocaleDateString() + ')'
    } catch {
      return tsStr
    }
  }

  return (
    <div className="space-y-6 animate-pop-in">
      {/* Header Banner */}
      <div className="rounded-xl border border-border bg-panel p-5 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
              👑 AI Studio — SuperLearner & End-to-End ML Pipeline
            </h2>
            <p className="text-xs text-muted-foreground mt-1 max-w-2xl">
              Engineers 60 temporal & RSSI features, evaluates base model tournaments (CatBoost, XGBoost, LightGBM, RandomForest), and trains the Stacking SuperLearner Ensemble for sub-meter positioning accuracy.
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-4 text-xs font-mono text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <span className="size-1.5 rounded-full bg-accent animate-pulse-dot" />
                <span>Last Successful Run: <strong>{formatIsoTimestamp(data?.last_successful_run) || (data?.last_trained_timestamp ? formatTimestamp(data.last_trained_timestamp) : 'Never')}</strong></span>
              </div>
            </div>
          </div>

          {/* Controls & Job State Badge */}
          <div className="flex items-center gap-2">
            <button
              onClick={reloadModels}
              disabled={reloading || !canTrain}
              title="Hot-reload the latest models saved on disk directly into the active positioning engine"
              className="rounded-lg bg-accent-soft hover:bg-accent/20 px-3 py-1.5 text-xs font-semibold text-accent transition-colors flex items-center gap-1.5 shadow-xs disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-accent"
            >
              <span className={reloading ? 'animate-spin' : ''}>🔄</span>
              {reloading ? 'Reloading...' : 'Reload Active Models'}
            </button>

            {jobStatus === 'TRAINING' && canTrain && (
              <button
                onClick={cancelRun}
                disabled={cancelling}
                title="Cancel the active training pipeline run"
                className="rounded-lg bg-panel border border-border hover:bg-muted px-3 py-1.5 text-xs font-semibold text-foreground transition-colors flex items-center gap-1 shadow-xs disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-accent"
              >
                {cancelling ? 'Cancelling...' : '⛔ Cancel Run'}
              </button>
            )}

            {jobStatus === 'TRAINING' && (
              <span className="rounded-full border border-border bg-panel px-3 py-1 text-xs font-semibold text-accent animate-pulse flex items-center gap-1.5 gpu-accelerated">
                <span className="size-2 rounded-full bg-accent animate-ping-ring" />
                ⚡ EXECUTING PIPELINE ({data?.job?.progress ?? 0}%)
              </span>
            )}
            {jobStatus === 'COMPLETED' && (
              <span className="rounded-full border border-border bg-panel px-3 py-1 text-xs font-semibold text-foreground flex items-center gap-1.5">
                ✅ PIPELINE COMPLETED
              </span>
            )}
            {jobStatus === 'CANCELLED' && (
              <span className="rounded-full border border-border bg-panel px-3 py-1 text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
                🚫 PIPELINE CANCELLED
              </span>
            )}
            {jobStatus === 'ERROR' && (
              <span className="rounded-full border border-border bg-panel px-3 py-1 text-xs font-semibold text-foreground flex items-center gap-1.5">
                ❌ PIPELINE ERROR
              </span>
            )}
            {jobStatus === 'IDLE' && (
              <span className="rounded-full border border-border bg-panel px-3 py-1 text-xs font-semibold text-muted-foreground">
                READY TO LAUNCH
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Last Execution Result Card */}
      {data?.last_result && (
        <div className="rounded-xl border border-border bg-panel p-4 space-y-3 shadow-xs animate-pop-in">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-xs font-semibold text-foreground flex items-center gap-2">
              <span>📋 Last Execution Result</span>
              <span className={`rounded-md px-2 py-0.5 text-[10px] font-bold ${
                data.last_result.status === 'COMPLETED'
                  ? 'bg-accent-soft text-accent border border-accent/20'
                  : data.last_result.status === 'CANCELLED'
                  ? 'bg-muted text-muted-foreground border border-border'
                  : 'bg-muted text-foreground border border-border'
              }`}>
                {data.last_result.status}
              </span>
            </h3>
            {data.last_result.timestamp && (
              <span className="text-[11px] font-mono text-muted-foreground">
                Executed: {formatIsoTimestamp(data.last_result.timestamp)}
              </span>
            )}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div className="rounded-lg bg-panel p-2.5 space-y-0.5">
              <span className="text-[10px] text-muted-foreground block">Champion Model</span>
              <span className="font-semibold text-foreground truncate block">{data.last_result.algorithm || 'N/A'}</span>
            </div>
            <div className="rounded-lg bg-panel p-2.5 space-y-0.5">
              <span className="text-[10px] text-muted-foreground block">Execution Duration</span>
              <span className="font-semibold text-purple-300 font-mono block">{data.last_result.duration || 'N/A'}</span>
            </div>
            <div className="rounded-lg bg-panel p-2.5 space-y-0.5">
              <span className="text-[10px] text-muted-foreground block">Distance Error (MAE)</span>
              <span className="font-semibold text-emerald-400 font-mono block">
                {data.last_result.mae_meters !== undefined ? `${data.last_result.mae_meters} m` : 'N/A'}
              </span>
            </div>
            <div className="rounded-lg bg-panel p-2.5 space-y-0.5">
              <span className="text-[10px] text-muted-foreground block">Zone Precision</span>
              <span className="font-semibold text-sky-400 font-mono block">
                {data.last_result.zone_accuracy !== undefined ? `${data.last_result.zone_accuracy}%` : 'N/A'}
              </span>
            </div>
          </div>

          {data.last_result.message && (
            <div className="text-xs text-muted-foreground font-mono bg-panel/50 p-2 rounded-lg border border-border/40">
              <span className="text-purple-300 font-semibold">Outcome: </span>
              {data.last_result.message}
            </div>
          )}
        </div>
      )}

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

      {/* Backend Auto-Healing Background Banner */}
      {isBackendOffline && (
        <div className="rounded-xl border border-sky-500/30 bg-sky-500/10 p-4 flex items-center justify-between gap-3 text-xs text-sky-200">
          <div className="flex items-center gap-3">
            <span className="relative flex size-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75" />
              <span className="relative inline-flex rounded-full size-2.5 bg-sky-500" />
            </span>
            <div>
              <strong className="font-semibold text-sky-100 block flex items-center gap-1.5">
                ⚡ Location Engine Auto-Healing Active
              </strong>
              <span className="text-sky-300/90">Starting backend engine automatically in background (Port 8000). Connecting...</span>
            </div>
          </div>
          <button
            onClick={handleRetryConnection}
            disabled={isRetrying}
            className="rounded-lg bg-sky-500/20 hover:bg-sky-500/30 text-sky-200 font-semibold px-3 py-1.5 text-xs transition-colors flex items-center gap-1.5 shadow-xs"
          >
            <span className={isRetrying ? 'animate-spin' : ''}>🔄</span>
            {isRetrying ? 'Checking...' : 'Check Connection'}
          </button>
        </div>
      )}

      {/* Error Notification Banner */}
      {errorMessage && (
        <div className="rounded-xl border border-border bg-panel p-4 flex items-center justify-between gap-3 text-xs text-foreground">
          <div className="flex items-center gap-2">
            <span className="text-lg">❌</span>
            <div>
              <strong className="font-semibold block text-foreground">Pipeline Execution Status</strong>
              <span>{errorMessage}</span>
            </div>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="rounded-md bg-muted hover:bg-muted/80 px-2.5 py-1 font-semibold text-foreground transition-colors"
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
              <div className="rounded-lg border border-border bg-panel p-3 text-xs font-medium text-muted-foreground">
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
                    className={`rounded-lg border px-3 py-2 text-xs font-medium transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-accent ${
                      algorithm === algo
                        ? 'border-accent bg-accent-soft text-accent font-bold shadow-sm'
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
                className="w-full rounded-lg border border-border bg-panel px-3 py-2 text-xs text-foreground focus:outline-2 focus:outline-accent disabled:opacity-50 disabled:cursor-not-allowed"
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
                  className="w-full accent-accent disabled:opacity-50 disabled:cursor-not-allowed"
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
                  className="w-full accent-accent disabled:opacity-50 disabled:cursor-not-allowed"
                />
              </div>
            </div>

            {/* Action Triggers with States */}
            <div className="space-y-2 pt-2">
              <button
                disabled={isTraining || !canTrain}
                onClick={startTournament}
                className="w-full rounded-lg bg-accent hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2.5 text-xs font-semibold text-primary-foreground transition-colors flex items-center justify-center gap-2 shadow-sm focus-visible:outline-2 focus-visible:outline-accent"
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
              <div className="space-y-2 pt-2 rounded-lg border border-border bg-panel p-3">
                <div className="flex justify-between text-xs">
                  <span className="text-foreground font-medium">{data?.job?.message || 'Processing...'}</span>
                  <span className="text-accent font-bold">{data?.job?.progress ?? 0}%</span>
                </div>
                <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full bg-accent transition-[width] duration-300"
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
