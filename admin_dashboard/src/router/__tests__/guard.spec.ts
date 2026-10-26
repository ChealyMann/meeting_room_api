import { describe, expect, it } from 'vitest'

import { resolveNavigation, type Nav } from '../guard'

const nav = (name: string, fullPath: string, isPublic = false): Nav => ({
  name,
  fullPath,
  meta: isPublic ? { public: true } : {},
})

const HOME = nav('home', '/')
const PROFILE = nav('profile', '/profile')
const SIGN_IN = nav('sign-in', '/sign-in', true)
const CHANGE = nav('change-password', '/change-password')
const NO_ACCESS = nav('no-access', '/no-access')

const signedOut = { signedIn: false, mustChangePassword: false, isAdmin: false }
const mustChange = { signedIn: true, mustChangePassword: true, isAdmin: true }
const staff = { signedIn: true, mustChangePassword: false, isAdmin: false }
const admin = { signedIn: true, mustChangePassword: false, isAdmin: true }

describe('resolveNavigation', () => {
  it('sends a signed-out user to sign-in and remembers the page', () => {
    expect(resolveNavigation(HOME, signedOut)).toEqual({ name: 'sign-in', query: { redirect: '/' } })
    expect(resolveNavigation(PROFILE, signedOut)).toEqual({
      name: 'sign-in',
      query: { redirect: '/profile' },
    })
  })

  it('lets a signed-out user open public pages', () => {
    expect(resolveNavigation(SIGN_IN, signedOut)).toBe(true)
  })

  it('opens only the password page until the password is changed', () => {
    expect(resolveNavigation(PROFILE, mustChange)).toEqual({ name: 'change-password' })
    expect(resolveNavigation(HOME, mustChange)).toEqual({ name: 'change-password' })
    expect(resolveNavigation(SIGN_IN, mustChange)).toEqual({ name: 'change-password' })
    expect(resolveNavigation(CHANGE, mustChange)).toBe(true)
  })

  it('checks the password before the Admin role', () => {
    expect(resolveNavigation(HOME, { ...mustChange, isAdmin: false })).toEqual({
      name: 'change-password',
    })
  })

  it('sends a user without the Admin role to no-access', () => {
    expect(resolveNavigation(HOME, staff)).toEqual({ name: 'no-access' })
    expect(resolveNavigation(SIGN_IN, staff)).toEqual({ name: 'no-access' })
    expect(resolveNavigation(NO_ACCESS, staff)).toBe(true)
  })

  it('sends a signed-in admin away from sign-in and no-access', () => {
    expect(resolveNavigation(SIGN_IN, admin)).toEqual({ name: 'home' })
    expect(resolveNavigation(NO_ACCESS, admin)).toEqual({ name: 'home' })
  })

  it('lets an admin open app pages', () => {
    expect(resolveNavigation(PROFILE, admin)).toBe(true)
    expect(resolveNavigation(HOME, admin)).toBe(true)
    expect(resolveNavigation(CHANGE, admin)).toBe(true)
  })
})
