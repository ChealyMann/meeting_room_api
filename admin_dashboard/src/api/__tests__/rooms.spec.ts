import { describe, expect, it, vi, type Mock } from 'vitest'

import { createApiClient } from '../client'
import { toQuery } from '../query'
import { listAll, listRoomOwners } from '../references'
import {
  createRoom,
  listRooms,
  reorderRoomPhotos,
  setRoomEquipment,
  updateRoom,
  uploadRoomPhoto,
} from '../rooms'
import type { RoomCreate } from '../types'

const BASE = 'http://localhost:8000'

type FetchMock = Mock<typeof fetch>

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function clientWith(fetchImpl: FetchMock) {
  return createApiClient({
    baseUrl: BASE,
    getAccessToken: () => 'A',
    refresh: async () => false,
    onAuthLost: () => {},
    fetchImpl,
  })
}

/** Method, URL and body of the n-th fetch call. */
function sent(fn: FetchMock, n = 0) {
  const call = fn.mock.calls[n]
  if (!call) throw new Error(`fetch was not called ${n + 1} time(s)`)
  const init = call[1] ?? {}
  return { method: init.method, url: String(call[0]), body: init.body }
}

const answer = (body: unknown) => vi.fn<typeof fetch>(async () => json(200, body))

describe('toQuery', () => {
  it('drops empty values, joins lists with commas and keeps the order', () => {
    expect(
      toQuery({
        search: 'board',
        location_id: 3,
        equipment_ids: [1, 4],
        has_owner: false,
        floor_id: undefined,
        owner_id: null,
        province: '',
      }),
    ).toBe('?search=board&location_id=3&equipment_ids=1%2C4&has_owner=false')
  })

  it('is empty when there is nothing to send', () => {
    expect(toQuery({})).toBe('')
    expect(toQuery({ equipment_ids: [] })).toBe('')
  })
})

describe('rooms', () => {
  it('lists rooms with the given filters', async () => {
    const fetchMock = answer({ items: [], page: 2, size: 50, total: 0 })

    await listRooms(clientWith(fetchMock), { is_active: true, page: 2, size: 50 })

    expect(sent(fetchMock)).toMatchObject({
      method: 'GET',
      url: `${BASE}/api/v1/rooms?is_active=true&page=2&size=50`,
    })
  })

  it('creates a room with exactly the given body', async () => {
    const fetchMock = answer({ id: 12 })
    const body: RoomCreate = {
      name_en: 'Mekong Room',
      name_kh: 'បន្ទប់មេគង្គ',
      floor_id: 3,
      category_id: 1,
      capacity: 12,
      start_time: '08:00',
      end_time: '17:00',
      is_private: false,
    }

    await createRoom(clientWith(fetchMock), body)

    expect(sent(fetchMock)).toEqual({
      method: 'POST',
      url: `${BASE}/api/v1/rooms`,
      body: JSON.stringify(body),
    })
  })

  it('sends only the changes when updating', async () => {
    const fetchMock = answer({ id: 12 })

    await updateRoom(clientWith(fetchMock), 12, { capacity: 14 })

    expect(sent(fetchMock)).toEqual({
      method: 'PATCH',
      url: `${BASE}/api/v1/rooms/12`,
      body: '{"capacity":14}',
    })
  })

  it('uploads a photo in a form field named file', async () => {
    const fetchMock = answer({ id: 33 })
    const file = new File(['jpg'], 'room.jpg', { type: 'image/jpeg' })

    await uploadRoomPhoto(clientWith(fetchMock), 12, file)

    const { method, url, body } = sent(fetchMock)
    expect(method).toBe('POST')
    expect(url).toBe(`${BASE}/api/v1/rooms/12/photos`)
    expect((body as FormData).get('file')).toBe(file)
  })

  it('reorders photos and sets equipment with id lists', async () => {
    const fetchMock = answer({ items: [], total: 0 })
    const client = clientWith(fetchMock)

    await reorderRoomPhotos(client, 12, [33, 31])
    await setRoomEquipment(client, 12, [1, 4])

    expect(sent(fetchMock, 0)).toEqual({
      method: 'PUT',
      url: `${BASE}/api/v1/rooms/12/photos/order`,
      body: '{"photo_ids":[33,31]}',
    })
    expect(sent(fetchMock, 1)).toEqual({
      method: 'PUT',
      url: `${BASE}/api/v1/rooms/12/equipment`,
      body: '{"equipment_ids":[1,4]}',
    })
  })
})

describe('references', () => {
  it('collects every page of a list', async () => {
    const items = (from: number, count: number) =>
      Array.from({ length: count }, (_, i) => ({ id: from + i }))
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      const page = new URL(String(input)).searchParams.get('page')
      return page === '1'
        ? json(200, { items: items(1, 100), page: 1, size: 100, total: 150 })
        : json(200, { items: items(101, 50), page: 2, size: 100, total: 150 })
    })

    const all = await listAll<{ id: number }>(clientWith(fetchMock), '/api/v1/locations')

    expect(all).toHaveLength(150)
    expect(sent(fetchMock, 0).url).toBe(`${BASE}/api/v1/locations?page=1&size=100`)
    expect(sent(fetchMock, 1).url).toBe(`${BASE}/api/v1/locations?page=2&size=100`)
  })

  it('lists active room owners only', async () => {
    const fetchMock = answer({ items: [], page: 1, size: 100, total: 0 })

    await listRoomOwners(clientWith(fetchMock))

    expect(sent(fetchMock).url).toBe(
      `${BASE}/api/v1/users?role=ROOM_OWNER&is_active=true&page=1&size=100`,
    )
  })
})
