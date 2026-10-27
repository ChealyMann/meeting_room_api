import { describe, expect, it, vi, type Mock } from 'vitest'

import { createApiClient } from '../client'
import { createRoomType, listEquipmentPage, listRoomTypePage, updateEquipment } from '../catalog'

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

describe('catalog API', () => {
  it('lists room types with the given filters', async () => {
    const fetchMock = answer({ items: [], page: 2, size: 50, total: 0 })

    await listRoomTypePage(client(fetchMock), { search: 'board', is_active: true, page: 2, size: 50 })

    expect(sent(fetchMock)).toMatchObject({ method: 'GET', url: `${BASE}/api/v1/categories?search=board&is_active=true&page=2&size=50` })
  })

  it('creates a room type with exactly the given body', async () => {
    const fetchMock = answer({ id: 2 })

    await createRoomType(client(fetchMock), { name_kh: 'បន្ទប់ប្រជុំ', name_en: 'Meeting room', sort_order: 0 })

    expect(sent(fetchMock)).toEqual({
      method: 'POST',
      url: `${BASE}/api/v1/categories`,
      body: JSON.stringify({ name_kh: 'បន្ទប់ប្រជុំ', name_en: 'Meeting room', sort_order: 0 }),
    })
  })

  it('lists equipment on its own path', async () => {
    const fetchMock = answer({ items: [], page: 1, size: 20, total: 0 })

    await listEquipmentPage(client(fetchMock), { search: 'mic', page: 1, size: 20 })

    expect(sent(fetchMock)).toMatchObject({ url: `${BASE}/api/v1/equipment?search=mic&page=1&size=20` })
  })

  it('clears an icon with null', async () => {
    const fetchMock = answer({ id: 4 })

    await updateEquipment(client(fetchMock), 4, { icon: null })

    expect(sent(fetchMock)).toEqual({ method: 'PATCH', url: `${BASE}/api/v1/equipment/4`, body: '{"icon":null}' })
  })
})
