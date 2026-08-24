import type { SVGProps } from 'react'

export interface IconProps extends SVGProps<SVGSVGElement> {
  size?: number
  className?: string
}

const defaultProps = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
}

// ═══════════════════════════════════════════════════════════════════
// MATERIAL DESIGN 3 NAVIGATION & SHELL ICONS
// ═══════════════════════════════════════════════════════════════════

export function M3Monitor({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <rect x="2" y="3" width="20" height="14" rx="2" />
      <path d="M8 21h8M12 17v4" />
      <circle cx="12" cy="10" r="2.5" />
    </svg>
  )
}

export function M3Operations({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

export function M3Training({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2z" />
      <path d="M12 6v6l4 2" />
      <path d="M16 4.5l3.5 3.5" />
    </svg>
  )
}

export function M3Reports({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
    </svg>
  )
}

export function M3Admin({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

// ═══════════════════════════════════════════════════════════════════
// MATERIAL DESIGN 3 ALERTS & STATUS ICONS
// ═══════════════════════════════════════════════════════════════════

export function M3Error({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 8v4M12 16h.01" strokeWidth={2.2} />
    </svg>
  )
}

export function M3Warning({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <path d="M12 9v4M12 17h.01" strokeWidth={2.2} />
    </svg>
  )
}

export function M3Info({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4M12 8h.01" strokeWidth={2.2} />
    </svg>
  )
}

export function M3CheckCircle({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <circle cx="12" cy="12" r="10" />
      <path d="M9 12l2 2 4-4" strokeWidth={2} />
    </svg>
  )
}

export function M3Bell({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  )
}

export function M3ShieldAlert({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="M12 8v4M12 16h.01" strokeWidth={2.2} />
    </svg>
  )
}

export function M3Battery({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <rect x="2" y="7" width="16" height="10" rx="2" />
      <path d="M22 11v2" strokeWidth={2} />
    </svg>
  )
}

// ═══════════════════════════════════════════════════════════════════
// MATERIAL DESIGN 3 ACTIONS & UTILITY ICONS
// ═══════════════════════════════════════════════════════════════════

export function M3Search({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.35-4.35" strokeWidth={2} />
    </svg>
  )
}

export function M3Filter({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
    </svg>
  )
}

export function M3Refresh({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <path d="M21.5 2v6h-6M2.5 22v-6h6" />
      <path d="M20 11.5a8.38 8.38 0 0 0-.9-3.8 8.5 8.5 0 0 0-7.6-4.7 8.38 8.38 0 0 0-3.8.9L2.5 7.5M4 12.5a8.38 8.38 0 0 0 .9 3.8 8.5 8.5 0 0 0 7.6 4.7 8.38 8.38 0 0 0 3.8-.9l5.2-3.6" />
    </svg>
  )
}

export function M3Upload({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
    </svg>
  )
}

export function M3Download({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
    </svg>
  )
}

export function M3Deploy({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.71.79-1.81.2-2.7l-2.48-2.48c-.89-.59-1.99-.51-2.72.18z" />
      <path d="M12 15l-3-3 7.5-7.5a2.12 2.12 0 0 1 3 3L12 15z" />
      <path d="M9 18l3 3" />
    </svg>
  )
}

export function M3Grid({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
    </svg>
  )
}

export function M3Tag({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
      <line x1="7" y1="7" x2="7.01" y2="7" strokeWidth={2.2} />
    </svg>
  )
}

export function M3Anchor({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <circle cx="12" cy="5" r="3" />
      <line x1="12" y1="8" x2="12" y2="21" strokeWidth={2} />
      <path d="M5 12H2a10 10 0 0 0 20 0h-3" />
    </svg>
  )
}

export function M3Close({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <line x1="18" y1="6" x2="6" y2="18" strokeWidth={2} />
      <line x1="6" y1="6" x2="18" y2="18" strokeWidth={2} />
    </svg>
  )
}

export function M3Check({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <polyline points="20 6 9 17 4 12" strokeWidth={2} />
    </svg>
  )
}

export function M3Play({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <polygon points="5 3 19 12 5 21 5 3" />
    </svg>
  )
}

export function M3Stop({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <rect x="5" y="5" width="14" height="14" rx="2" />
    </svg>
  )
}
