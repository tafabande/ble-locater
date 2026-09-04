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

export function M3Collector({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <circle cx="12" cy="12" r="3" />
      <path d="M5.64 5.64a9 9 0 0 0 0 12.72M18.36 5.64a9 9 0 0 1 0 12.72M8.46 8.46a5 5 0 0 0 0 7.08M15.54 8.46a5 5 0 0 1 0 7.08" />
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

export function M3Layers({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <polygon points="12 2 2 7 12 12 22 7 12 2" />
      <polyline points="2 17 12 22 22 17" />
      <polyline points="2 12 12 17 22 12" />
    </svg>
  )
}

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

export function M3Trash({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      <line x1="10" y1="11" x2="10" y2="17" />
      <line x1="14" y1="11" x2="14" y2="17" />
    </svg>
  )
}

export function M3Pointer({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <path d="M3 3l7 18 3-7 7-3L3 3z" />
    </svg>
  )
}

export function M3CropSquare({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <rect x="3" y="3" width="18" height="18" rx="2" />
    </svg>
  )
}

export function M3Beacon({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <circle cx="12" cy="12" r="2" />
      <path d="M16.24 7.76a6 6 0 0 1 0 8.49M7.76 16.24a6 6 0 0 1 0-8.49" />
      <path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 19.07a10 10 0 0 1 0-14.14" />
    </svg>
  )
}

export function M3Wall({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <rect x="3" y="4" width="18" height="16" rx="1" />
      <line x1="3" y1="12" x2="21" y2="12" />
      <line x1="9" y1="4" x2="9" y2="12" />
      <line x1="15" y1="4" x2="15" y2="12" />
      <line x1="6" y1="12" x2="6" y2="20" />
      <line x1="12" y1="12" x2="12" y2="20" />
      <line x1="18" y1="12" x2="18" y2="20" />
    </svg>
  )
}

export function M3Door({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <path d="M4 21V3a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v18M2 21h20" />
      <rect x="7" y="6" width="10" height="15" />
      <circle cx="14" cy="13" r="1" fill="currentColor" />
    </svg>
  )
}

export function M3Sparkles({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <path d="M12 2l2.4 5.6L20 10l-5.6 2.4L12 18l-2.4-5.6L4 10l5.6-2.4L12 2z" />
      <path d="M19 15l1.2 2.8L23 19l-2.8 1.2L19 23l-1.2-2.8L15 19l2.8-1.2L19 15z" />
    </svg>
  )
}

export function M3Building({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <rect x="4" y="2" width="16" height="20" rx="2" />
      <line x1="9" y1="6" x2="9" y2="6.01" strokeWidth={2.5} />
      <line x1="15" y1="6" x2="15" y2="6.01" strokeWidth={2.5} />
      <line x1="9" y1="10" x2="9" y2="10.01" strokeWidth={2.5} />
      <line x1="15" y1="10" x2="15" y2="10.01" strokeWidth={2.5} />
      <line x1="9" y1="14" x2="9" y2="14.01" strokeWidth={2.5} />
      <line x1="15" y1="14" x2="15" y2="14.01" strokeWidth={2.5} />
      <path d="M10 22v-4h4v4" />
    </svg>
  )
}

export function M3Business({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <rect x="3" y="7" width="18" height="14" rx="2" />
      <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
    </svg>
  )
}

export function M3Lightbulb({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <path d="M9 18h6M10 22h4M15 10a4 4 0 1 0-7 2.6V15a1 1 0 0 0 1 1h4a1 1 0 0 0 1-1v-2.4c1.2-.7 2-2 2-3.6z" />
    </svg>
  )
}

export function M3Walk({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <circle cx="13" cy="4" r="2" />
      <path d="M7 21l3-7 3 2v6" />
      <path d="M6 12l4-2 3 4 4-2" />
    </svg>
  )
}

export function M3Settings({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  )
}

export function M3BarChart({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <line x1="18" y1="20" x2="18" y2="10" strokeWidth={2} />
      <line x1="12" y1="20" x2="12" y2="4" strokeWidth={2} />
      <line x1="6" y1="20" x2="6" y2="14" strokeWidth={2} />
    </svg>
  )
}

export function M3Ruler({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <path d="M21.17 8.01L15.99 2.83a2 2 0 0 0-2.83 0L2.83 13.16a2 2 0 0 0 0 2.83l5.18 5.18a2 2 0 0 0 2.83 0l10.33-10.33a2 2 0 0 0 0-2.83z" />
      <line x1="7.07" y1="14.57" x2="9.9" y2="17.4" />
      <line x1="9.9" y1="11.74" x2="14.14" y2="15.98" />
      <line x1="12.73" y1="8.91" x2="15.56" y2="11.74" />
      <line x1="15.56" y1="6.09" x2="19.8" y2="10.33" />
    </svg>
  )
}

export function M3Trophy({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <path d="M6 9H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h2" />
      <path d="M18 9h2a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2h-2" />
      <path d="M4 22h16M12 15v7M8 4h8v7a4 4 0 0 1-8 0V4z" />
    </svg>
  )
}

export function M3Bolt({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  )
}

export function M3Clipboard({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
      <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
    </svg>
  )
}

export function M3Pin({ size = 20, className = '', ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} className={className} {...props}>
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  )
}




