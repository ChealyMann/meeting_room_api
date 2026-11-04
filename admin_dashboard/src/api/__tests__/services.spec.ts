import { describe, expect, it, vi, type Mock } from 'vitest'

import { createApiClient } from '../client'
import { getService, listServicePage, updateService } from '../services'

const BASE = 'http://localhost:8000'
type FetchMock = Mock<typeof fetch>

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}
const answer = (body: unknown) => vi.fn<typeof fetch>(async () => json(body))
const client = (fetchImpl: FetchMock) =>
  createApiClient({ baseUrl: BASE, getAccessToken: () => 'A', refresh: async () => false, onAuthLost: () => {}, fetchImpl })

function sent(fn: FetchMock) {
  const call = fn.mock.calls[0]
  if (!call) throw new Error('fetch was not called')
  return { method: call[1]?.method, url: String(call[0]), body: call[1]?.body }
}

describe('services API', () => {
  it('lists IT services with the given filters', async () => {
    const fetchMock = answer({ items: [], page: 1, size: 20, total: 0 })

    await listServicePage(client(fetchMock), 'it', { search: 'mic', is_active: true, page: 1, size: 20 })

    expect(sent(fetchMock)).toMatchObject({ method: 'GET', url: `${BASE}/api/v1/it-services?search=mic&is_active=true&page=1&size=20` })
  })

  it('sends the version with a catering package change', async () => {
    const fetchMock = answer({ id: 3 })

    await updateService(client(fetchMock), 'catering', 3, { version: 2, is_active: false })

    expect(sent(fetchMock)).toEqual({
      method: 'PATCH',
      url: `${BASE}/api/v1/catering-packages/3`,
      body: JSON.stringify({ version: 2, is_active: false }),
    })
  })

  it('finds one package in the list, since the API has no GET by id', async () => {
    const fetchMock = answer({ items: [{ id: 2 }, { id: 3, name: 'Lunch box' }], page: 1, size: 100, total: 2 })

    const found = await getService(client(fetchMock), 'catering', 3)

    expect(found).toMatchObject({ id: 3, name: 'Lunch box' })
    expect(sent(fetchMock).url).toBe(`${BASE}/api/v1/catering-packages?page=1&size=100`)
  })
})
