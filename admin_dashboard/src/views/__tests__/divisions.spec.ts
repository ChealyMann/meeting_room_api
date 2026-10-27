import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { NAV_GROUPS } from '../../layouts/nav'
import { useSessionStore } from '../../stores/session'
import { mountConfirmHost } from '../../test-utils/confirm'
import { pickerLabel } from '../../test-utils/picker'
import DivisionsView from '../DivisionsView.vue'

enableAutoUnmount(afterEach)

const PP = { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' }
const stamps = { is_active: true, created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z' }
const OFFICES = [{ id: 3, name_en: 'Head Office', name_kh: 'ការិយាល័យ', description: null, address: null, province: PP, map_query: null, ...stamps }]
const DEPARTMENTS = [
  { id: 4, location_id: 3, name_en: 'IT Department', name_kh: 'ព័ត៌មានវិទ្យា', sort_order: 1, ...stamps },
  { id: 5, location_id: 3, name_en: 'Old Department', name_kh: 'ចាស់', sort_order: 2, ...stamps, is_active: false },
]
const division = (id: number, changes: Record<string, unknown> = {}) => ({
  id,
  department_id: 4,
  name_en: 'Software',
  name_kh: 'កម្មវិធី',
  short_name: 'SW',
  sort_order: 1,
  ...stamps,
  ...changes,
})

const listCalls: string[] = []
const writes: Array<{ method: string; path: string; body: string }> = []
let saveAnswer: () => Response
let detail: ReturnType<typeof division>
let rows: unknown[]

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  listCalls.length = 0
  writes.length = 0
  detail = division(12)
  rows = [division(12), division(14, { department_id: 77, name_en: 'Lost', short_name: null })]
  saveAnswer = () => json(division(12, { name_en: 'Software 2' }))
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      const method = init?.method ?? 'GET'
      if (method !== 'GET') {
        writes.push({ method, path: url.pathname, body: String(init?.body) })
        return saveAnswer()
      }
      if (url.pathname === '/api/v1/locations') return json({ items: OFFICES, page: 1, size: 100, total: 1 })
      if (url.pathname === '/api/v1/departments') return json({ items: DEPARTMENTS, page: 1, size: 100, total: 2 })
      if (url.pathname === '/api/v1/divisions/12') return json(detail)
      if (url.pathname === '/api/v1/divisions') {
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
    routes: [{ path: '/divisions', name: 'divisions', component: DivisionsView }],
  })
  await router.push(path)
  const wrapper = mount(DivisionsView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}

const panel = () => document.body.querySelector('[role="dialog"]') as HTMLElement | null
const inPanel = <T extends Element>(selector: string) => panel()?.querySelector<T>(selector) ?? null
async function clickInPanel(text: string) {
  await flushPromises()
  ;[...panel()!.querySelectorAll('button')].find((b) => b.textContent?.trim() === text)!.click()
  await flushPromises()
}

describe('DivisionsView', () => {
  it('asks the API with the department from the address', async () => {
    await mountAt('/divisions?department_id=4')

    expect(listCalls[listCalls.length - 1]).toBe('?department_id=4&is_active=true&page=1&size=20')
  })

  it('groups the department filter by office, and filters with it', async () => {
    const { wrapper, router } = await mountAt('/divisions')

    await wrapper.get('button#filter-department').trigger('click')
    await flushPromises()
    expect(wrapper.findAll('.heading').map((h) => h.text())).toEqual(['Head Office'])
    expect(wrapper.findAll('[role="option"]').map((o) => o.text())).toEqual(['All departments', 'IT Department'])

    await wrapper.findAll('[role="option"]').find((o) => o.text() === 'IT Department')!.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ department_id: '4' })
  })

  it('still loads for a department that is gone, and says so', async () => {
    const { wrapper } = await mountAt('/divisions?department_id=99')

    expect(wrapper.get('button#filter-department').text()).toBe('Unknown department')
  })

  it('shows serial, names, department and office', async () => {
    const { wrapper } = await mountAt('/divisions')

    const [first, second] = wrapper.findAll('tbody tr')
    expect(first!.text()).toContain('DV·0012')
    expect(first!.get('.name-plate .en').text()).toBe('Software SW')
    expect(first!.text()).toContain('IT Department')
    expect(first!.text()).toContain('Head Office')
    expect(second!.text()).toContain('#77')
    expect(wrapper.get('.count').text()).toBe('002 divisions')
  })

  it('keeps an off department in the select and sends only what changed', async () => {
    detail = division(12, { department_id: 5 })
    await mountAt('/divisions?id=12')

    const select = document.getElementById('department_id')!
    expect(select.closest('.field')?.textContent).toContain("Its users' province follows the new department's office.")
    expect(select.getAttribute('aria-describedby')).toContain('move-help')
    expect(pickerLabel('department_id')).toBe('Old Department (off)')

    const name = inPanel<HTMLInputElement>('#name_en')!
    name.value = 'Software 2'
    name.dispatchEvent(new Event('input'))
    await clickInPanel('Save changes')

    expect(writes).toEqual([{ method: 'PATCH', path: '/api/v1/divisions/12', body: JSON.stringify({ name_en: 'Software 2' }) }])
  })

  it('shows why a division cannot be turned on and keeps it inactive', async () => {
    saveAnswer = () => json({ error: { code: 'INACTIVE_REFERENCE', message: 'Turn on its department first.' } }, 409)
    detail = division(12, { is_active: false })
    rows = [division(12, { is_active: false })]
    const { wrapper } = await mountAt('/divisions?status=all&id=12')

    panel()!.querySelector<HTMLElement>('.panel-foot [role="switch"]')!.click()
    await flushPromises()

    expect(writes).toEqual([{ method: 'PATCH', path: '/api/v1/divisions/12', body: JSON.stringify({ is_active: true }) }])
    expect(panel()?.querySelector('[role="alert"]')?.textContent).toContain('Turn on its department first.')
    expect(wrapper.findAll('tbody tr')[0]!.text()).toContain('Inactive')
  })

  it('is a real page in the sidebar', () => {
    const item = NAV_GROUPS.flatMap((g) => g.items).find((i) => i.label === 'Divisions')
    expect(item?.route).toBe('divisions')
  })
})
