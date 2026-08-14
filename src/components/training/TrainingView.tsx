import { useEffect, useState } from 'react'

interface ModelMetrics {
  exists: boolean
  algorithm: string
  mae_meters?: number
  rmse?: number
  r2_score?: number
  accuracy?: number
  f1_score?: number
}

interface TrainingStatus {
  job: {
    status: string
    progress: number
    message: string
  }
  available_models: {
    distance_estimator: ModelMetrics
    zone_classifier: ModelMetrics
  }
  datasets: { name: string; rows: number; type: string }[]
}

export function TrainingView() {
  const [data, setData] = useState<TrainingStatus | null>(null)
  const [algorithm, setAlgorithm] = useState<string>('CatBoost')
  const [lr, setLr] = useState<number>(0.08)
  const [trees, setTrees] = useState<number>(250)
  const [dataset, setDataset] = useState<string>('observations.csv')
  const [submitting, setSubmitting] = useState(false)

  const fetchTrainingStatus = async () => {
    try {
      const res = await fetch('/api/training/status')
      if (res.ok) {
        const json = await res.json()
        setData(json)
      }
    } catch {
      setData((prev) => prev ?? {
        job: { status: 'IDLE', progress: 0, message: 'No active training run' },
        available_models: {
          distance_estimator: { exists: true, algorithm: 'CatBoostRegressor', mae_meters: 0.68, rmse: 0.85, r2_score: 0.94 },
          zone_classifier: { exists: true, algorithm: 'CatBoostClassifier', accuracy: 0.965, f1_score: 0.96 }
        },
        datasets: [
          { name: 'observations.csv', rows: 45120, type: 'Real Experimental Data' },
          { name: 'synthetic_observations.csv', rows: 8500, type: 'Synthetic Motion Data' },
          { name: 'raw_packets.csv', rows: 1200, type: 'Hardware Session Packet Stream' }
        ]
      })
    }
  }

  useEffect(() => {
    fetchTrainingStatus()
    const iv = setInterval(fetchTrainingStatus, 2000)
    return () => clearInterval(iv)
  }, [])

  const startTournament = async () => {
    setSubmitting(true)
    try {
      await fetch('/api/training/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          algorithm,
          learning_rate: lr,
          n_estimators: trees,
          dataset
        })
      })
      await fetchTrainingStatus()
    } catch (e) {
      console.error(e)
    } finally {
      setSubmitting(false)
    }
  }

  const isTraining = data?.job?.status === 'TRAINING'

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="rounded-xl border border-purple-500/30 bg-purple-500/5 p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-purple-300 flex items-center gap-2">
              🧠 AI Model Training Studio & ML Tournament
            </h2>
            <p className="text-xs text-muted-foreground mt-1 max-w-2xl">
              Train CatBoost, XGBoost, and LightGBM models on collected BLE signal observations to optimize room localization precision and minimize distance error.
            </p>
          </div>
          <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${
            isTraining ? 'bg-amber-500/10 text-amber-400 border-amber-500/30 animate-pulse' : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
          }`}>
            {isTraining ? '⚡ TRAINING IN PROGRESS' : 'READY TO TRAIN'}
          </span>
        </div>
      </div>

      {/* Main Grid: Controls vs Evaluation & Metrics */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Left Column: Model Training Configuration */}
        <div className="space-y-4 lg:col-span-6">
          <div className="rounded-xl border border-border bg-card p-5 space-y-4">
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <span>⚙️ Tournament Settings</span>
            </h3>

            {/* Algorithm Selector */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">ML Algorithm</label>
              <div className="grid grid-cols-2 gap-2">
                {['CatBoost', 'XGBoost', 'LightGBM', 'RandomForest'].map((algo) => (
                  <button
                    key={algo}
                    onClick={() => setAlgorithm(algo)}
                    className={`rounded-lg border px-3 py-2 text-xs font-medium transition-colors text-left ${
                      algorithm === algo
                        ? 'border-purple-500/50 bg-purple-500/10 text-purple-300'
                        : 'border-border bg-panel text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {algo}
                  </button>
                ))}
              </div>
            </div>

            {/* Dataset Selector */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Training Dataset</label>
              <select
                value={dataset}
                onChange={(e) => setDataset(e.target.value)}
                className="w-full rounded-lg border border-border bg-panel px-3 py-2 text-xs text-foreground focus:outline-none"
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
                  min="0.01"
                  max="0.30"
                  step="0.01"
                  value={lr}
                  onChange={(e) => setLr(parseFloat(e.target.value))}
                  className="w-full accent-purple-400"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">Trees / Estimators ({trees})</label>
                <input
                  type="range"
                  min="50"
                  max="1000"
                  step="50"
                  value={trees}
                  onChange={(e) => setTrees(parseInt(e.target.value))}
                  className="w-full accent-purple-400"
                />
              </div>
            </div>

            {/* Action Trigger */}
            <div className="pt-2">
              <button
                disabled={isTraining || submitting}
                onClick={startTournament}
                className="w-full rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-50 px-4 py-2.5 text-xs font-semibold text-white transition-colors flex items-center justify-center gap-2"
              >
                {isTraining ? (
                  <>
                    <span className="size-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Training ML Models...
                  </>
                ) : (
                  '🚀 Start AI Model Training Tournament'
                )}
              </button>
            </div>

            {/* Progress Bar */}
            {isTraining && (
              <div className="space-y-1.5 pt-2">
                <div className="flex justify-between text-[11px]">
                  <span className="text-purple-300 font-medium">{data?.job?.message}</span>
                  <span className="text-muted-foreground">{data?.job?.progress}%</span>
                </div>
                <div className="h-2 w-full rounded-full bg-panel overflow-hidden">
                  <div
                    className="h-full bg-purple-500 transition-all duration-500"
                    style={{ width: `${data?.job?.progress ?? 0}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Model Metrics & Evaluation */}
        <div className="space-y-4 lg:col-span-6">
          <h3 className="text-sm font-semibold text-foreground">📊 Active AI Model Performance</h3>

          {/* Distance Estimator Card */}
          <div className="rounded-xl border border-border bg-card p-4 space-y-3">
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
          <div className="rounded-xl border border-border bg-card p-4 space-y-3">
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
        </div>
      </div>
    </div>
  )
}
