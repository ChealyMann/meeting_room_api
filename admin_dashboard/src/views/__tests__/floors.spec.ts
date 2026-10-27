import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { NAV_GROUPS } from '../../layouts/nav'
import { useSessionStore } from '../../stores/session'
import { mountConfirmHost } from '../../test-utils/confirm'
import FloorsView from '../FloorsView.vue'

enableAutoUnmount(afterEach)

const PP = { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' }
const stamps = { is_active: true, created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z' }
const OFFICES = [
  { id: 3, name_en: 'Head Office', name_kh: 'ការិយាល័យ', description: null, address: null, province: PP, map_query: null, ...stamps },
  { id: 4, name_en: 'Siem Reap Branch', name_kh: 'សាខា', description: null, address: null, province: PP, map_query: null, ...stamps },
]
const BUILDINGS = [
  { id: 5, location_id: 3, name_en: 'Tower A', name_kh: 'អគារ ក', short_name: 'A', sort_order: 1, ...stamps },
  { id: 8, location_id: 4, name_en: 'River House', name_kh: 'ផ្ទះ', short_name: null, sort_order: 1, ...stamps },
]
const floor = (id: number, changes: Record<string, unknown> = {}) => ({
  id,
  building_id: 5,
  floor_label: '3rd floor',
  sort_order: 3,
  ...stamps,
  ...changes,
})

const listCalls: string[] = []
const buildingCalls: string[] = []
const writes: Array<{ method: string; path: string; body: string }> = []

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  listCalls.length = 0
  buildingCalls.length = 0
  writes.length = 0
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      const method = init?.method ?? 'GET'
      if (method !== 'GET') {
        writes.push({ method, path: url.pathname, body: String(init?.body) })
        return json({
          ...floor(12, { floor_label: 'Ground' }),
          building: { id: 5, name_en: 'Tower A', name_kh: 'អគារ ក' },
          location: { id: 3, name_en: 'Head Office', name_kh: 'ការិយាល័យ' },
          province: PP,
        }, 201)
      }
      if (url.pathname === '/api/v1/locations') return json({ items: OFFICES, page: 1, size: 100, total: 2 })
      if (url.pathname === '/api/v1/buildings') {
        buildingCalls.push(url.search)
        const office = Number(url.searchParams.get('location_id')) || null
        const items = office ? BUILDINGS.filter((b) => b.location_id === office) : BUILDINGS
        return json({ items, page: 1, size: 100, total: items.length })
      }
      if (url.pathname === '/api/v1/floors') {
        listCalls.push(url.search)
        return json({ items: [floor(7), floor(9, { building_id: 77, floor_label: 'Roof' })], page: 1, size: 20, total: 2 })
      }
      return json({ items: [], page: 1, size: 1, total: 0 })
    }),
  )
})
afterEach(() => vi.unstubAllGlobals())

async function mountAt(path: string) {
  mountConfirmHost()
  const router: Router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/floors', name: 'floors', component: FloorsView }],
  })
  await router.push(path)
  const wrapper = mount(FloorsView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}

const panel = () => document.body.querySelector('[role="dialog"]') as HTMLElement | null
const inPanel = <T extends Element>(selector: string) => panel()?.querySelector<T>(selector) ?? null

async function pick(wrapper: { get: (s: string) => { trigger: (e: string) => Promise<void> }; findAll: (s: string) => Array<{ text: () => string; trigger: (e: string) => Promise<void> }> }, id: string, text: string) {
  await wrapper.get(`button#${id}`).trigger('click')
  await flushPromises()
  await wrapper.findAll('[role="option"]').find((o) => o.text() === text)!.trigger('click')
  await flushPromises()
}

describe('FloorsView', () => {
  it('asks the API with the office and building from the address', async () => {
    await mountAt('/floors?location_id=3&building_id=5')

    expect(listCalls[listCalls.length - 1]).toBe('?location_id=3&building_id=5&is_active=true&page=1&size=20')
  })

  it('shows serial, floor, building and office', async () => {
    const { wrapper } = await mountAt('/floors')

    const [first, second] = wrapper.findAll('tbody tr')
    expect(first!.text()).toContain('FL·0007')
    expect(first!.text()).toContain('3rd floor')
    expect(first!.text()).toContain('Tower A')
    expect(first!.text()).toContain('Head Office')
    expect(second!.text()).toContain('#77')
    expect(wrapper.get('.count').text()).toBe('002 floors')
  })

  it('shows "Unknown building" for a building the office does not have', async () => {
    const { wrapper } = await mountAt('/floors?location_id=3&building_id=99')

    const select = wrapper.get<HTMLSelectElement>('#filter-building')
    expect(select.element.value).toBe('99')
    expect(select.find('option:checked').text()).toBe('Unknown building')
  })

  it('clears the building when another office is chosen', async () => {
    const { wrapper, router } = await mountAt('/floors?location_id=3&building_id=5')

    await pick(wrapper, 'filter-office', 'Siem Reap Branch')

    expect(router.currentRoute.value.query).toEqual({ location_id: '4' })
  })

  it('pre-sets office and building in a new floor and sends only the building', async () => {
    const { wrapper, router } = await mountAt('/floors?location_id=3&building_id=5')
    await wrapper.findAll('button').find((b) => b.text() === 'New floor')!.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.query).toEqual({ location_id: '3', building_id: '5', id: 'new' })
    expect(inPanel<HTMLSelectElement>('#location_id')!.value).toBe('3')
    expect(inPanel<HTMLSelectElement>('#building_id')!.value).toBe('5')

    const label = inPanel<HTMLInputElement>('#floor_label')!
    label.value = 'Ground'
    label.dispatchEvent(new Event('input'))
    inPanel<HTMLFormElement>('form')!.dispatchEvent(new Event('submit'))
    await flushPromises()

    expect(writes).toEqual([
      { method: 'POST', path: '/api/v1/floors', body: JSON.stringify({ building_id: 5, floor_label: 'Ground', sort_order: 0 }) },
    ])
  })

  it('is a real page in the sidebar', () => {
    const floors = NAV_GROUPS.flatMap((g) => g.items).find((i) => i.label === 'Floors')
    expect(floors?.route).toBe('floors')
  })
})
