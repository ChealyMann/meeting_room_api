import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { useSessionStore } from '../../stores/session'
import RoomsView from '../RoomsView.vue'

const page = <T>(items: T[], total = items.length) => ({ items, page: 1, size: 100, total })

const OFFICES = [
  { id: 3, name_en: 'Head Office', name_kh: 'ការិយាល័យកណ្តាល', is_active: true },
  { id: 4, name_en: 'Siem Reap Branch', name_kh: 'សាខាសៀមរាប', is_active: true },
]
const BUILDINGS: Record<string, unknown[]> = {
  '3': [{ id: 5, location_id: 3, name_en: 'Building A', name_kh: 'អគារ A', is_active: true }],
  '4': [{ id: 6, location_id: 4, name_en: 'Main Building', name_kh: 'អគារធំ', is_active: true }],
}
const FLOORS: Record<string, unknown[]> = {
  '5': [{ id: 7, building_id: 5, floor_label: '3rd floor', is_active: true }],
}
const TYPES = [{ id: 1, name_en: 'Meeting room', name_kh: 'បន្ទប់ប្រជុំ', is_active: true }]

function room(id: number, overrides: Record<string, unknown> = {}) {
  return {
    id,
    name_en: 'Mekong Room',
    name_kh: 'បន្ទប់មេគង្គ',
    short_desc: null,
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
    ...overrides,
  }
}

type RoomsAnswer = () => Promise<Response> | Response
let roomsAnswer: RoomsAnswer
let roomCalls: string[]

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

enableAutoUnmount(afterEach)

