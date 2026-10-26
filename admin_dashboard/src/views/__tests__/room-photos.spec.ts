import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { answerConfirm, confirmDialog, mountConfirmHost } from '../../test-utils/confirm'
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
let orderAnswer: (ids: number[]) => Response | Promise<Response>
let serverPhotos: PhotoOut[] = []

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
      if (path === '/api/v1/rooms/12') return json({ id: 12, photos: serverPhotos })
      return json({})
    }),
  )
})

afterEach(() => vi.unstubAllGlobals())

async function mountPhotos(photos: PhotoOut[]) {
  mountConfirmHost()
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

  it("shows the server's order when it refuses a reorder (someone else changed the photos)", async () => {
    // The API's real answer (app/services/room_photo.py reorder_photos).
    orderAnswer = () =>
      json({ error: { code: 'VALIDATION_ERROR', message: 'Invalid request.', fields: { photo_ids: 'The list of photos is not complete.' } } }, 422)
    serverPhotos = [photo(31, 1), photo(32, 2), photo(34, 3)]
    const wrapper = await mountPhotos([photo(31, 1), photo(32, 2)])

    await wrapper.findAll('li.photo')[1]!.get('button[aria-label="Move earlier"]').trigger('click')
    await flushPromises()

    expect(calls.some((c) => c.method === 'GET' && c.path === '/api/v1/rooms/12')).toBe(true)
    expect(ids(wrapper)).toEqual([31, 32, 34])
    expect(wrapper.get('[role="alert"]').text()).toContain('The photos changed. This is the current order.')
    expect(lastChange(wrapper).map((p) => p.id)).toEqual([31, 32, 34])
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
    await flushPromises()
    expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
    expect(confirmDialog()?.textContent).toContain('Delete photo 2?')

    await answerConfirm('Delete photo')

    expect(calls.find((c) => c.method === 'DELETE')?.path).toBe('/api/v1/rooms/12/photos/32')
    expect(ids(wrapper)).toEqual([31])
  })
})

describe('RoomPhotos delete confirm', () => {
  it('keeps the photo when the dialog is cancelled', async () => {
    const wrapper = await mountPhotos([photo(31, 1), photo(32, 2)])

    await wrapper.findAll('li.photo')[0]!.get('button[aria-label="Delete photo"]').trigger('click')
    await flushPromises()
    expect(confirmDialog()?.textContent).toContain('the next photo becomes the cover')
    await answerConfirm('Cancel')

    expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
    expect(ids(wrapper)).toEqual([31, 32])
  })
})

describe('RoomPhotos one action at a time', () => {
  it('blocks moves and deletes while an upload runs', async () => {
    let finish: () => void = () => {}
    const pending = new Promise<void>((resolve) => (finish = resolve))
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>(async (_input, init) => {
        if (init?.method === 'POST') {
          await pending
          return json(photo(nextId++, 9), 201)
        }
        calls.push({ method: init?.method ?? 'GET', path: '' })
        return json({ items: [], total: 0 })
      }),
    )
    const wrapper = await mountPhotos([photo(31, 1), photo(32, 2)])

    const input = wrapper.get('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [new File(['x'], 'a.jpg')], configurable: true })
    await input.trigger('change')

    const first = wrapper.findAll('li.photo')[0]!
    expect(first.get('button[aria-label="Move later"]').attributes('disabled')).toBeDefined()
    expect(first.get('button[aria-label="Delete photo"]').attributes('disabled')).toBeDefined()
    finish()
    await flushPromises()
    expect(wrapper.findAll('li.photo')[0]!.get('button[aria-label="Move later"]').attributes('disabled')).toBeUndefined()
  })

  it('sends one reorder at a time', async () => {
    let release: () => void = () => {}
    orderAnswer = (order) =>
      new Promise<Response>((resolve) =>
        (release = () => resolve(json({ items: order.map((id, i) => photo(id, i + 1)), total: order.length }))),
      )
    const wrapper = await mountPhotos([photo(31, 1), photo(32, 2), photo(33, 3)])

    await wrapper.findAll('li.photo')[0]!.get('button[aria-label="Move later"]').trigger('click')
    await wrapper.findAll('li.photo')[1]!.get('button[aria-label="Move later"]').trigger('click')
    release()
    await flushPromises()

    expect(calls.filter((c) => c.method === 'PUT')).toHaveLength(1)
    expect(ids(wrapper)).toEqual([32, 31, 33])
  })
})
