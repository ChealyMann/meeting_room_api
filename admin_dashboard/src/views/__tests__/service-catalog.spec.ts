import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { useToast } from '../../composables/useToast'
import { NAV_GROUPS } from '../../layouts/nav'
import { useSessionStore } from '../../stores/session'
import { mountConfirmHost } from '../../test-utils/confirm'
import ServiceCatalogView from '../ServiceCatalogView.vue'

enableAutoUnmount(afterEach)

const service = (id: number, changes: Record<string, unknown> = {}) => ({
  id,
  name: 'Coffee break',
  description: 'Coffee and cake',
  sort_order: 1,
  is_active: true,
  version: 2,
  created_at: '2026-11-01T00:00:00Z',
  updated_at: '2026-11-01T00:00:00Z',
  ...changes,
})

const listCalls: string[] = []
const writes: Array<{ method: string; path: string; body: string }> = []
let saveAnswer: () => Response
let listItems: () => unknown[]

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  useToast().toasts.value = []
  listCalls.length = 0
  writes.length = 0
  saveAnswer = () => json(service(9, { name: 'Coffee break' }), 201)
  listItems = () => [service(3), service(5, { name: 'Lunch box', is_active: false })]
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      const method = init?.method ?? 'GET'
      if (method !== 'GET') {
        writes.push({ method, path: url.pathname, body: String(init?.body) })
        return saveAnswer()
      }
      if (url.pathname === '/api/v1/catering-packages' || url.pathname === '/api/v1/it-services') {
        listCalls.push(url.pathname + url.search)
        const items = listItems()
        return json({ items, page: 1, size: 20, total: items.length })
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
    routes: [
      { path: '/catering-packages', name: 'catering-packages', component: ServiceCatalogView, props: { kind: 'catering' } },
      { path: '/it-services', name: 'it-services', component: ServiceCatalogView, props: { kind: 'it' } },
    ],
  })
  await router.push(path)
  const kind = path.startsWith('/it-services') ? 'it' : 'catering'
  const wrapper = mount(ServiceCatalogView, { props: { kind }, global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}

const panel = () => document.body.querySelector('[role="dialog"]') as HTMLElement | null
const inPanel = <T extends Element>(selector: string) => panel()?.querySelector<T>(selector) ?? null
function setValue(selector: string, value: string) {
  const el = inPanel<HTMLInputElement>(selector)!
  el.value = value
  el.dispatchEvent(new Event('input'))
}
async function submitPanel() {
  inPanel<HTMLFormElement>('form')!.dispatchEvent(new Event('submit'))
  await flushPromises()
}
const panelButton = (text: string) => [...(panel()?.querySelectorAll('button') ?? [])].find((b) => b.textContent?.trim() === text)

describe('ServiceCatalogView', () => {
  it('asks the API with the search from the address', async () => {
    await mountAt('/catering-packages?search=tea')

    expect(listCalls[listCalls.length - 1]).toBe('/api/v1/catering-packages?search=tea&is_active=true&page=1&size=20')
  })

  it('shows serial, name and count', async () => {
    const { wrapper } = await mountAt('/catering-packages')

    const [first] = wrapper.findAll('tbody tr')
    expect(first!.text()).toContain('CP·0003')
    expect(first!.text()).toContain('Coffee break')
    expect(wrapper.get('h1').text()).toBe('Catering packages')
    expect(wrapper.get('.count').text()).toBe('002 packages')
  })

  it('creates a package', async () => {
    const { wrapper } = await mountAt('/catering-packages')
    await wrapper.findAll('button').find((b) => b.text() === 'New package')!.trigger('click')
    await flushPromises()

    setValue('#name', 'Coffee break')
    await submitPanel()

    expect(writes).toEqual([
      { method: 'POST', path: '/api/v1/catering-packages', body: JSON.stringify({ name: 'Coffee break', sort_order: 0, is_active: true }) },
    ])
    expect(useToast().toasts.value.map((t) => t.title)).toContain('Coffee break saved')
  })

  it('shows a duplicate name under Name', async () => {
    saveAnswer = () => json({ error: { code: 'DUPLICATE', message: 'Name used.', fields: { name: 'A package already has this name.' } } }, 409)
    await mountAt('/catering-packages?id=new')

    setValue('#name', 'Coffee break')
    await submitPanel()

    expect(inPanel('#name-error')?.textContent).toContain('A package already has this name.')
  })

  it('offers Reload when someone saved first', async () => {
    saveAnswer = () => json({ error: { code: 'STALE_VERSION', message: 'This package changed. Reload it.', fields: {} } }, 409)
    await mountAt('/catering-packages?id=3')

    setValue('#name', 'Tea break')
    await submitPanel()
    expect(writes[0]!.body).toBe(JSON.stringify({ name: 'Tea break', version: 2 }))
    expect(panel()?.textContent).toContain('This package changed. Reload it.')

    listItems = () => [service(3, { name: 'Coffee and tea', version: 3 })]
    const calls = listCalls.length
    panelButton('Reload')!.click()
    await flushPromises()

    expect(listCalls.length).toBeGreaterThan(calls)
    expect(inPanel<HTMLInputElement>('#name')!.value).toBe('Coffee and tea')
    expect(panel()?.textContent).not.toContain('This package changed. Reload it.')
  })

  it('shows IT services with their own words', async () => {
    const { wrapper } = await mountAt('/it-services')

    expect(listCalls[listCalls.length - 1]).toBe('/api/v1/it-services?is_active=true&page=1&size=20')
    expect(wrapper.get('h1').text()).toBe('IT services')
    expect(wrapper.findAll('button').some((b) => b.text() === 'New service')).toBe(true)
    expect(wrapper.find('tbody tr').text()).toContain('IS·0003')
  })

  it('are real pages in the sidebar', () => {
    const items = NAV_GROUPS.flatMap((g) => g.items)
    expect(items.find((i) => i.label === 'Catering packages')?.route).toBe('catering-packages')
    expect(items.find((i) => i.label === 'IT services')?.route).toBe('it-services')
  })
})
