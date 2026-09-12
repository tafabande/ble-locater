import { useState, type ReactNode } from 'react'

interface Props {
  title: string
  icon?: ReactNode
  badge?: ReactNode
  defaultOpen?: boolean
  isOpen?: boolean
  onToggle?: (open: boolean) => void
  action?: ReactNode
  className?: string
  children: ReactNode
}

export function CollectorCollapsible({
  title,
  icon,
  badge,
  defaultOpen = true,
  isOpen: controlledOpen,
  onToggle,
  action,
  className = '',
  children,
}: Props) {
  const [internalOpen, setInternalOpen] = useState(defaultOpen)
  const isExpanded = controlledOpen !== undefined ? controlledOpen : internalOpen

  const handleToggle = () => {
    const next = !isExpanded
    if (controlledOpen === undefined) {
      setInternalOpen(next)
    }
    onToggle?.(next)
  }

  return (
    <div
      className={`rounded-2xl bg-card shadow-sm border border-border/40 transition-all duration-200 ${
        isExpanded ? 'p-4' : 'px-4 py-3'
      } ${className}`}
    >
      <div className="flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={handleToggle}
          className="flex flex-1 items-center gap-2 text-left cursor-pointer select-none group"
          aria-expanded={isExpanded}
        >
          {icon && (
            <span className="text-teal-600 dark:text-teal-400 flex items-center justify-center">
              {icon}
            </span>
          )}
          <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground group-hover:text-foreground transition-colors flex items-center gap-1.5">
            {title}
            {badge && (
              <span className="normal-case tracking-normal">{badge}</span>
            )}
          </span>
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={`text-muted-foreground/60 group-hover:text-foreground transition-transform duration-200 ml-auto mr-1 ${
              isExpanded ? 'rotate-180' : 'rotate-0'
            }`}
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>

        {action && <div className="flex items-center gap-1">{action}</div>}
      </div>

      {isExpanded && <div className="mt-3 pt-2 border-t border-border/30 space-y-3">{children}</div>}
    </div>
  )
}
