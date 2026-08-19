export type UserRole = 'viewer' | 'operator' | 'admin'

export const ROLE_LABELS: Record<UserRole, string> = {
  viewer: 'Viewer',
  operator: 'Operator',
  admin: 'Admin',
}

const ROLE_RANK: Record<UserRole, number> = {
  viewer: 0,
  operator: 1,
  admin: 2,
}

export function canAccess(role: UserRole, minimum: UserRole) {
  return ROLE_RANK[role] >= ROLE_RANK[minimum]
}

