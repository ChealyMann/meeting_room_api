import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { useToast } from '../../composables/useToast'
import { NAV_GROUPS } from '../../layouts/nav'
import { useSessionStore } from '../../stores/session'
import { mountConfirmHost } from '../../test-utils/confirm'
import EquipmentView from '../EquipmentView.vue'

enableAutoUnmount(afterEach)

const item = (id: number, changes: Record<string, unknown> = {}) => ({
  id,
  name: 'Projector',
  icon: 'projector',
  sort_order: 1,
  is_active: true,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
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
  useToast().toasts.value = []
  listCalls.length = 0
  writes.length = 0
  saveAnswer = () => json(item(9), 201)
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      const method = init?.method ?? 'GET'
      if (method !== 'GET') {
        writes.push({ method, path: url.pathname, body: String(init?.body) })
        return saveAnswer()
      }
      if (url.pathname === '/api/v1/equipment/4') return json(item(4))
      if (url.pathname === '/api/v1/equipment') {
        listCalls.push(url.search)
        return json({ items: [item(4), item(6, { name: 'Old screen', icon: 'old-icon', is_active: false })], page: 1, size: 20, total: 2 })
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
    routes: [{ path: '/equipment', name: 'equipment', component: EquipmentView }],
  })
  await router.push(path)
  const wrapper = mount(EquipmentView, { global: { plugins: [router] }, attachTo: document.body })
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

describe('EquipmentView', () => {
  it('asks the API with the search from the address', async () => {
    await mountAt('/equipment?search=mic')

    expect(listCalls[listCalls.length - 1]).toBe('?search=mic&is_active=true&page=1&size=20')
  })

  it('shows serial, icon and name', async () => {
    const { wrapper } = await mountAt('/equipment')

    const [first, second] = wrapper.findAll('tbody tr')
    expect(first!.text()).toContain('EQ·0004')
    expect(first!.text()).toContain('Projector')
    expect(first!.find('.col-icon svg').exists()).toBe(true)
    expect(second!.find('.col-icon .unknown').exists()).toBe(true)
    expect(wrapper.get('.count').text()).toBe('002 items')
  })

  it('creates an item with an icon', async () => {
    const { wrapper } = await mountAt('/equipment')
    await wrapper.findAll('button').find((b) => b.text() === 'New item')!.trigger('click')
    await flushPromises()

    setValue('#name', 'Projector')
    inPanel<HTMLElement>('[role="radio"][aria-label="Projector"]')!.click()
    await flushPromises()
    await submitPanel()

    expect(writes).toEqual([
      { method: 'POST', path: '/api/v1/equipment', body: JSON.stringify({ name: 'Projector', icon: 'projector', sort_order: 0 }) },
    ])
    expect(useToast().toasts.value.map((t) => t.title)).toContain('Projector saved')
  })

  it('shows a duplicate name under Name', async () => {
    saveAnswer = () => json({ error: { code: 'DUPLICATE', message: 'Name used.', fields: { name: 'An item already has this name.' } } }, 409)
    await mountAt('/equipment?id=new')

    setValue('#name', 'Projector')
    await submitPanel()

    expect(inPanel('#name-error')?.textContent).toContain('An item already has this name.')
  })

  it('is a real page in the sidebar', () => {
    const entry = NAV_GROUPS.flatMap((g) => g.items).find((i) => i.label === 'Equipment')
    expect(entry?.route).toBe('equipment')
  })
})
