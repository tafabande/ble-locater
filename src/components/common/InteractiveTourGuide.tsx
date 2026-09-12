import { useState, useEffect } from 'react'
import type { TourStep } from '../../lib/tourGuides'
import {
  M3Sparkles,
  M3Check,
  M3Info,
  M3Close,
  M3ChevronRight,
  M3ChevronLeft,
} from './MaterialIcon'

interface Props {
  steps: TourStep[]
  isOpen: boolean
  onClose: () => void
  onTabChange?: (tabKey: string) => void
  tourTitle?: string
}

export function InteractiveTourGuide({
  steps,
  isOpen,
  onClose,
  onTabChange,
  tourTitle = 'Interactive Quest Guide',
}: Props) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0)
  const [isMinimized, setIsMinimized] = useState(false)
  const [isCompleted, setIsCompleted] = useState(false)

  // Ensure current step index is within bounds when steps change
  const currentStep = steps[currentStepIndex] || steps[0]
  const totalSteps = steps.length
  const totalXp = steps.reduce((sum, s) => sum + s.xpReward, 0)
  const earnedXp = steps.slice(0, currentStepIndex + 1).reduce((sum, s) => sum + s.xpReward, 0)

  // Handle element spotlighting and auto-scrolling
  useEffect(() => {
    if (!isOpen || !currentStep || isCompleted) {
      // Clean up any highlights
      document.querySelectorAll('.tour-target-highlight').forEach((el) => {
        el.classList.remove('tour-target-highlight')
      })
      return
    }

    // If step requests a tab change, notify parent
    if (currentStep.tabKey && onTabChange) {
      onTabChange(currentStep.tabKey)
    }

    // Give DOM a small tick to render any switched tab contents
    const timer = window.setTimeout(() => {
      // Remove previous highlights
      document.querySelectorAll('.tour-target-highlight').forEach((el) => {
        el.classList.remove('tour-target-highlight')
      })

      const target = document.getElementById(currentStep.targetId)
      if (target) {
        target.classList.add('tour-target-highlight')
        target.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    }, 120)

    return () => {
      window.clearTimeout(timer)
      document.querySelectorAll('.tour-target-highlight').forEach((el) => {
        el.classList.remove('tour-target-highlight')
      })
    }
  }, [isOpen, currentStep, isCompleted, onTabChange])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      document.querySelectorAll('.tour-target-highlight').forEach((el) => {
        el.classList.remove('tour-target-highlight')
      })
    }
  }, [])

  if (!isOpen) return null

  const handleNext = () => {
    if (currentStepIndex < totalSteps - 1) {
      setCurrentStepIndex((prev) => prev + 1)
    } else {
      setIsCompleted(true)
    }
  }

  const handlePrev = () => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex((prev) => prev - 1)
    }
  }

  const handleRestart = () => {
    setCurrentStepIndex(0)
    setIsCompleted(false)
  }

  // Badge styling helper
  const getBadgeStyle = (type: TourStep['badge']['type']) => {
    switch (type) {
      case 'must_have':
        return 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30'
      case 'recommended':
        return 'bg-teal-500/15 text-teal-700 dark:text-teal-300 border-teal-500/30'
      case 'optional':
        return 'bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30'
      case 'advanced':
        return 'bg-purple-500/15 text-purple-700 dark:text-purple-300 border-purple-500/30'
      default:
        return 'bg-muted text-muted-foreground border-border'
    }
  }

  // Minimized Pill HUD
  if (isMinimized) {
    return (
      <aside
        aria-label="Interactive Tour Guide Minimized"
        className="fixed bottom-5 right-5 z-50 flex items-center gap-2.5 rounded-2xl bg-card/95 border-2 border-teal-500 p-2.5 shadow-2xl backdrop-blur-md animate-in fade-in slide-in-from-bottom-3"
      >
        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-teal-500 text-white font-bold text-sm shadow-sm">
          🎮
        </div>
        <div className="text-left">
          <div className="text-xs font-bold text-foreground">
            {isCompleted ? '🎉 Quest Complete!' : `Quest ${currentStepIndex + 1} of ${totalSteps}`}
          </div>
          <div className="text-[10px] text-teal-600 dark:text-teal-400 font-mono font-bold">
            {isCompleted ? '⭐ 500 XP Earned' : `⭐ ${earnedXp} XP`}
          </div>
        </div>
        <button
          type="button"
          onClick={() => setIsMinimized(false)}
          className="ml-1 rounded-xl bg-teal-600 hover:bg-teal-700 text-white px-2.5 py-1 text-xs font-bold cursor-pointer transition-all shadow-xs"
        >
          Expand
        </button>
        <button
          type="button"
          onClick={onClose}
          className="rounded-xl p-1 text-muted-foreground hover:bg-muted hover:text-foreground cursor-pointer transition-all"
          title="Close Tour"
        >
          <M3Close size={16} />
        </button>
      </aside>
    )
  }

  return (
    <aside
      aria-label="Interactive Tour Guide"
      className="fixed bottom-5 right-5 z-50 max-w-lg w-[calc(100vw-2.5rem)] rounded-3xl bg-card/95 border border-teal-500/40 shadow-2xl backdrop-blur-xl transition-all duration-300 animate-in fade-in slide-in-from-bottom-4"
    >
      {/* Top Game HUD Header */}
      <div className="flex items-center justify-between border-b border-border/40 bg-gradient-to-r from-teal-500/10 via-card to-card px-5 py-3.5 rounded-t-3xl">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-teal-500/20 text-teal-600 dark:text-teal-400 text-lg shadow-inner">
            🎮
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-black uppercase tracking-wider text-teal-600 dark:text-teal-400 font-mono">
                {tourTitle}
              </span>
              <span className="rounded-full bg-teal-500/20 px-2 py-0.2 text-[10px] font-bold text-teal-700 dark:text-teal-300">
                Level 1
              </span>
            </div>
            <div className="text-xs font-bold text-foreground leading-tight">
              {isCompleted ? 'Quest Accomplished!' : currentStep.questTitle}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          {/* XP Pill */}
          <span className="hidden sm:inline-flex items-center gap-1 rounded-full bg-amber-500/15 border border-amber-500/30 px-2.5 py-0.5 text-[11px] font-mono font-bold text-amber-600 dark:text-amber-400">
            ⭐ {isCompleted ? totalXp : earnedXp} / {totalXp} XP
          </span>

          {/* Minimize */}
          <button
            type="button"
            onClick={() => setIsMinimized(true)}
            className="rounded-xl p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground cursor-pointer transition-all"
            title="Minimize Guide"
          >
            _
          </button>

          {/* Close */}
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground cursor-pointer transition-all"
            title="Exit Guide"
          >
            <M3Close size={16} />
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="h-1.5 w-full bg-muted overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-teal-500 to-emerald-400 transition-all duration-300"
          style={{
            width: isCompleted ? '100%' : `${((currentStepIndex + 1) / totalSteps) * 100}%`,
          }}
        />
      </div>

      {/* Main Content Body */}
      <div className="p-5 space-y-4 max-h-[70vh] overflow-y-auto">
        {isCompleted ? (
          /* Victory Completion Screen */
          <div className="text-center py-4 space-y-3">
            <div className="text-5xl animate-bounce">🏆</div>
            <h3 className="text-lg font-black text-foreground">
              Quest Complete! Achievement Unlocked!
            </h3>
            <div className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 px-3 py-1 text-xs font-bold text-emerald-700 dark:text-emerald-300">
              <M3Check size={16} />
              <span>Master Facility Architect • +{totalXp} XP</span>
            </div>
            <p className="text-xs text-muted-foreground max-w-sm mx-auto leading-relaxed">
              You've completed the walkthrough! You now know exactly what every option does, when to use it, and how to calibrate your indoor tracking space like a pro.
            </p>
            <div className="pt-2 flex items-center justify-center gap-3">
              <button
                type="button"
                onClick={handleRestart}
                className="rounded-xl border border-border/60 bg-muted/40 hover:bg-muted px-4 py-2 text-xs font-semibold text-foreground transition-all cursor-pointer"
              >
                ↺ Replay Tour
              </button>
              <button
                type="button"
                onClick={onClose}
                className="rounded-xl bg-teal-600 hover:bg-teal-700 text-white px-5 py-2 text-xs font-bold shadow-sm transition-all cursor-pointer"
              >
                Let's Track! 🚀
              </button>
            </div>
          </div>
        ) : (
          /* Active Quest Step Content */
          <>
            {/* Step Option Title & Badge */}
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <span className="text-2xl p-1.5 rounded-xl bg-teal-500/10 border border-teal-500/20">
                  {currentStep.icon}
                </span>
                <div>
                  <div className="text-sm font-bold text-foreground leading-tight">
                    {currentStep.optionName}
                  </div>
                  <div className="text-[11px] text-muted-foreground font-mono">
                    Mission {currentStepIndex + 1} of {totalSteps}
                  </div>
                </div>
              </div>

              <span
                className={`rounded-full border px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wider shrink-0 ${getBadgeStyle(
                  currentStep.badge.type
                )}`}
              >
                {currentStep.badge.label}
              </span>
            </div>

            {/* SECTION 1: WHAT IT DOES */}
            <div className="rounded-2xl bg-muted/30 border border-border/40 p-3.5 space-y-1.5">
              <div className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <span>💡</span>
                <span>What this option does:</span>
              </div>
              <p className="text-xs text-foreground/90 leading-relaxed font-medium">
                {currentStep.whatItDoes}
              </p>
            </div>

            {/* SECTION 2: SHOULD YOU USE IT? */}
            <div className="rounded-2xl bg-teal-500/5 border border-teal-500/30 p-3.5 space-y-2">
              <div className="flex items-center justify-between">
                <div className="text-[11px] font-bold uppercase tracking-wider text-teal-700 dark:text-teal-300 flex items-center gap-1.5">
                  <span>🤔</span>
                  <span>Should you use it?</span>
                </div>
              </div>

              <div className="text-xs font-bold text-foreground">
                {currentStep.shouldYouUseIt.verdict}
              </div>

              <div className="space-y-1.5 pt-1 border-t border-teal-500/15 text-xs">
                <div className="flex items-start gap-2 text-foreground/90">
                  <span className="text-emerald-500 font-bold shrink-0">✔️</span>
                  <span>
                    <strong>Use if:</strong> {currentStep.shouldYouUseIt.useIf}
                  </span>
                </div>
                <div className="flex items-start gap-2 text-foreground/90">
                  <span className="text-rose-500 font-bold shrink-0">❌</span>
                  <span>
                    <strong>Skip if:</strong> {currentStep.shouldYouUseIt.skipIf}
                  </span>
                </div>
              </div>
            </div>

            {/* SECTION 3: PRO GAMER TIP */}
            <div className="rounded-2xl bg-amber-500/10 border border-amber-500/25 p-3 flex items-start gap-2 text-xs">
              <span className="text-base shrink-0">🎯</span>
              <p className="text-muted-foreground text-[11px] leading-relaxed">
                <strong className="text-foreground font-semibold">Strategy Tip: </strong>
                {currentStep.proTip}
              </p>
            </div>
          </>
        )}
      </div>

      {/* Stepper Controls Footer */}
      {!isCompleted && (
        <div className="flex items-center justify-between border-t border-border/40 bg-muted/20 px-5 py-3 rounded-b-3xl">
          <button
            type="button"
            onClick={handlePrev}
            disabled={currentStepIndex === 0}
            className="flex items-center gap-1 rounded-xl px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground hover:bg-muted/50 disabled:opacity-30 disabled:pointer-events-none transition-all cursor-pointer"
          >
            <M3ChevronLeft size={16} />
            <span>Previous</span>
          </button>

          {/* Step Dots */}
          <div className="flex items-center gap-1.5">
            {steps.map((_, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setCurrentStepIndex(idx)}
                className={`h-2 rounded-full transition-all cursor-pointer ${
                  idx === currentStepIndex
                    ? 'w-5 bg-teal-500'
                    : idx < currentStepIndex
                    ? 'w-2 bg-teal-500/50'
                    : 'w-2 bg-muted-foreground/30'
                }`}
                title={`Jump to Quest ${idx + 1}`}
              />
            ))}
          </div>

          <button
            type="button"
            onClick={handleNext}
            className="flex items-center gap-1.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white px-4 py-1.5 text-xs font-bold shadow-sm transition-all cursor-pointer"
          >
            <span>{currentStepIndex === totalSteps - 1 ? 'Finish Quest 🎉' : 'Next Mission'}</span>
            <M3ChevronRight size={16} />
          </button>
        </div>
      )}
    </aside>
  )
}
