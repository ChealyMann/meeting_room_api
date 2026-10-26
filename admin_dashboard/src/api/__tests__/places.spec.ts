import { describe, expect, it, vi, type Mock } from 'vitest'

import { createApiClient } from '../client'
import { countActiveRooms, createOffice, listFloorPage, listOfficePage, updateBuilding } from '../places'
import type { LocationCreate } from '../types'

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

describe('places API', () => {
  it('lists offices with the given filters', async () => {
    const fetchMock = answer({ items: [], page: 2, size: 50, total: 0 })

    await listOfficePage(client(fetchMock), { province: 'PP', is_active: true, page: 2, size: 50 })

    expect(sent(fetchMock)).toMatchObject({ method: 'GET', url: `${BASE}/api/v1/locations?province=PP&is_active=true&page=2&size=50` })
  })

  it('creates an office with exactly the given body', async () => {
    const fetchMock = answer({ id: 3 })
    const body: LocationCreate = { name_en: 'Head Office', name_kh: 'ការិយាល័យកណ្តាល', province: 'PP' }

    await createOffice(client(fetchMock), body)

    expect(sent(fetchMock)).toEqual({ method: 'POST', url: `${BASE}/api/v1/locations`, body: JSON.stringify(body) })
  })

  it('moves a building with a PATCH of its office', async () => {
    const fetchMock = answer({ id: 5 })

    await updateBuilding(client(fetchMock), 5, { location_id: 4 })

    expect(sent(fetchMock)).toEqual({ method: 'PATCH', url: `${BASE}/api/v1/buildings/5`, body: '{"location_id":4}' })
  })

  it('lists floors by office and building', async () => {
    const fetchMock = answer({ items: [], page: 1, size: 20, total: 0 })

    await listFloorPage(client(fetchMock), { location_id: 3, building_id: 5 })

    expect(sent(fetchMock).url).toBe(`${BASE}/api/v1/floors?location_id=3&building_id=5`)
  })

  it('counts the active rooms in a place', async () => {
    const fetchMock = answer({ items: [{ id: 1 }], page: 1, size: 1, total: 12 })

    await expect(countActiveRooms(client(fetchMock), { building_id: 5 })).resolves.toBe(12)

    expect(sent(fetchMock).url).toBe(`${BASE}/api/v1/rooms?building_id=5&is_active=true&page=1&size=1`)
  })
})
