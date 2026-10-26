import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { PhotoOut } from '../../api/types'
import { useSessionStore } from '../../stores/session'
import RoomPhotos from '../rooms/RoomPhotos.vue'

enableAutoUnmount(afterEach)

const photo = (id: number, sort: number): PhotoOut => ({
  id,
  room_id: 12,
  url: `/uploads/rooms/12/${id}.jpg`,
  thumbnail_url: `/uploads/rooms/12/${id}_thumb.jpg`,
  sort_order: sort,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
})

const calls: Array<{ method: string; path: string; body?: unknown }> = []
let nextId = 50
let uploadAnswer: (file: File) => Response
let orderAnswer: (ids: number[]) => Response

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  calls.length = 0
  nextId = 50
  uploadAnswer = () => json(photo(nextId++, 9), 201)
  orderAnswer = (ids) => json({ items: ids.map((id, i) => photo(id, i + 1)), total: ids.length })
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const path = new URL(String(input)).pathname
      const method = init?.method ?? 'GET'
      const body = init?.body instanceof FormData ? init.body.get('file') : init?.body ? JSON.parse(String(init.body)) : undefined
      calls.push({ method, path, body })
      if (method === 'POST') return uploadAnswer(body as File)
      if (method === 'PUT') return orderAnswer((body as { photo_ids: number[] }).photo_ids)
      if (method === 'DELETE') return new Response(null, { status: 204 })
      return json({})
    }),
  )
})

afterEach(() => vi.unstubAllGlobals())

async function mountPhotos(photos: PhotoOut[]) {
  const wrapper = mount(RoomPhotos, { props: { roomId: 12, photos }, attachTo: document.body })
  await flushPromises()
  return wrapper
}

type Wrapper = Awaited<ReturnType<typeof mountPhotos>>

async function choose(wrapper: Wrapper, files: File[]) {
  const input = wrapper.get('input[type="file"]')
  Object.defineProperty(input.element, 'files', { value: files, configurable: true })
  await input.trigger('change')
  await flushPromises()
}

const ids = (wrapper: Wrapper) => wrapper.findAll('li.photo').map((li) => Number(li.attributes('data-id')))
const lastChange = (wrapper: Wrapper) => {
  const events = wrapper.emitted('change') ?? []
  return events[events.length - 1]?.[0] as PhotoOut[]
}

describe('RoomPhotos', () => {
  it('shows the photos with the first one as the cover', async () => {
    const wrapper = await mountPhotos([photo(31, 1), photo(32, 2)])

    expect(ids(wrapper)).toEqual([31, 32])
    expect(wrapper.findAll('li.photo')[0]!.text()).toContain('Cover')
    expect(wrapper.findAll('li.photo')[1]!.text()).not.toContain('Cover')
    expect(wrapper.get('img').attributes('src')).toBe('http://localhost:8000/uploads/rooms/12/31_thumb.jpg')
    expect(wrapper.text()).toContain('2/20')
  })

  it('uploads the good files and names each refused one', async () => {
    uploadAnswer = (file) =>
      file.name === 'photo-2.gif'
        ? json({ error: { code: 'UNSUPPORTED_FILE_TYPE', message: 'Wrong file type.' } }, 415)
        : json(photo(nextId++, 9), 201)
    const wrapper = await mountPhotos([])
    const files = ['photo-1.jpg', 'photo-2.gif', 'photo-3.png'].map((name) => new File(['x'], name))

    await choose(wrapper, files)

    expect(calls.filter((c) => c.method === 'POST').map((c) => (c.body as File).name)).toEqual([
      'photo-1.jpg',
      'photo-2.gif',
      'photo-3.png',
    ])
    expect(ids(wrapper)).toEqual([50, 51])
    expect(wrapper.get('[role="alert"]').text()).toContain('photo-2.gif: Wrong file type.')
    expect(lastChange(wrapper).map((p) => p.id)).toEqual([50, 51])
  })

  it('stops adding at 20 photos', async () => {
    const twenty = Array.from({ length: 20 }, (_, i) => photo(i + 1, i + 1))
    const wrapper = await mountPhotos(twenty)

    expect(wrapper.get('input[type="file"]').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('20 photos is the limit')
  })

  it('moves a photo later and sends the new order', async () => {
    const wrapper = await mountPhotos([photo(31, 1), photo(32, 2), photo(33, 3)])

    await wrapper.findAll('li.photo')[0]!.get('button[aria-label="Move later"]').trigger('click')
    await flushPromises()

    expect(calls.find((c) => c.method === 'PUT')).toEqual({
      method: 'PUT',
      path: '/api/v1/rooms/12/photos/order',
      body: { photo_ids: [32, 31, 33] },
    })
    expect(ids(wrapper)).toEqual([32, 31, 33])
    expect(wrapper.findAll('li.photo')[0]!.text()).toContain('Cover')
    expect(lastChange(wrapper).map((p) => p.id)).toEqual([32, 31, 33])
  })

  it('puts the order back when the server refuses it', async () => {
    orderAnswer = () => json({ error: { code: 'VALIDATION_ERROR', message: 'The photo list changed.' } }, 422)
    const wrapper = await mountPhotos([photo(31, 1), photo(32, 2)])

    await wrapper.findAll('li.photo')[1]!.get('button[aria-label="Move earlier"]').trigger('click')
    await flushPromises()

    expect(ids(wrapper)).toEqual([31, 32])
    expect(wrapper.get('[role="alert"]').text()).toContain('The photo list changed.')
  })

  it('reorders by drag and drop', async () => {
    const wrapper = await mountPhotos([photo(31, 1), photo(32, 2), photo(33, 3)])
    const items = wrapper.findAll('li.photo')

    await items[2]!.trigger('dragstart')
    await items[0]!.trigger('drop')
    await flushPromises()

    expect(ids(wrapper)).toEqual([33, 31, 32])
  })

  it('asks before deleting, then deletes', async () => {
    const wrapper = await mountPhotos([photo(31, 1), photo(32, 2)])

    await wrapper.findAll('li.photo')[1]!.get('button[aria-label="Delete photo"]').trigger('click')
    expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
    expect(wrapper.text()).toContain('Delete photo 2?')

    await wrapper.findAll('.confirm button').find((b) => b.text() === 'Delete photo')!.trigger('click')
    await flushPromises()

    expect(calls.find((c) => c.method === 'DELETE')?.path).toBe('/api/v1/rooms/12/photos/32')
    expect(ids(wrapper)).toEqual([31])
  })
})

describe('RoomPhotos delete confirm', () => {
  it('asks under the grid, full width, naming which photo', async () => {
    const wrapper = await mountPhotos([photo(31, 1), photo(32, 2)])

    await wrapper.findAll('li.photo')[1]!.get('button[aria-label="Delete photo"]').trigger('click')

    expect(wrapper.find('li.photo .confirm').exists()).toBe(false)
    expect(wrapper.get('.photos > .confirm').text()).toContain('Delete photo 2?')
  })
})

describe('RoomPhotos delete confirm visibility', () => {
  it('scrolls the confirm into view when it opens', async () => {
    const scroll = vi.fn<(arg?: ScrollIntoViewOptions | boolean) => void>()
    Element.prototype.scrollIntoView = scroll
    const wrapper = await mountPhotos([photo(31, 1), photo(32, 2), photo(33, 3)])

    await wrapper.findAll('li.photo')[2]!.get('button[aria-label="Delete photo"]').trigger('click')
    await flushPromises()

    expect(scroll).toHaveBeenCalledWith({ block: 'nearest', behavior: 'smooth' })
  })
})
