import { describe, expect, it, vi, type Mock } from 'vitest'

import {
  adminReject,
  getOwnerSummary,
  getPitikaSummary,
  listBookingPage,
  listOwnerBookingPage,
  listOwnerDecidedPage,
  listPitikaDecidedPage,
  ownerApprove,
  ownerReject,
} from '../bookings'
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

describe('Pitika decided API', () => {
  it('lists my decisions with only the filters that are set', async () => {
    const fetchMock = answer({ items: [], page: 1, size: 20, total: 0 })

    await listPitikaDecidedPage(client(fetchMock), { decision: 'APPROVED', page: 1, size: 20 })
    await listPitikaDecidedPage(client(fetchMock), { decision: 'REJECTED', room_id: 4, q: 'board', page: 2, size: 20 })

    expect(String(fetchMock.mock.calls[0]![0])).toBe(`${BASE}/api/v1/pitika/bookings/decided?decision=APPROVED&page=1&size=20`)
    expect(String(fetchMock.mock.calls[1]![0])).toBe(
      `${BASE}/api/v1/pitika/bookings/decided?decision=REJECTED&room_id=4&q=board&page=2&size=20`,
    )
  })

  it('reads the summary', async () => {
    const fetchMock = answer({ waiting: 3, approved_today: 5, rejected_today: 1 })

    expect(await getPitikaSummary(client(fetchMock))).toEqual({ waiting: 3, approved_today: 5, rejected_today: 1 })
    expect(String(fetchMock.mock.calls[0]![0])).toBe(`${BASE}/api/v1/pitika/bookings/summary`)
  })
})

describe('Room owner API', () => {
  it('lists my rooms without a province, with dates', async () => {
    const fetchMock = answer({ items: [], page: 1, size: 20, total: 0 })

    await listOwnerBookingPage(client(fetchMock), { status: 'PENDING_OWNER', province: 'PP', from: '2026-11-05', page: 1, size: 100 })

    expect(String(fetchMock.mock.calls[0]![0])).toBe(`${BASE}/api/v1/owner/bookings?status=PENDING_OWNER&from=2026-11-05&page=1&size=100`)
  })

  it('approves and rejects with exactly the given body', async () => {
    const fetchMock = answer({ id: 12 })

    await ownerApprove(client(fetchMock), 12, { notes: null, version: 3 })
    await ownerReject(client(fetchMock), 12, { reason: 'Room closed', version: 3 })

    const sent = fetchMock.mock.calls.map((c) => [c[1]?.method, String(c[0]), c[1]?.body])
    expect(sent).toEqual([
      ['POST', `${BASE}/api/v1/owner/bookings/12/approve`, JSON.stringify({ notes: null, version: 3 })],
      ['POST', `${BASE}/api/v1/owner/bookings/12/reject`, JSON.stringify({ reason: 'Room closed', version: 3 })],
    ])
  })

  it('lists my decisions and reads my summary', async () => {
    const fetchMock = answer({ items: [], page: 1, size: 20, total: 0 })

    await listOwnerDecidedPage(client(fetchMock), { decision: 'REJECTED', page: 1, size: 20 })
    await getOwnerSummary(client(fetchMock))

    expect(fetchMock.mock.calls.map((c) => String(c[0]))).toEqual([
      `${BASE}/api/v1/owner/bookings/decided?decision=REJECTED&page=1&size=20`,
      `${BASE}/api/v1/owner/bookings/summary`,
    ])
  })
})