beforeEach(() => {
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  roomCalls = []
  roomsAnswer = () => json(page([room(12), room(13, { name_en: 'Tonle Room', owner: { id: 2, name_en: 'Sok Dara', name_kh: 'សុខ ដារា' } })]))
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input) => {
      const url = new URL(String(input))
      const q = url.searchParams
      switch (url.pathname) {
        case '/api/v1/rooms':
          roomCalls.push(url.search)
          return roomsAnswer()
        case '/api/v1/locations':
          return json(page(OFFICES))
        case '/api/v1/buildings':
          return json(page(BUILDINGS[q.get('location_id') ?? ''] ?? []))
        case '/api/v1/floors':
          return json(page(FLOORS[q.get('building_id') ?? ''] ?? []))
        case '/api/v1/categories':
          return json(page(TYPES))
        case '/api/v1/rooms/12':
          return json({ ...room(12), description: null, photos: [], equipment: [], created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z' })
        default:
          return json(page([]))
      }
    }),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

async function mountAt(path: string) {
  const router: Router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', name: 'home', component: RoomsView }],
  })
  await router.push(path)
  const wrapper = mount(RoomsView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}

const query = (router: Router) => router.currentRoute.value.query

describe('RoomsView list', () => {
  it('asks the API with the filters from the address', async () => {
    await mountAt('/?location_id=3&search=board')

    expect(roomCalls[roomCalls.length - 1]).toBe('?location_id=3&search=board&is_active=true&page=1&size=20')
  })

  it('shows rooms with Khmer over English, serial, hours and owner', async () => {
    const { wrapper } = await mountAt('/')

    const first = wrapper.findAll('tbody tr')[0]!
    expect(first.get('.name-plate').findAll('span').map((s) => s.text())).toEqual(['បន្ទប់មេគង្គ', 'Mekong Room'])
    expect(first.text()).toContain('RM·0012')
    expect(first.text()).toContain('08:00–17:00')
    expect(first.text()).toContain('No owner')
    expect(wrapper.findAll('tbody tr')[1]!.text()).toContain('Sok Dara')
    expect(wrapper.get('.count').text()).toBe('002 rooms')
  })

  it('clears building and floor when the office changes', async () => {
    const { wrapper, router } = await mountAt('/?location_id=3')

    await wrapper.get('select#filter-building').setValue('5')
    await flushPromises()
    expect(query(router)).toMatchObject({ location_id: '3', building_id: '5' })

    await wrapper.get('select#filter-office').setValue('4')
    await flushPromises()
    expect(query(router)).toEqual({ location_id: '4' })
  })

  it('still loads rooms for an office that no longer exists, and says so', async () => {
    const { wrapper } = await mountAt('/?location_id=999')

    expect(roomCalls[roomCalls.length - 1]).toContain('location_id=999')
    const select = wrapper.get('select#filter-office').element as HTMLSelectElement
    expect(select.selectedOptions[0]!.textContent).toBe('Unknown office')
  })

  it('opens a room from its row', async () => {
    const { wrapper, router } = await mountAt('/')

    await wrapper.findAll('tbody tr')[0]!.trigger('click')
    await flushPromises()

    expect(query(router)).toMatchObject({ room: '12' })
  })

  it('invites to add the first room when there are none', async () => {
    roomsAnswer = () => json(page([]))
    const { wrapper } = await mountAt('/')

    expect(wrapper.text()).toContain('No rooms yet')
    expect(wrapper.text()).not.toContain('Clear filters')
  })

  it('names the filters when nothing matches, and clears them', async () => {
    roomsAnswer = () => json(page([]))
    const { wrapper, router } = await mountAt('/?location_id=3&search=board')

    expect(wrapper.text()).toContain('No rooms match')
    expect(wrapper.text()).toContain('Head Office')
    expect(wrapper.text()).toContain('“board”')

    await wrapper.findAll('button').find((b) => b.text() === 'Clear filters')!.trigger('click')
    await flushPromises()
    expect(query(router)).toEqual({})
  })

  it('shows skeleton rows while the rooms are loading', async () => {
    roomsAnswer = () => new Promise<Response>(() => {})
    const { wrapper } = await mountAt('/')

    expect(wrapper.find('.skeleton[aria-hidden="true"]').exists()).toBe(true)
    expect(wrapper.find('tbody').exists()).toBe(false)
  })

  it('moves to another page from the paging foot', async () => {
    roomsAnswer = () => json({ items: [room(12)], page: 1, size: 20, total: 45 })
    const { wrapper, router } = await mountAt('/')

    await wrapper.findAll('nav[aria-label="Pages"] button').find((b) => b.text() === '2')!.trigger('click')
    await flushPromises()

    expect(query(router)).toEqual({ page: '2' })
  })

  it('shows the API message with a way to try again', async () => {
    roomsAnswer = () => json({ error: { code: 'X', message: 'Database is down.' } }, 500)
    const { wrapper } = await mountAt('/')

    expect(wrapper.get('[role="alert"]').text()).toContain('Database is down.')
    roomsAnswer = () => json(page([room(12)]))
    await wrapper.findAll('button').find((b) => b.text() === 'Try again')!.trigger('click')
    await flushPromises()
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
  })

  it('waits for typing to stop before searching', async () => {
    const { wrapper, router } = await mountAt('/')
    vi.useFakeTimers()

    await wrapper.get('input[type="search"]').setValue('mek')
    expect(query(router)).toEqual({})
    vi.advanceTimersByTime(300)
    await flushPromises()

    expect(query(router)).toEqual({ search: 'mek' })
  })
})

describe('RoomsView panels', () => {
  it('opens a room from the address, edits it and closes it', async () => {
    const { router } = await mountAt('/?room=12')
    const panel = () => document.body.querySelector('[role="dialog"]')

    expect(panel()?.textContent).toContain('បន្ទប់មេគង្គ')
    ;[...document.body.querySelectorAll('[role="dialog"] button')]
      .find((b) => b.textContent?.trim() === 'Edit')!
      .dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await flushPromises()
    expect(query(router)).toMatchObject({ room: '12', edit: '1' })
    expect(document.body.querySelector('#name_en')).not.toBeNull()

    ;(document.body.querySelector('[role="dialog"] button[aria-label="Close"]') as HTMLElement).click()
    await flushPromises()
    expect(query(router)).toEqual({})
  })

  it('opens the create form for room=new', async () => {
    await mountAt('/?room=new')

    expect(document.body.querySelector('[role="dialog"]')?.textContent).toContain('New room')
  })
})
