import { describe, expect, it, vi, type Mock } from 'vitest'

import { createApiClient } from '../client'
import { assignStaff, getItSummary, listItStaff, listTicketPage, markReady } from '../it'

const BASE = 'http://localhost:8000'
type FetchMock = Mock<typeof fetch>
const answer = (body: unknown) =>
  vi.fn<typeof fetch>(async () => new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } }))
const client = (fetchImpl: FetchMock) =>
  createApiClient({ baseUrl: BASE, getAccessToken: () => 'A', refresh: async () => false, onAuthLost: () => {}, fetchImpl })

describe('IT API', () => {
  it('lists tickets of a tab with only the filters that are set', async () => {
    const fetchMock = answer({ items: [], page: 1, size: 100, total: 0 })

    await listTicketPage(client(fetchMock), { state: 'to_assign', page: 1, size: 100 })
    await listTicketPage(client(fetchMock), { state: 'done', from: '2026-11-05', q: 'audit', page: 2, size: 20 })

    expect(fetchMock.mock.calls.map((c) => String(c[0]))).toEqual([
      `${BASE}/api/v1/it/tickets?state=to_assign&page=1&size=100`,
      `${BASE}/api/v1/it/tickets?state=done&from=2026-11-05&q=audit&page=2&size=20`,
    ])
  })

  it('reads the summary and the IT Staff', async () => {
    const fetchMock = answer({ items: [], total: 0 })

    await getItSummary(client(fetchMock))
    await listItStaff(client(fetchMock))

    expect(fetchMock.mock.calls.map((c) => String(c[0]))).toEqual([`${BASE}/api/v1/it/tickets/summary`, `${BASE}/api/v1/it/staff`])
  })

  it('assigns staff and marks ready with exactly the given body', async () => {
    const fetchMock = answer({ id: 5 })

    await assignStaff(client(fetchMock), 5, { user_ids: [31, 32], technician_notes: null, version: 1 })
    await markReady(client(fetchMock), 5, { version: 2 })

    expect(fetchMock.mock.calls.map((c) => [c[1]?.method, String(c[0]), c[1]?.body])).toEqual([
      ['PUT', `${BASE}/api/v1/it/tickets/5/staff`, JSON.stringify({ user_ids: [31, 32], technician_notes: null, version: 1 })],
      ['POST', `${BASE}/api/v1/it/tickets/5/ready`, JSON.stringify({ version: 2 })],
    ])
  })
})
