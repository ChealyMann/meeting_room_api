export interface Nav {
  name: string
  fullPath: string
  meta: { public?: boolean }
}

export interface SessionState {
  signedIn: boolean
  mustChangePassword: boolean
  isAdmin: boolean
}

export type NavResult = true | { name: string; query?: Record<string, string> }

/** Where a navigation may go. Order matters: sign-in, then new password, then the Admin role. */
export function resolveNavigation(to: Nav, s: SessionState): NavResult {
  if (!s.signedIn) {
    return to.meta.public ? true : { name: 'sign-in', query: { redirect: to.fullPath } }
  }
  if (s.mustChangePassword) {
    return to.name === 'change-password' ? true : { name: 'change-password' }
  }
  if (!s.isAdmin) {
    return to.name === 'no-access' ? true : { name: 'no-access' }
  }
  if (to.name === 'sign-in' || to.name === 'no-access') return { name: 'home' }
  return true
}
