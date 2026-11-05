import { describe, expect, it } from 'vitest'

import { homeFor, resolveNavigation, type Nav } from '../guard'

const nav = (name: string, fullPath: string, meta: Nav['meta'] = {}): Nav => ({ name, fullPath, meta })

const ADMIN_ONLY = ['ADMIN']
const HOME = nav('home', '/', { roles: ADMIN_ONLY })
const OFFICES = nav('offices', '/offices', { roles: ADMIN_ONLY })
const BOOKINGS = nav('bookings', '/bookings', { roles: ['ADMIN', 'PITIKA', 'ROOM_OWNER'] })
const OWNER_REVIEW = nav('owner-review', '/owner-review', { roles: ['ROOM_OWNER'] })
const REVIEW = nav('review', '/review', { roles: ['PITIKA'] })
const PROFILE = nav('profile', '/profile')
const SIGN_IN = nav('sign-in', '/sign-in', { public: true })
const CHANGE = nav('change-password', '/change-password')
const NO_ACCESS = nav('no-access', '/no-access')

const signedOut = { signedIn: false, mustChangePassword: false, roles: [] }
const mustChange = { signedIn: true, mustChangePassword: true, roles: ['ADMIN'] }
const staff = { signedIn: true, mustChangePassword: false, roles: ['STAFF'] }
const admin = { signedIn: true, mustChangePassword: false, roles: ['ADMIN'] }
const pitika = { signedIn: true, mustChangePassword: false, roles: ['PITIKA', 'STAFF'] }
const both = { signedIn: true, mustChangePassword: false, roles: ['ADMIN', 'PITIKA'] }
const owner = { signedIn: true, mustChangePassword: false, roles: ['ROOM_OWNER', 'STAFF'] }

describe('Room owner', () => {
  it('lands on the owner To review and may open Bookings', () => {
    expect(homeFor(['ROOM_OWNER'])).toBe('owner-review')
    expect(resolveNavigation(SIGN_IN, owner)).toEqual({ name: 'owner-review' })
    expect(resolveNavigation(OWNER_REVIEW, owner)).toBe(true)
    expect(resolveNavigation(BOOKINGS, owner)).toBe(true)
  })

  it('is sent home from Admin and Pitika pages', () => {
    expect(resolveNavigation(OFFICES, owner)).toEqual({ name: 'owner-review' })
    expect(resolveNavigation(REVIEW, owner)).toEqual({ name: 'owner-review' })
  })

  it('keeps the Pitika home for a Pitika who also owns a room', () => {
    expect(homeFor(['PITIKA', 'ROOM_OWNER'])).toBe('review')
    expect(homeFor(['STAFF'])).toBe('no-access')
  })
})

describe('resolveNavigation', () => {
  it('sends a signed-out user to sign-in and remembers the page', () => {
    expect(resolveNavigation(HOME, signedOut)).toEqual({ name: 'sign-in', query: { redirect: '/' } })
    expect(resolveNavigation(PROFILE, signedOut)).toEqual({ name: 'sign-in', query: { redirect: '/profile' } })
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

  it('checks the password before the roles', () => {
    expect(resolveNavigation(HOME, { ...mustChange, roles: ['STAFF'] })).toEqual({ name: 'change-password' })
  })

  it('sends a user with no dashboard role to no-access', () => {
    expect(resolveNavigation(HOME, staff)).toEqual({ name: 'no-access' })
    expect(resolveNavigation(SIGN_IN, staff)).toEqual({ name: 'no-access' })
    expect(resolveNavigation(NO_ACCESS, staff)).toBe(true)
  })

  it('sends a signed-in admin away from sign-in and no-access', () => {
    expect(resolveNavigation(SIGN_IN, admin)).toEqual({ name: 'home' })
    expect(resolveNavigation(NO_ACCESS, admin)).toEqual({ name: 'home' })
  })

  it('lets an admin open the Admin pages, but not the Pitika queue', () => {
    expect(resolveNavigation(PROFILE, admin)).toBe(true)
    expect(resolveNavigation(HOME, admin)).toBe(true)
    expect(resolveNavigation(CHANGE, admin)).toBe(true)
    expect(resolveNavigation(REVIEW, admin)).toEqual({ name: 'home' })
  })

  it('lets a Pitika open their pages and sends them home from Admin pages', () => {
    expect(resolveNavigation(REVIEW, pitika)).toBe(true)
    expect(resolveNavigation(BOOKINGS, pitika)).toBe(true)
    expect(resolveNavigation(PROFILE, pitika)).toBe(true)
    expect(resolveNavigation(OFFICES, pitika)).toEqual({ name: 'review' })
    expect(resolveNavigation(HOME, pitika)).toEqual({ name: 'review' })
    expect(resolveNavigation(SIGN_IN, pitika)).toEqual({ name: 'review' })
    expect(resolveNavigation(NO_ACCESS, pitika)).toEqual({ name: 'review' })
  })

  it('opens both sets of pages for an Admin who is also Pitika, home staying Rooms', () => {
    expect(resolveNavigation(HOME, both)).toBe(true)
    expect(resolveNavigation(REVIEW, both)).toBe(true)
    expect(resolveNavigation(SIGN_IN, both)).toEqual({ name: 'home' })
  })
})

describe('homeFor', () => {
  it('is Rooms for an Admin, To review for a Pitika, and no-access otherwise', () => {
    expect(homeFor(['ADMIN'])).toBe('home')
    expect(homeFor(['PITIKA'])).toBe('review')
    expect(homeFor(['PITIKA', 'ADMIN'])).toBe('home')
    expect(homeFor(['STAFF'])).toBe('no-access')
  })
})
