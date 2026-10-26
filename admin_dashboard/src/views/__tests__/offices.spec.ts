import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { useToast } from '../../composables/useToast'
import { NAV_GROUPS } from '../../layouts/nav'
import { useSessionStore } from '../../stores/session'
import { confirmDialog, mountConfirmHost } from '../../test-utils/confirm'
import OfficesView from '../OfficesView.vue'

enableAutoUnmount(afterEach)

const PROVINCES = [
  { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' },
  { code: 'SIEM_REAP', name_en: 'Siem Reap', name_kh: 'សៀមរាប' },
]
const office = (id: number, changes: Record<string, unknown> = {}) => ({
  id,
  name_en: 'Head Office',
  name_kh: 'ការិយាល័យកណ្តាល',
  description: null,
  address: 'Norodom Blvd',
  province: PROVINCES[0],
  map_query: null,
  is_active: true,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
  ...changes,
})

const listCalls: string[] = []
const writes: Array<{ method: string; path: string; body: string }> = []
let saveAnswer: () => Response
let officeAnswer: () => Response | Promise<Response>

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  useToast().toasts.value = []
  listCalls.length = 0
  writes.length = 0
  saveAnswer = () => json(office(9, { name_en: 'Siem Reap Branch' }), 201)
  officeAnswer = () => json(office(3))
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      const method = init?.method ?? 'GET'
      if (method !== 'GET') {
        writes.push({ method, path: url.pathname, body: String(init?.body) })
        return saveAnswer()
      }
      if (url.pathname === '/api/v1/provinces') return json({ items: PROVINCES, total: 2 })
      if (/^\/api\/v1\/locations\/\d+$/.test(url.pathname)) return officeAnswer()
      if (url.pathname === '/api/v1/locations') {
        listCalls.push(url.search)
        return json({ items: [office(3), office(4, { name_en: 'Old Branch', name_kh: 'សាខាចាស់', is_active: false, address: null })], page: 1, size: 20, total: 2 })
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
    routes: [{ path: '/offices', name: 'offices', component: OfficesView }],
  })
  await router.push(path)
  const wrapper = mount(OfficesView, { global: { plugins: [router] }, attachTo: document.body })
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
async function submitPanel() {
  inPanel<HTMLFormElement>('form')!.dispatchEvent(new Event('submit'))
  await flushPromises()
}

