import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { useToast } from '../../composables/useToast'
import { NAV_GROUPS } from '../../layouts/nav'
import { useSessionStore } from '../../stores/session'
import { mountConfirmHost } from '../../test-utils/confirm'
import PositionsView from '../PositionsView.vue'

enableAutoUnmount(afterEach)

const position = (id: number, changes: Record<string, unknown> = {}) => ({
  id,
  name_en: 'IT Lead',
  name_kh: 'ប្រធានព័ត៌មានវិទ្យា',
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
  saveAnswer = () => json(position(9, { name_en: 'Clerk', name_kh: 'បុគ្គលិក' }), 201)
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      const method = init?.method ?? 'GET'
      if (method !== 'GET') {
        writes.push({ method, path: url.pathname, body: String(init?.body) })
        return saveAnswer()
      }
      if (url.pathname === '/api/v1/positions/4') return json(position(4))
      if (url.pathname === '/api/v1/positions') {
        listCalls.push(url.search)
        return json({ items: [position(4), position(6, { name_en: 'Driver', name_kh: 'អ្នកបើកបរ', is_active: false })], page: 1, size: 20, total: 2 })
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
    routes: [{ path: '/positions', name: 'positions', component: PositionsView }],
  })
  await router.push(path)
  const wrapper = mount(PositionsView, { global: { plugins: [router] }, attachTo: document.body })
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

describe('PositionsView', () => {
  it('asks the API with the search from the address', async () => {
    await mountAt('/positions?search=lead')

    expect(listCalls[listCalls.length - 1]).toBe('?search=lead&is_active=true&page=1&size=20')
  })

  it('shows positions with serial and Khmer over English', async () => {
    const { wrapper } = await mountAt('/positions')

    const row = wrapper.findAll('tbody tr')[0]!
    expect(row.text()).toContain('PS·0004')
    expect(row.get('.name-plate').findAll('span').map((s) => s.text())).toEqual(['ប្រធានព័ត៌មានវិទ្យា', 'IT Lead'])
    expect(wrapper.get('.count').text()).toBe('002 positions')
  })

  it('creates a position from the panel', async () => {
    const { wrapper, router } = await mountAt('/positions')
    await wrapper.findAll('button').find((b) => b.text() === 'New position')!.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ id: 'new' })

    setValue('#name_kh', 'បុគ្គលិក')
    setValue('#name_en', 'Clerk')
    await submitPanel()

    expect(writes).toEqual([
      { method: 'POST', path: '/api/v1/positions', body: JSON.stringify({ name_kh: 'បុគ្គលិក', name_en: 'Clerk', sort_order: 0 }) },
    ])
    expect(useToast().toasts.value.map((t) => t.title)).toContain('Clerk saved')
  })

  it('shows a duplicate name under the English name', async () => {
    saveAnswer = () => json({ error: { code: 'DUPLICATE', message: 'Name used.', fields: { name_en: 'A position already has this name.' } } }, 409)
    await mountAt('/positions?id=new')

    setValue('#name_kh', 'ប្រធាន')
    setValue('#name_en', 'IT Lead')
    await submitPanel()

    expect(inPanel('#name_en-error')?.textContent).toContain('A position already has this name.')
  })

  it('keeps "Save changes" off until something changes, and can turn off', async () => {
    await mountAt('/positions?id=4')

    const save = [...panel()!.querySelectorAll('button')].find((b) => b.textContent?.trim() === 'Save changes')!
    expect(save.disabled).toBe(true)
    expect(panel()?.textContent).toContain('Turn off')
  })

  it('is a real page in the sidebar', () => {
    const item = NAV_GROUPS.flatMap((g) => g.items).find((i) => i.label === 'Positions')
    expect(item?.route).toBe('positions')
  })
})
