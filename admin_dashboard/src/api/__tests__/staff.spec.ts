import { describe, expect, it, vi, type Mock } from 'vitest'

import { createApiClient } from '../client'
import {
  cancelMyBooking,
  checkBooking,
  getDaySchedule,
  listActiveServices,
  listBookableRooms,
  listHolidays,
  listMyBookings,
  sendBooking,
} from '../staff'

const BASE = 'http://localhost:8000'
type FetchMock = Mock<typeof fetch>

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}
const answer = (body: unknown) => vi.fn<typeof fetch>(async () => json(body))
const client = (fetchImpl: FetchMock) =>
  createApiClient({ baseUrl: BASE, getAccessToken: () => 'A', refresh: async () => false, onAuthLost: () => {}, fetchImpl })
const urlOf = (m: FetchMock, n = 0) => String(m.mock.calls[n]![0])
const initOf = (m: FetchMock, n = 0) => m.mock.calls[n]![1]!
const bodyOf = (m: FetchMock, n = 0) => JSON.parse(String(initOf(m, n).body))

const PAGE = { items: [], page: 1, size: 100, total: 0 }

describe('Staff API', () => {
  it('lists bookable rooms with the filters', async () => {
    const m = answer(PAGE)
    await listBookableRooms(client(m), { q: 'mekong', is_private: false, page: 1, size: 100 })
    expect(urlOf(m)).toBe(`${BASE}/api/v1/rooms?is_bookable=true&search=mekong&is_private=false&page=1&size=100`)
  })

  it('asks every room for one day in one request', async () => {
    const m = answer({ items: [], total: 0 })
    await getDaySchedule(client(m), '2026-11-13', [3, 5])
    expect(urlOf(m)).toBe(`${BASE}/api/v1/room-schedule?date=2026-11-13&room_ids=3%2C5`)
  })

  it('lists active food packages and IT services in one page of 100', async () => {
    const m = answer({ ...PAGE, items: [{ id: 1 }] })
    const items = await listActiveServices(client(m), 'catering')
    expect(urlOf(m)).toBe(`${BASE}/api/v1/catering-packages?page=1&size=100`)
    expect(items).toEqual([{ id: 1 }])
    const n = answer(PAGE)
    await listActiveServices(client(n), 'it')
    expect(urlOf(n)).toBe(`${BASE}/api/v1/it-services?page=1&size=100`)
  })

  it('lists holidays between two days, asking each year once', async () => {
    const m = vi.fn<typeof fetch>(async (input) =>
      String(input).includes('year=2026')
        ? json({ ...PAGE, items: [{ id: 1, holiday_date: '2026-11-09' }, { id: 2, holiday_date: '2026-12-29' }] })
        : json({ ...PAGE, items: [{ id: 3, holiday_date: '2027-01-01' }, { id: 4, holiday_date: '2027-04-14' }] }),
    )
    const items = await listHolidays(client(m), '2026-11-12', '2027-01-05')
    expect(m.mock.calls.map((call) => String(call[0]))).toEqual([
      `${BASE}/api/v1/public-holidays?year=2026&page=1&size=100`,
      `${BASE}/api/v1/public-holidays?year=2027&page=1&size=100`,
    ])
    expect(items.map((h) => h.id)).toEqual([2, 3])
  })

  it('checks and sends a booking with the body unchanged', async () => {
    const body = {
      room_id: 12,
      sessions: [{ date: '2026-11-13', start_time: '09:00', end_time: '10:00' }],
      meeting_title: 'Budget review',
      meeting_type: 'INTERNAL' as const,
      attendees: 8,
    }
    const c = answer({ route: 'R1', first_status: 'PENDING_PITIKA', steps: ['PITIKA', 'CONFIRMED'], problem: null, warnings: [] })
    await checkBooking(client(c), { room_id: 12, sessions: body.sessions, has_catering: false, has_it: false })
    expect([initOf(c).method, urlOf(c)]).toEqual(['POST', `${BASE}/api/v1/bookings/check`])
    const s = answer({ id: 9 })
    await sendBooking(client(s), body)
    expect([initOf(s).method, urlOf(s)]).toEqual(['POST', `${BASE}/api/v1/bookings`])
    expect(bodyOf(s)).toEqual(body)
  })

  it('lists my bookings', async () => {
    const m = answer(PAGE)
    await listMyBookings(client(m), { page: 2, size: 50 })
    expect(urlOf(m)).toBe(`${BASE}/api/v1/bookings/mine?page=2&size=50`)
  })

  it('cancels with the version, and a reason only when given', async () => {
    const m = answer({ id: 9 })
    await cancelMyBooking(client(m), 9, 4)
    expect([initOf(m).method, urlOf(m)]).toEqual(['POST', `${BASE}/api/v1/bookings/9/cancel`])
    expect(bodyOf(m)).toEqual({ version: 4 })
    await cancelMyBooking(client(m), 9, 5, 'Plans changed')
    expect(bodyOf(m, 1)).toEqual({ version: 5, reason: 'Plans changed' })
  })
})
