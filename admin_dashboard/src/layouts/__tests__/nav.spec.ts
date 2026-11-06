import { describe, expect, it } from 'vitest'

import { NAV_ICONS, navFor, navIcon, pageLabel, roleTitle } from '../nav'

const shape = (roles: string[]) =>
  navFor(roles).map((group) => ({ title: group.title, items: group.items.map((item) => item.route) }))

describe('navFor', () => {
  it("gives an Admin today's menu: Daily, then the four setup groups", () => {
    expect(shape(['ADMIN'])).toEqual([
      { title: 'Daily', items: ['bookings', 'food-list', 'home'] },
      { title: 'Places', items: ['offices', 'buildings', 'floors'] },
      { title: 'Catalog', items: ['room-types', 'equipment', 'catering-packages', 'it-services', 'public-holidays'] },
      { title: 'Organisation', items: ['departments', 'divisions', 'positions'] },
      { title: 'People', items: ['users', 'roles'] },
    ])
  })

  it('gives a Pitika only Daily: To review, Bookings, Food list', () => {
    expect(shape(['PITIKA', 'STAFF'])).toEqual([{ title: 'Daily', items: ['review', 'bookings', 'food-list'] }])
    const review = navFor(['PITIKA'])[0]!.items[0]!
    expect(review).toMatchObject({ label: 'To review', icon: 'inbox' })
    expect(NAV_ICONS[review.icon]).toBeDefined()
  })

  it('puts To review first for an Admin who is also Pitika', () => {
    expect(shape(['ADMIN', 'PITIKA'])[0]).toEqual({ title: 'Daily', items: ['review', 'bookings', 'food-list', 'home'] })
  })

  it('gives a Room owner To review and Bookings', () => {
    expect(shape(['ROOM_OWNER', 'STAFF'])).toEqual([{ title: 'Daily', items: ['owner-review', 'bookings'] }])
    expect(navFor(['ROOM_OWNER'])[0]!.items[0]).toMatchObject({ label: 'To review', icon: 'inbox' })
  })

  it('calls the owner page My rooms for a Pitika who also owns a room', () => {
    expect(shape(['PITIKA', 'ROOM_OWNER'])).toEqual([{ title: 'Daily', items: ['review', 'owner-review', 'bookings', 'food-list'] }])
    const mine = navFor(['PITIKA', 'ROOM_OWNER'])[0]!.items[1]!
    expect(mine).toMatchObject({ label: 'My rooms', icon: 'door-open' })
  })

  it('gives the IT Lead IT setup and IT Staff My tasks', () => {
    expect(shape(['IT_LEAD'])).toEqual([{ title: 'Daily', items: ['it-setup'] }])
    expect(shape(['IT_STAFF'])).toEqual([{ title: 'Daily', items: ['my-tasks'] }])
    expect(shape(['IT_LEAD', 'IT_STAFF'])).toEqual([{ title: 'Daily', items: ['it-setup', 'my-tasks'] }])
    for (const item of navFor(['IT_LEAD', 'IT_STAFF'])[0]!.items) expect(NAV_ICONS[item.icon]).toBeDefined()
  })

  it('gives anyone else nothing', () => {
    expect(navFor(['STAFF'])).toEqual([])
  })
})

describe('roleTitle', () => {
  it('names the first dashboard role the user has', () => {
    expect(roleTitle(['ADMIN', 'ROOM_OWNER'])).toBe('Admin')
    expect(roleTitle(['PITIKA', 'ROOM_OWNER'])).toBe('Pitika')
    expect(roleTitle(['ROOM_OWNER', 'STAFF'])).toBe('Room owner')
    expect(roleTitle(['IT_LEAD', 'IT_STAFF'])).toBe('IT Lead')
    expect(roleTitle(['IT_STAFF'])).toBe('IT Staff')
  })
})

describe('pageLabel and navIcon', () => {
  it('name the owner page My rooms for a Pitika who owns a room, everywhere', () => {
    expect(pageLabel('owner-review', ['PITIKA', 'ROOM_OWNER'])).toBe('My rooms')
    expect(pageLabel('owner-review', ['ROOM_OWNER'])).toBe('To review')
    expect(navIcon('owner-review', ['PITIKA', 'ROOM_OWNER'])).toBe(NAV_ICONS['door-open'])
    expect(navIcon('owner-review', ['ROOM_OWNER'])).toBe(NAV_ICONS.inbox)
  })

  it('know nothing of a page outside the menu', () => {
    expect(pageLabel('profile', ['ADMIN'])).toBeNull()
    expect(navIcon('profile', ['ADMIN'])).toBeUndefined()
  })
})
