import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { navFor } from '../../layouts/nav'
import { useSessionStore } from '../../stores/session'
import { listItem } from '../../test-utils/bookings'
import { clearDate, dateLabel, pickDate } from '../../test-utils/datePicker'
import { pickerLabel } from '../../test-utils/picker'
import BookingsView from '../BookingsView.vue'

enableAutoUnmount(afterEach)

const listCalls: string[] = []
let listAnswer: () => Response

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  listCalls.length = 0
  listAnswer = () => json({ items: [listItem(12)], page: 1, size: 20, total: 1 })
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input) => {
      const url = new URL(String(input))
      if (url.pathname === '/api/v1/bookings' || url.pathname === '/api/v1/pitika/bookings') {
        listCalls.push(url.pathname === '/api/v1/bookings' ? url.search : `pitika${url.search}`)
        return listAnswer()
      }
      if (url.pathname.startsWith('/api/v1/bookings/')) return json({ error: { code: 'NOT_FOUND', message: 'Not found.', fields: {} } }, 404)
      if (url.pathname === '/api/v1/provinces') return json({ items: [{ code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' }], total: 1 })
      return json({ items: [], page: 1, size: 100, total: 0 })
    }),
  )
})
afterEach(() => vi.unstubAllGlobals())

async function mountAt(path: string) {
  const router: Router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/bookings', name: 'bookings', component: BookingsView },
      { path: '/', name: 'home', component: BookingsView },
    ],
  })
  await router.push(path)
  const wrapper = mount(BookingsView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}

describe('BookingsView', () => {
  it('asks the API with the status from the address and shows its words', async () => {
    await mountAt('/bookings?status=PENDING_OWNER')

    expect(listCalls[listCalls.length - 1]).toBe('?status=PENDING_OWNER&page=1&size=20')
    expect(pickerLabel('filter-status')).toBe('Waiting for owner')
  })

  it('shows each booking in a row', async () => {
    const { wrapper } = await mountAt('/bookings')

    const row = wrapper.get('tbody tr')
    expect(row.text()).toContain('NBC-26-48213')
    expect(row.text()).toContain('Budget review')
    expect(row.text()).toContain('Internal')
    expect(row.text()).toContain('Mekong Room')
    expect(row.text()).toContain('Sok Dara')
    expect(row.text()).toContain('Tue 10 Nov 2026')
    expect(row.text()).toContain('+2 more')
    expect(row.text()).toContain('Waiting for Pitika')
    expect(row.find('[aria-label="Food ordered"]').exists()).toBe(true)
    expect(row.find('[aria-label="IT help asked"]').exists()).toBe(false)
    expect(wrapper.get('.count').text()).toBe('001 booking')
  })

  it('shows the API field message when a filter is refused', async () => {
    listAnswer = () =>
      json({ error: { code: 'VALIDATION_ERROR', message: 'Invalid request.', fields: { to: 'Must be on or after from.' } } }, 422)
    const { wrapper } = await mountAt('/bookings?from=2026-11-10&to=2026-11-01')

    expect(wrapper.get('.load-error').text()).toContain('Must be on or after from.')
    expect(wrapper.find('#filter-to').exists()).toBe(true)
  })

  it('hides the count and the paging while the list cannot load', async () => {
    const { wrapper, router } = await mountAt('/bookings')
    expect(wrapper.get('.count').text()).toBe('001 booking')

    listAnswer = () =>
      json({ error: { code: 'VALIDATION_ERROR', message: 'Invalid request.', fields: { to: 'Must be on or after from.' } } }, 422)
    await router.push('/bookings?from=2026-11-10&to=2026-11-01')
    await flushPromises()

    expect(wrapper.find('.load-error').exists()).toBe(true)
    expect(wrapper.find('.count').exists()).toBe(false)
    expect(wrapper.find('nav.pager').exists()).toBe(false)
  })

  it('offers Clear filters in the filter bar only when a filter is set', async () => {
    const plain = await mountAt('/bookings')
    expect(plain.wrapper.find('.filters .clear-filters').exists()).toBe(false)
    plain.wrapper.unmount()

    const { wrapper, router } = await mountAt('/bookings?status=CONFIRMED&q=budget')
    await wrapper.get('.filters .clear-filters').trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.query).toEqual({})
    expect(listCalls[listCalls.length - 1]).toBe('?page=1&size=20')
    expect(wrapper.find('.filters .clear-filters').exists()).toBe(false)
  })

  it('sets the day range with the date pickers, and To cannot be before From', async () => {
    const { router } = await mountAt('/bookings')
    expect(dateLabel('filter-from')).toBe('Any day')

    await pickDate('filter-from', '2026-11-10')
    expect(router.currentRoute.value.query).toEqual({ from: '2026-11-10' })
    expect(dateLabel('filter-from')).toBe('Tue 10 Nov 2026')

    document.querySelector<HTMLButtonElement>('#filter-to')!.click()
    await flushPromises()
    const toPicker = document.querySelector('#filter-to')!.closest('.date-picker')!
    const nine = [...toPicker.querySelectorAll<HTMLButtonElement>('.pop .day:not(.other)')].find((b) => b.textContent?.trim() === '9')
    expect(nine?.disabled).toBe(true)
    await pickDate('filter-to', '2026-11-12')
    expect(router.currentRoute.value.query).toEqual({ from: '2026-11-10', to: '2026-11-12' })
    expect(listCalls[listCalls.length - 1]).toBe('?from=2026-11-10&to=2026-11-12&page=1&size=20')

    await clearDate('filter-from')
    expect(router.currentRoute.value.query).toEqual({ to: '2026-11-12' })
  })

  it('opens a booking through the address', async () => {
    const { wrapper, router } = await mountAt('/bookings')

    await wrapper.get('tbody tr').trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.query.id).toBe('12')
  })

  it('lists the Pitika province for a Pitika, with no province filter', async () => {
    useSessionStore().user = { roles: [{ code: 'PITIKA' }, { code: 'STAFF' }] } as never
    await mountAt('/bookings')

    expect(listCalls).toEqual(['pitika?page=1&size=20'])
    expect(document.querySelector('#filter-province')).toBeNull()
    expect(document.querySelector('#filter-status')).not.toBeNull()
  })

  it('keeps the Admin list for an Admin who is also Pitika', async () => {
    useSessionStore().user = { roles: [{ code: 'ADMIN' }, { code: 'PITIKA' }] } as never
    await mountAt('/bookings')

    expect(listCalls).toEqual(['?page=1&size=20'])
    expect(document.querySelector('#filter-province')).not.toBeNull()
  })

  it('is in the Daily group of the sidebar', () => {
    const group = navFor(['ADMIN']).find((g) => g.title === 'Daily')
    expect(group?.items.map((i) => i.route)).toEqual(['bookings', 'food-list', 'home'])
  })
})
