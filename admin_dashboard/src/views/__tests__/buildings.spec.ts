import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { NAV_GROUPS } from '../../layouts/nav'
import { useSessionStore } from '../../stores/session'
import { mountConfirmHost } from '../../test-utils/confirm'
import BuildingsView from '../BuildingsView.vue'

enableAutoUnmount(afterEach)

const PP = { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' }
const office = (id: number, name_en: string, is_active = true) => ({
  id,
  name_en,
  name_kh: `ការិយាល័យ ${id}`,
  description: null,
  address: null,
  province: PP,
  map_query: null,
  is_active,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
})
const OFFICES = [office(3, 'Head Office'), office(4, 'Siem Reap Branch'), office(6, 'Old Branch', false)]
const building = (id: number, changes: Record<string, unknown> = {}) => ({
  id,
  location_id: 3,
  name_en: 'Tower A',
  name_kh: 'អគារ ក',
  short_name: 'A',
  sort_order: 1,
  is_active: true,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
  ...changes,
})
const detail = (id: number, changes: Record<string, unknown> = {}) => ({
  ...building(id, changes),
  location: { id: 3, name_en: 'Head Office', name_kh: 'ការិយាល័យ 3' },
  province: PP,
})

const listCalls: string[] = []
const writes: Array<{ method: string; path: string; body: string }> = []
let saveAnswer: () => Response
let detailAnswer: () => Response
let rows: unknown[]

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  listCalls.length = 0
  writes.length = 0
  saveAnswer = () => json(detail(9), 201)
  detailAnswer = () => json(detail(5))
  rows = [building(5), building(7, { location_id: 99, name_en: 'Annex', short_name: null })]
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      const method = init?.method ?? 'GET'
      if (method !== 'GET') {
        writes.push({ method, path: url.pathname, body: String(init?.body) })
        return saveAnswer()
      }
      if (url.pathname === '/api/v1/locations') return json({ items: OFFICES, page: 1, size: 100, total: 3 })
      if (url.pathname === '/api/v1/buildings/5') return detailAnswer()
      if (url.pathname === '/api/v1/buildings') {
        listCalls.push(url.search)
        return json({ items: rows, page: 1, size: 20, total: rows.length })
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
    routes: [{ path: '/buildings', name: 'buildings', component: BuildingsView }],
  })
  await router.push(path)
  const wrapper = mount(BuildingsView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}

const panel = () => document.body.querySelector('[role="dialog"]') as HTMLElement | null
const inPanel = <T extends Element>(selector: string) => panel()?.querySelector<T>(selector) ?? null
function setValue(selector: string, value: string) {
  const el = inPanel<HTMLInputElement | HTMLSelectElement>(selector)!
  el.value = value
  el.dispatchEvent(new Event(el instanceof HTMLSelectElement ? 'change' : 'input'))
}
async function clickInPanel(text: string) {
  await flushPromises() // let the panel render the last change first
  ;[...panel()!.querySelectorAll('button')].find((b) => b.textContent?.trim() === text)!.click()
  await flushPromises()
}

async function pick(wrapper: { get: (s: string) => { trigger: (e: string) => Promise<void> }; findAll: (s: string) => Array<{ text: () => string; trigger: (e: string) => Promise<void> }> }, id: string, text: string) {
  await wrapper.get(`button#${id}`).trigger('click')
  await flushPromises()
  await wrapper.findAll('[role="option"]').find((o) => o.text() === text)!.trigger('click')
  await flushPromises()
}

describe('BuildingsView', () => {
  it('asks the API with the office from the address', async () => {
    await mountAt('/buildings?location_id=3')

    expect(listCalls[listCalls.length - 1]).toBe('?location_id=3&is_active=true&page=1&size=20')
  })

  it('shows serial, Khmer over English with the short name, and the office name', async () => {
    const { wrapper } = await mountAt('/buildings')

    const [first, second] = wrapper.findAll('tbody tr')
    expect(first!.text()).toContain('BL·0005')
    expect(first!.get('.name-plate .kh').text()).toBe('អគារ ក')
    expect(first!.get('.name-plate .en').text()).toBe('Tower A A')
    expect(first!.text()).toContain('Head Office')
    expect(second!.text()).toContain('#99')
    expect(wrapper.get('.count').text()).toBe('002 buildings')
  })

  it('filters by office with the search picker', async () => {
    const { wrapper, router } = await mountAt('/buildings')

    await pick(wrapper, 'filter-office', 'Siem Reap Branch')

    expect(router.currentRoute.value.query).toEqual({ location_id: '4' })
  })

  it('pre-sets the filtered office in a new building', async () => {
    const { wrapper, router } = await mountAt('/buildings?location_id=3')
    await wrapper.findAll('button').find((b) => b.text() === 'New building')!.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.query).toEqual({ location_id: '3', id: 'new' })
    expect(inPanel<HTMLSelectElement>('#location_id')!.value).toBe('3')
  })

  it('shows a duplicate name under the English name when a move is refused', async () => {
    saveAnswer = () =>
      json({ error: { code: 'DUPLICATE', message: 'Name used.', fields: { name_en: 'This office already has a building with this name.' } } }, 409)
    const { wrapper } = await mountAt('/buildings?id=5')
    expect(inPanel('label[for="location_id"]')?.closest('.field')?.textContent).toContain('Change to move the building')
    const before = listCalls.length

    setValue('#location_id', '4')
    await clickInPanel('Save changes')

    expect(writes).toEqual([{ method: 'PATCH', path: '/api/v1/buildings/5', body: JSON.stringify({ location_id: 4 }) }])
    expect(inPanel('#name_en-error')?.textContent).toContain('This office already has a building with this name.')
    expect(listCalls.length).toBe(before)
    expect(wrapper.findAll('tbody tr')[0]!.text()).toContain('Head Office')
  })

  it('shows why a building cannot be turned on and keeps it inactive', async () => {
    saveAnswer = () => json({ error: { code: 'INACTIVE_REFERENCE', message: 'Turn on its office first.' } }, 409)
    detailAnswer = () => json(detail(5, { is_active: false }))
    rows = [building(5, { is_active: false })]
    const { wrapper } = await mountAt('/buildings?status=all&id=5')

    await clickInPanel('Turn on')

    expect(writes).toEqual([{ method: 'PATCH', path: '/api/v1/buildings/5', body: JSON.stringify({ is_active: true }) }])
    expect(panel()?.querySelector('[role="alert"]')?.textContent).toContain('Turn on its office first.')
    expect(panel()).not.toBeNull()
    expect(wrapper.findAll('tbody tr')[0]!.text()).toContain('Inactive')
  })

  it('is a real page in the sidebar', () => {
    const buildings = NAV_GROUPS.flatMap((g) => g.items).find((i) => i.label === 'Buildings')
    expect(buildings?.route).toBe('buildings')
  })
})
