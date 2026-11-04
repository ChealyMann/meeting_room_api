import { describe, expect, it, vi, type Mock } from 'vitest'

import { adminReject, listBookingPage } from '../bookings'
import { createApiClient } from '../client'

const BASE = 'http://localhost:8000'
type FetchMock = Mock<typeof fetch>

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}
const answer = (body: unknown) => vi.fn<typeof fetch>(async () => json(body))
const client = (fetchImpl: FetchMock) =>
  createApiClient({ baseUrl: BASE, getAccessToken: () => 'A', refresh: async () => false, onAuthLost: () => {}, fetchImpl })

describe('bookings API', () => {
  it('lists all bookings with the given filters', async () => {
    const fetchMock = answer({ items: [], page: 1, size: 20, total: 0 })

    await listBookingPage(client(fetchMock), {
      status: 'CONFIRMED',
      province: 'SIEM_REAP',
      from: '2026-11-01',
      to: '2026-11-30',
      q: 'NBC-26',
      page: 1,
      size: 20,
    })

    expect(String(fetchMock.mock.calls[0]![0])).toBe(
      `${BASE}/api/v1/bookings?status=CONFIRMED&province=SIEM_REAP&from=2026-11-01&to=2026-11-30&q=NBC-26&page=1&size=20`,
    )
  })
})

describe('Admin booking actions API', () => {
  it('rejects with exactly the given body', async () => {
    const fetchMock = answer({ id: 12 })

    await adminReject(client(fetchMock), 12, { reason: null, version: 3 })

    const call = fetchMock.mock.calls[0]!
    expect([call[1]?.method, String(call[0]), call[1]?.body]).toEqual([
      'POST',
      `${BASE}/api/v1/admin/bookings/12/reject`,
      JSON.stringify({ reason: null, version: 3 }),
    ])
  })
})