describe('OfficesView', () => {
  it('asks the API with the filters from the address', async () => {
    await mountAt('/offices?province=PP&search=head')

    expect(listCalls[listCalls.length - 1]).toBe('?province=PP&search=head&is_active=true&page=1&size=20')
  })

  it('shows offices with serial, Khmer over English and province', async () => {
    const { wrapper } = await mountAt('/offices')

    const row = wrapper.findAll('tbody tr')[0]!
    expect(row.text()).toContain('OF·0003')
    expect(row.get('.name-plate').findAll('span').map((s) => s.text())).toEqual(['ការិយាល័យកណ្តាល', 'Head Office'])
    expect(row.text()).toContain('Phnom Penh')
    expect(wrapper.get('.count').text()).toBe('002 offices')
  })

  it('drops a province code the API does not know from the address', async () => {
    const { router } = await mountAt('/offices?province=XX')

    expect(router.currentRoute.value.query).toEqual({})
    expect(listCalls[listCalls.length - 1]).toBe('?is_active=true&page=1&size=20')
  })

  it('creates an office from the panel and reloads the list', async () => {
    const { wrapper, router } = await mountAt('/offices')
    await wrapper.findAll('button').find((b) => b.text() === 'New office')!.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ id: 'new' })
    expect(panel()?.textContent).toContain('New office')

    setValue('#name_kh', 'សាខាសៀមរាប')
    setValue('#name_en', 'Siem Reap Branch')
    setValue('#province', 'SIEM_REAP')
    const before = listCalls.length
    await submitPanel()

    expect(writes).toEqual([
      { method: 'POST', path: '/api/v1/locations', body: JSON.stringify({ name_kh: 'សាខាសៀមរាប', name_en: 'Siem Reap Branch', province: 'SIEM_REAP' }) },
    ])
    expect(listCalls.length).toBeGreaterThan(before)
    expect(useToast().toasts.value.map((t) => t.title)).toContain('Siem Reap Branch saved')
  })

  it('shows a duplicate name under the English name', async () => {
    saveAnswer = () => json({ error: { code: 'DUPLICATE', message: 'Name used.', fields: { name_en: 'An office already has this name.' } } }, 409)
    await mountAt('/offices?id=new')

    setValue('#name_kh', 'ការិយាល័យ')
    setValue('#name_en', 'Head Office')
    setValue('#province', 'PP')
    await submitPanel()

    expect(inPanel('#name_en-error')?.textContent).toContain('An office already has this name.')
  })

  it('keeps "Save changes" off until something changes', async () => {
    await mountAt('/offices?id=3')

    const save = [...panel()!.querySelectorAll('button')].find((b) => b.textContent?.trim() === 'Save changes')!
    expect(save.disabled).toBe(true)
    expect(panel()?.textContent).toContain('Turn off')
  })

  it('opens the panel only when the office has loaded, marking the row busy meanwhile', async () => {
    let release: () => void = () => {}
    officeAnswer = () => new Promise<Response>((resolve) => (release = () => resolve(json(office(3)))))
    const { wrapper, router } = await mountAt('/offices')

    await wrapper.findAll('tbody tr')[0]!.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ id: '3' })
    expect(panel()).toBeNull()
    expect(wrapper.findAll('tbody tr')[0]!.attributes('aria-busy')).toBe('true')

    release()
    await flushPromises()
    expect(inPanel<HTMLInputElement>('#name_en')?.value).toBe('Head Office')
    expect(wrapper.findAll('tbody tr')[0]!.attributes('aria-busy')).toBeUndefined()
  })

  it('says above the list when an office cannot open, with Try again and Close', async () => {
    officeAnswer = () => json({ error: { code: 'NOT_FOUND', message: 'Office not found.' } }, 404)
    const { wrapper, router } = await mountAt('/offices?id=3')

    expect(panel()).toBeNull()
    const alert = wrapper.get('.open-error')
    expect(alert.text()).toContain('Office not found.')
    officeAnswer = () => json(office(3))
    await alert.findAll('button').find((b) => b.text() === 'Try again')!.trigger('click')
    await flushPromises()
    expect(inPanel<HTMLInputElement>('#name_en')?.value).toBe('Head Office')

    officeAnswer = () => json({ error: { code: 'NOT_FOUND', message: 'Office not found.' } }, 404)
    await router.push('/offices?id=4')
    await flushPromises()
    await wrapper.get('.open-error').findAll('button').find((b) => b.text() === 'Close')!.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({})
  })

  it('closes only the turn-off question on Escape, keeping the panel and the typing', async () => {
    await mountAt('/offices?id=3')
    const turnOff = () => [...panel()!.querySelectorAll('button')].find((b) => b.textContent?.trim() === 'Turn off')!
    turnOff().click()
    await flushPromises()
    expect(confirmDialog()).not.toBeNull()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises()

    expect(confirmDialog()).toBeNull()
    expect(panel()).not.toBeNull()
  })

  it('will not turn off while the form has unsaved changes, and says why', async () => {
    await mountAt('/offices?id=3')
    setValue('#name_en', 'Head Office 2')
    await flushPromises()

    ;[...panel()!.querySelectorAll('button')].find((b) => b.textContent?.trim() === 'Turn off')!.click()
    await flushPromises()

    expect(confirmDialog()).toBeNull()
    expect(writes).toEqual([])
    expect(panel()?.querySelector('[role="alert"]')?.textContent).toContain('Save or cancel your changes first.')
    expect(inPanel<HTMLInputElement>('#name_en')?.value).toBe('Head Office 2')
  })

  it('is a real page in the sidebar', () => {
    const offices = NAV_GROUPS.flatMap((g) => g.items).find((i) => i.label === 'Offices')
    expect(offices?.route).toBe('offices')
  })
})
