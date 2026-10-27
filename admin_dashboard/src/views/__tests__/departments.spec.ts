import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { NAV_GROUPS } from '../../layouts/nav'
import { useSessionStore } from '../../stores/session'
import { mountConfirmHost } from '../../test-utils/confirm'
import DepartmentsView from '../DepartmentsView.vue'

enableAutoUnmount(afterEach)

const PP = { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' }
const stamps = { is_active: true, created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z' }
const office = (id: number, name_en: string) => ({ id, name_en, name_kh: `ការិយាល័យ ${id}`, description: null, address: null, province: PP, map_query: null, ...stamps })
const OFFICES = [office(3, 'Head Office'), office(4, 'Siem Reap Branch')]
const department = (id: number, changes: Record<string, unknown> = {}) => ({
  id,
  location_id: 3,
  name_en: 'IT Department',
  name_kh: 'នាយកដ្ឋានព័ត៌មានវិទ្យា',
  sort_order: 1,
  ...stamps,
  ...changes,
})

const listCalls: string[] = []
const writes: Array<{ method: string; path: string; body: string }> = []
let saveAnswer: () => Response

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  listCalls.length = 0
  writes.length = 0
  saveAnswer = () => json(department(9), 201)
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      const method = init?.method ?? 'GET'
      if (method !== 'GET') {
        writes.push({ method, path: url.pathname, body: String(init?.body) })
        return saveAnswer()
      }
      if (url.pathname === '/api/v1/locations') return json({ items: OFFICES, page: 1, size: 100, total: 2 })
      if (url.pathname === '/api/v1/departments/3') return json(department(3))
      if (url.pathname === '/api/v1/departments') {
        listCalls.push(url.search)
        return json({ items: [department(3), department(7, { location_id: 99, name_en: 'Audit' })], page: 1, size: 20, total: 2 })
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
    routes: [{ path: '/departments', name: 'departments', component: DepartmentsView }],
  })
  await router.push(path)
  const wrapper = mount(DepartmentsView, { global: { plugins: [router] }, attachTo: document.body })
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

describe('DepartmentsView', () => {
  it('asks the API with the office from the address', async () => {
    await mountAt('/departments?location_id=3')

    expect(listCalls[listCalls.length - 1]).toBe('?location_id=3&is_active=true&page=1&size=20')
  })

  it('shows serial, Khmer over English and the office name', async () => {
    const { wrapper } = await mountAt('/departments')

    const [first, second] = wrapper.findAll('tbody tr')
    expect(first!.text()).toContain('DP·0003')
    expect(first!.get('.name-plate').findAll('span').map((s) => s.text())).toEqual(['នាយកដ្ឋានព័ត៌មានវិទ្យា', 'IT Department'])
    expect(first!.text()).toContain('Head Office')
    expect(second!.text()).toContain('#99')
    expect(wrapper.get('.count').text()).toBe('002 departments')
  })

  it('filters by office with the search picker', async () => {
    const { wrapper, router } = await mountAt('/departments')

    await pick(wrapper, 'filter-office', 'Siem Reap Branch')

    expect(router.currentRoute.value.query).toEqual({ location_id: '4' })
  })

  it('pre-sets the filtered office in a new department', async () => {
    const { wrapper, router } = await mountAt('/departments?location_id=3')
    await wrapper.findAll('button').find((b) => b.text() === 'New department')!.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.query).toEqual({ location_id: '3', id: 'new' })
    expect(inPanel<HTMLSelectElement>('#location_id')!.value).toBe('3')
  })

  it('shows a duplicate name under the English name when a move is refused', async () => {
    saveAnswer = () =>
      json({ error: { code: 'DUPLICATE', message: 'Name used.', fields: { name_en: 'This office already has a department with this name.' } } }, 409)
    await mountAt('/departments?id=3')
    expect(inPanel('label[for="location_id"]')?.closest('.field')?.textContent).toContain("Its users' province changes with it.")
    const before = listCalls.length

    const select = inPanel<HTMLSelectElement>('#location_id')!
    select.value = '4'
    select.dispatchEvent(new Event('change'))
    await flushPromises()
    ;[...panel()!.querySelectorAll('button')].find((b) => b.textContent?.trim() === 'Save changes')!.click()
    await flushPromises()

    expect(writes).toEqual([{ method: 'PATCH', path: '/api/v1/departments/3', body: JSON.stringify({ location_id: 4 }) }])
    expect(inPanel('#name_en-error')?.textContent).toContain('This office already has a department with this name.')
    expect(listCalls.length).toBe(before)
  })

  it('is a real page in the sidebar', () => {
    const item = NAV_GROUPS.flatMap((g) => g.items).find((i) => i.label === 'Departments')
    expect(item?.route).toBe('departments')
  })
})
