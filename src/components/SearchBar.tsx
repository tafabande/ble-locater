import { useEffect, useMemo, useRef, useState } from 'react'
import { M3Search, M3Close } from './common/MaterialIcon'

export interface SearchItem {
  id: string
  label: string
  sub: string
  kind: 'tag' | 'anchor'
}

interface Props {
  items: SearchItem[]
  focus: string | null
  onFocus: (id: string | null) => void
}

export function SearchBar({ items, focus, onFocus }: Props) {
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const wrapRef = useRef<HTMLDivElement>(null)

  const focused = items.find((i) => i.id === focus)

  // Non-aggressive: only suggest once the user has actually typed something.
  const matches = useMemo(() => {
    const s = q.trim().toLowerCase()
    if (!s) return []
    return items
      .filter((i) => i.label.toLowerCase().includes(s) || i.id.toLowerCase().includes(s) || i.sub.toLowerCase().includes(s))
      .slice(0, 6)
  }, [q, items])

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  useEffect(() => setActive(0), [q])

  const choose = (id: string) => {
    onFocus(id)
    setOpen(false)
    setQ('')
  }

  const onKey = (e: React.KeyboardEvent) => {
    if (!open || matches.length === 0) return
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive((a) => (a + 1) % matches.length) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => (a - 1 + matches.length) % matches.length) }
    else if (e.key === 'Enter') { e.preventDefault(); choose(matches[active].id) }
    else if (e.key === 'Escape') setOpen(false)
  }

  // When something is isolated, show a pill instead of the input.
  if (focused) {
    return (
      <div className="flex items-center gap-2 rounded-full bg-accent-soft py-1 pl-3 pr-1 text-xs shadow-xs">
        <span className="font-mono text-[10px] uppercase tracking-wider text-accent">{focused.kind}</span>
        <span className="font-medium text-foreground">{focused.label}</span>
        <button
          onClick={() => onFocus(null)}
          aria-label="Clear focus"
          className="grid size-5 place-items-center rounded-full text-accent transition-colors hover:bg-accent hover:text-primary-foreground focus-visible:outline-2 focus-visible:outline-accent"
        >
          <M3Close size={12} />
        </button>
      </div>
    )
  }

  return (
    <div ref={wrapRef} className="relative w-44 sm:w-64">
      <div className="flex items-center gap-2 rounded-full border border-border/40 bg-card px-3.5 py-1.5 shadow-xs focus-within:ring-2 focus-within:ring-accent">
        <M3Search size={16} className="shrink-0 text-muted-foreground" />
        <input
          value={q}
          onChange={(e) => { setQ(e.target.value); setOpen(true) }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKey}
          placeholder="Search tag or anchor…"
          className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
        />
      </div>

      {open && matches.length > 0 && (
        <ul className="absolute right-0 z-30 mt-2 w-full min-w-[240px] overflow-hidden rounded-xl bg-card py-1 shadow-xl">
          {matches.map((m, i) => (
            <li key={`${m.kind}-${m.id}`}>
              <button
                onMouseEnter={() => setActive(i)}
                onClick={() => choose(m.id)}
                className={`flex w-full items-center gap-2.5 px-3 py-2 text-left transition-colors ${i === active ? 'bg-accent-soft' : ''}`}
              >
                <span
                  className="grid size-6 shrink-0 place-items-center rounded-md font-mono text-[10px] font-semibold"
                  style={{ background: 'var(--muted)', color: m.kind === 'tag' ? 'var(--accent)' : 'var(--foreground)' }}
                >
                  {m.kind === 'tag' ? 'T' : 'A'}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">{m.label}</span>
                  <span className="block truncate font-mono text-[10px] text-muted-foreground">{m.sub}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
