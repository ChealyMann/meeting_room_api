export interface Nav {
  name: string
  fullPath: string
  /** `roles`: who may open the page; none means every dashboard role (e.g. My profile). */
  meta: { public?: boolean; roles?: string[] }
}

export interface SessionState {
  signedIn: boolean
  mustChangePassword: boolean
  /** The user's role codes, as `GET /me` sends them. */
  roles: string[]
}

export type NavResult = true | { name: string; query?: Record<string, string> }

/** The roles that may use the dashboard. The others (Staff, …) see "No access". */
export const DASHBOARD_ROLES = ['ADMIN', 'PITIKA']

/** Where a user lands: Rooms for an Admin, To review for a Pitika, else No access. */
export function homeFor(roles: string[]): string {
  if (roles.includes('ADMIN')) return 'home'
  if (roles.includes('PITIKA')) return 'review'
  return 'no-access'
}

/** Where a navigation may go. Order matters: sign-in, then new password, then the roles. */
export function resolveNavigation(to: Nav, s: SessionState): NavResult {
  if (!s.signedIn) {
    return to.meta.public ? true : { name: 'sign-in', query: { redirect: to.fullPath } }
  }
  if (s.mustChangePassword) {
    return to.name === 'change-password' ? true : { name: 'change-password' }
  }
  const home = homeFor(s.roles)
  if (home === 'no-access') {
    return to.name === 'no-access' ? true : { name: 'no-access' }
  }
  if (to.name === 'sign-in' || to.name === 'no-access') return { name: home }
  // A page for other roles (an Admin list for a Pitika, the Pitika queue for an Admin).
  if (to.meta.roles && !to.meta.roles.some((role) => s.roles.includes(role))) return { name: home }
  return true
}
