import { useState, useRef, useEffect, type ReactNode } from 'react'

export interface DropdownMenuItem {
  id?: string
  label: string
  icon?: ReactNode
  badge?: ReactNode
  disabled?: boolean
  danger?: boolean
  onClick?: () => void
  subItems?: DropdownMenuItem[]
}

interface Props {
  trigger: ReactNode | ((isOpen: boolean) => ReactNode)
  items?: DropdownMenuItem[]
  align?: 'left' | 'right'
  className?: string
  children?: ReactNode | ((close: () => void) => ReactNode)
}

export function CollectorDropdown({
  trigger,
  items,
  align = 'right',
  className = '',
  children,
}: Props) {
  const [isOpen, setIsOpen] = useState(false)
  const [activeSubmenu, setActiveSubmenu] = useState<string | null>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false)
        setActiveSubmenu(null)
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  const close = () => {
    setIsOpen(false)
    setActiveSubmenu(null)
  }

  return (
    <div ref={menuRef} className={`relative inline-block text-left ${className}`}>
      <div onClick={() => setIsOpen(!isOpen)} className="cursor-pointer">
        {typeof trigger === 'function' ? trigger(isOpen) : trigger}
      </div>

      {isOpen && (
        <div
          className={`absolute ${
            align === 'right' ? 'right-0' : 'left-0'
          } mt-2 min-w-56 rounded-2xl bg-card p-1.5 shadow-xl border border-border/60 z-50 animate-in fade-in zoom-in-95 duration-100 backdrop-blur-md`}
        >
          {items && items.length > 0 && (
            <div className="space-y-0.5">
              {items.map((item, idx) => {
                const hasSub = item.subItems && item.subItems.length > 0
                const isSubOpen = activeSubmenu === (item.id || item.label)

                return (
                  <div
                    key={item.id || idx}
                    className="relative"
                    onMouseEnter={() => hasSub && setActiveSubmenu(item.id || item.label)}
                    onMouseLeave={() => hasSub && setActiveSubmenu(null)}
                  >
                    <button
                      type="button"
                      disabled={item.disabled}
                      onClick={() => {
                        if (!hasSub && item.onClick) {
                          item.onClick()
                          close()
                        }
                      }}
                      className={`w-full flex items-center justify-between gap-2 px-3 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer select-none ${
                        item.danger
                          ? 'text-rose-600 hover:bg-rose-500/10'
                          : item.disabled
                          ? 'opacity-40 cursor-not-allowed text-muted-foreground'
                          : 'text-foreground hover:bg-muted/80'
                      }`}
                    >
                      <span className="flex items-center gap-2">
                        {item.icon && <span className="opacity-80">{item.icon}</span>}
                        <span>{item.label}</span>
                      </span>

                      <span className="flex items-center gap-1">
                        {item.badge && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-md bg-muted">
                            {item.badge}
                          </span>
                        )}
                        {hasSub && (
                          <svg
                            width="12"
                            height="12"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            className="opacity-60"
                          >
                            <polyline points="9 18 15 12 9 6" />
                          </svg>
                        )}
                      </span>
                    </button>

                    {/* Cascading Submenu */}
                    {hasSub && isSubOpen && (
                      <div
                        className={`absolute top-0 ${
                          align === 'right' ? 'right-full mr-1.5' : 'left-full ml-1.5'
                        } min-w-48 rounded-2xl bg-card p-1.5 shadow-2xl border border-border/60 z-50 animate-in fade-in zoom-in-95 duration-100`}
                      >
                        <div className="space-y-0.5">
                          {item.subItems!.map((sub, sIdx) => (
                            <button
                              key={sub.id || sIdx}
                              type="button"
                              disabled={sub.disabled}
                              onClick={() => {
                                if (sub.onClick) {
                                  sub.onClick()
                                  close()
                                }
                              }}
                              className="w-full flex items-center justify-between gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-foreground hover:bg-muted/80 transition-all cursor-pointer select-none"
                            >
                              <span className="flex items-center gap-2">
                                {sub.icon && <span className="opacity-80">{sub.icon}</span>}
                                <span>{sub.label}</span>
                              </span>
                              {sub.badge && (
                                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-md bg-muted">
                                  {sub.badge}
                                </span>
                              )}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {/* Custom Popover Content */}
          {children && (
            <div className="p-1">
              {typeof children === 'function' ? children(close) : children}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
