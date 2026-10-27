import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { useToast } from '../../composables/useToast'
import { NAV_GROUPS } from '../../layouts/nav'
import { useSessionStore } from '../../stores/session'
import { mountConfirmHost } from '../../test-utils/confirm'
import RoomTypesView from '../RoomTypesView.vue'

enableAutoUnmount(afterEach)

const roomType = (id: number, changes: Record<string, unknown> = {}) => ({
  id,
  name_en: 'Meeting room',
  name_kh: 'បន្ទប់ប្រជុំ',
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
  saveAnswer = () => json(roomType(9, { name_en: 'Board room', name_kh: 'បន្ទប់ក្រុមប្រឹក្សា' }), 201)
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      const method = init?.method ?? 'GET'
      if (method !== 'GET') {
        writes.push({ method, path: url.pathname, body: String(init?.body) })
        return saveAnswer()
      }
      if (url.pathname === '/api/v1/categories/2') return json(roomType(2))
      if (url.pathname === '/api/v1/categories') {
        listCalls.push(url.search)
        return json({ items: [roomType(2), roomType(4, { name_en: 'Hall', name_kh: 'សាល', is_active: false })], page: 1, size: 20, total: 2 })
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
    routes: [{ path: '/room-types', name: 'room-types', component: RoomTypesView }],
  })
  await router.push(path)
  const wrapper = mount(RoomTypesView, { global: { plugins: [router] }, attachTo: document.body })
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

describe('RoomTypesView', () => {
  it('asks the API with the search from the address', async () => {
    await mountAt('/room-types?search=board')

    expect(listCalls[listCalls.length - 1]).toBe('?search=board&is_active=true&page=1&size=20')
  })

  it('shows room types with serial and Khmer over English', async () => {
    const { wrapper } = await mountAt('/room-types')

    const row = wrapper.findAll('tbody tr')[0]!
    expect(row.text()).toContain('RT·0002')
    expect(row.get('.name-plate').findAll('span').map((s) => s.text())).toEqual(['បន្ទប់ប្រជុំ', 'Meeting room'])
    expect(wrapper.get('.count').text()).toBe('002 room types')
  })

  it('creates a room type from the panel', async () => {
    const { wrapper, router } = await mountAt('/room-types')
    await wrapper.findAll('button').find((b) => b.text() === 'New room type')!.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ id: 'new' })

    setValue('#name_kh', 'បន្ទប់ក្រុមប្រឹក្សា')
    setValue('#name_en', 'Board room')
    await submitPanel()

    expect(writes).toEqual([
      { method: 'POST', path: '/api/v1/categories', body: JSON.stringify({ name_kh: 'បន្ទប់ក្រុមប្រឹក្សា', name_en: 'Board room', sort_order: 0 }) },
    ])
    expect(useToast().toasts.value.map((t) => t.title)).toContain('Board room saved')
  })

  it('shows a duplicate name under the English name', async () => {
    saveAnswer = () => json({ error: { code: 'DUPLICATE', message: 'Name used.', fields: { name_en: 'A room type already has this name.' } } }, 409)
    await mountAt('/room-types?id=new')

    setValue('#name_kh', 'បន្ទប់ប្រជុំ')
    setValue('#name_en', 'Meeting room')
    await submitPanel()

    expect(inPanel('#name_en-error')?.textContent).toContain('A room type already has this name.')
  })

  it('keeps "Save changes" off until something changes, and shows the Active switch', async () => {
    await mountAt('/room-types?id=2')

    const save = [...panel()!.querySelectorAll('button')].find((b) => b.textContent?.trim() === 'Save changes')!
    expect(save.disabled).toBe(true)
    expect(panel()?.querySelector('.panel-foot [role="switch"]')?.getAttribute('aria-checked')).toBe('true')
  })

  it('is a real page in the sidebar', () => {
    const item = NAV_GROUPS.flatMap((g) => g.items).find((i) => i.label === 'Room types')
    expect(item?.route).toBe('room-types')
  })
})
