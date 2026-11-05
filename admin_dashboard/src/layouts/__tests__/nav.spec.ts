import { describe, expect, it } from 'vitest'

import { NAV_ICONS, navFor } from '../nav'

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

  it('gives anyone else nothing', () => {
    expect(navFor(['STAFF'])).toEqual([])
  })
})
