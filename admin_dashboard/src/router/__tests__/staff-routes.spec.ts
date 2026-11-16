import { describe, expect, it } from 'vitest'

import router from '../index'

describe('Staff routes', () => {
  it('open a room and the booking by a numeric room id', () => {
    expect(router.resolve('/find-room').name).toBe('find-room')
    expect(router.resolve('/find-room/7')).toMatchObject({ name: 'staff-room', params: { roomId: '7' } })
    expect(router.resolve('/book/12')).toMatchObject({ name: 'book', params: { roomId: '12' } })
    expect(router.resolve('/my-bookings').name).toBe('my-bookings')
  })

  it('do not take a room id that is not a number', () => {
    expect(router.resolve('/book/abc').name).not.toBe('book')
    expect(router.resolve('/find-room/dd').name).not.toBe('staff-room')
  })
})
