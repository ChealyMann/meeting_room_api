import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { RoomDetail } from '../../api/types'
import { useSessionStore } from '../../stores/session'
import RoomFormPanel from '../rooms/RoomFormPanel.vue'

const page = <T>(items: T[]) => ({ items, page: 1, size: 100, total: items.length })
const BUILDINGS: Record<string, unknown[]> = {
  '3': [{ id: 5, location_id: 3, name_en: 'Building A', name_kh: 'អគារ A', is_active: true }],
  '4': [{ id: 6, location_id: 4, name_en: 'Main Building', name_kh: 'អគារធំ', is_active: true }],
}
const FLOORS: Record<string, unknown[]> = {
  '5': [{ id: 7, building_id: 5, floor_label: '3rd floor', is_active: true }],
}

const SAVED = {
  id: 12,
  name_en: 'Mekong Room',
  name_kh: 'បន្ទប់មេគង្គ',
  short_desc: null,
  description: null,
  capacity: 12,
  size_sqm: null,
  start_time: '08:00',
  end_time: '17:00',
  category: { id: 1, name_en: 'Meeting room', name_kh: 'បន្ទប់ប្រជុំ' },
  floor: { id: 7, floor_label: '3rd floor' },
  building: { id: 5, name_en: 'Building A', name_kh: 'អគារ A', short_name: null },
  location: { id: 3, name_en: 'Head Office', name_kh: 'ការិយាល័យកណ្តាល' },
  province: { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' },
  owner: null,
  cover_photo: null,
  is_active: true,
  is_bookable: true,
  is_private: false,
  photos: [],
  equipment: [],
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
}

let posts: Array<{ method: string; path: string; body: string }>
let saveAnswer: () => Response
const fetchCalls: string[] = []

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  posts = []
  fetchCalls.length = 0
  saveAnswer = () => json(SAVED, 201)
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      fetchCalls.push(url.pathname + url.search)
      const q = url.searchParams
      if (init?.method === 'POST' || init?.method === 'PATCH') {
        posts.push({ method: init.method, path: url.pathname, body: String(init.body) })
        return saveAnswer()
      }
      switch (url.pathname) {
        case '/api/v1/locations':
          return json(page([
            { id: 3, name_en: 'Head Office', name_kh: '', is_active: true },
            { id: 4, name_en: 'Siem Reap Branch', name_kh: '', is_active: true },
          ]))
        case '/api/v1/buildings':
          return json(page(BUILDINGS[q.get('location_id') ?? ''] ?? []))
        case '/api/v1/floors':
          return json(page(FLOORS[q.get('building_id') ?? ''] ?? []))
        case '/api/v1/categories':
          return json(page([{ id: 1, name_en: 'Meeting room', name_kh: '', is_active: true }]))
        case '/api/v1/users':
          return json(page([{ id: 2, name_en: 'Sok Dara', name_kh: 'សុខ ដារា', is_active: true }]))
        default:
          return json(page([]))
      }
    }),
  )
})

afterEach(() => vi.unstubAllGlobals())

async function mountPanel(room: RoomDetail | null = null) {
  const wrapper = mount(RoomFormPanel, {
    props: { room },
    global: { stubs: { teleport: true } },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

type Wrapper = Awaited<ReturnType<typeof mountPanel>>

async function fillValid(wrapper: Wrapper) {
  await wrapper.get('#name_kh').setValue('បន្ទប់មេគង្គ')
  await wrapper.get('#name_en').setValue('Mekong Room')
  await wrapper.get('#location_id').setValue('3')
  await flushPromises()
  await wrapper.get('#building_id').setValue('5')
  await flushPromises()
  await wrapper.get('#floor_id').setValue('7')
  await wrapper.get('#category_id').setValue('1')
  await wrapper.get('#capacity').setValue('12')
}

async function submit(wrapper: Wrapper) {
  await wrapper.get('form').trigger('submit')
  await flushPromises()
}

describe('RoomFormPanel', () => {
  it('sends nothing while required fields are missing, and lists them', async () => {
    const wrapper = await mountPanel()

    await submit(wrapper)

    expect(posts).toEqual([])
    const summary = wrapper.get('[role="alert"]').text()
    expect(summary).toContain('Khmer name')
    expect(summary).toContain('Floor')
    expect(wrapper.get('#name_kh-error').text()).toBe('Enter the Khmer name.')
  })

  it('creates the room with exactly the form values and reports it', async () => {
    const wrapper = await mountPanel()
    await fillValid(wrapper)

    await submit(wrapper)

    expect(posts).toEqual([
      {
        method: 'POST',
        path: '/api/v1/rooms',
        body: JSON.stringify({
          name_kh: 'បន្ទប់មេគង្គ',
          name_en: 'Mekong Room',
          floor_id: 7,
          category_id: 1,
          capacity: 12,
          start_time: '08:00',
          end_time: '17:00',
          is_private: false,
        }),
      },
    ])
    expect(wrapper.emitted('saved')?.[0]?.[0]).toMatchObject({ id: 12 })
  })

  it('shows a duplicate name under the English name', async () => {
    saveAnswer = () =>
      json({ error: { code: 'DUPLICATE', message: 'Name used.', fields: { name_en: 'A room on this floor already has this name.' } } }, 409)
    const wrapper = await mountPanel()
    await fillValid(wrapper)

    await submit(wrapper)

    expect(wrapper.get('#name_en-error').text()).toBe('A room on this floor already has this name.')
    expect(wrapper.emitted('saved')).toBeUndefined()
  })

  it('clears building and floor when the office changes', async () => {
    const wrapper = await mountPanel()
    await fillValid(wrapper)

    await wrapper.get('#location_id').setValue('4')
    await flushPromises()

    expect((wrapper.get('#building_id').element as HTMLSelectElement).value).toBe('')
    expect((wrapper.get('#floor_id').element as HTMLSelectElement).value).toBe('')
    expect(fetchCalls).toContain('/api/v1/buildings?location_id=4&page=1&size=100')
  })

  it('offers "No owner" and the active room owners', async () => {
    const wrapper = await mountPanel()

    const options = wrapper.findAll('#room_owner_id option').map((o) => o.text())
    expect(options).toEqual(['No owner', 'Sok Dara'])
    expect(fetchCalls).toContain('/api/v1/users?role=ROOM_OWNER&is_active=true&page=1&size=100')
  })

  it('keeps "Save changes" off until something changes, then sends only that', async () => {
    const wrapper = await mountPanel(SAVED as unknown as RoomDetail)
    const save = () => wrapper.findAll('button').find((b) => b.text() === 'Save changes')!

    expect(save().attributes('disabled')).toBeDefined()
    await wrapper.get('#capacity').setValue('14')
    expect(save().attributes('disabled')).toBeUndefined()

    await submit(wrapper)
    expect(posts).toEqual([{ method: 'PATCH', path: '/api/v1/rooms/12', body: '{"capacity":14}' }])
  })
})
