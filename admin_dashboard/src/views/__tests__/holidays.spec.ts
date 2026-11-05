import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { useConfirm } from '../../composables/useConfirm'
import { useToast } from '../../composables/useToast'
import { NAV_GROUPS } from '../../layouts/nav'
import { useSessionStore } from '../../stores/session'
import { pickDate } from '../../test-utils/datePicker'
import { mountConfirmHost } from '../../test-utils/confirm'
import HolidaysView from '../HolidaysView.vue'

enableAutoUnmount(afterEach)

const holiday = (id: number, changes: Record<string, unknown> = {}) => ({
  id,
  holiday_date: '2026-11-09',
  name_km: 'ទិវាឯករាជ្យជាតិ',
  name_en: 'Independence Day',
  remarks: null,
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
  saveAnswer = () => json(holiday(9), 201)
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      const method = init?.method ?? 'GET'
      if (method !== 'GET') {
        writes.push({ method, path: url.pathname, body: String(init?.body) })
        return saveAnswer()
      }
      if (url.pathname === '/api/v1/public-holidays') {
        listCalls.push(url.search)
        return json({
          items: [holiday(4), holiday(6, { holiday_date: '2026-12-10', name_km: 'ទិវាសិទ្ធិមនុស្ស', name_en: null, remarks: 'Bank closed' })],
          page: 1,
          size: 20,
          total: 2,
        })
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
    routes: [{ path: '/public-holidays', name: 'public-holidays', component: HolidaysView }],
  })
  await router.push(path)
  const wrapper = mount(HolidaysView, { global: { plugins: [router] }, attachTo: document.body })
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

describe('HolidaysView', () => {
  it('asks the API with the year from the address and no status', async () => {
    await mountAt('/public-holidays?year=2026')

    expect(listCalls[listCalls.length - 1]).toBe('?year=2026&page=1&size=20')
  })

  it('shows serial, date and both names', async () => {
    const { wrapper } = await mountAt('/public-holidays')

    const [first, second] = wrapper.findAll('tbody tr')
    expect(first!.text()).toContain('PH·0004')
    expect(first!.text()).toContain('Mon 9 Nov 2026')
    expect(first!.text()).toContain('ទិវាឯករាជ្យជាតិ')
    expect(first!.text()).toContain('Independence Day')
    expect(second!.text()).toContain('—')
    expect(second!.text()).toContain('Bank closed')
    expect(wrapper.get('.count').text()).toBe('002 holidays')
  })

  it('filters by year with the year buttons', async () => {
    const { wrapper, router } = await mountAt('/public-holidays')
    const thisYear = String(new Date().getFullYear())

    await wrapper.findAll('.segmented button').find((b) => b.text() === thisYear)!.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.query.year).toBe(thisYear)
  })

  it('adds a holiday with an empty English name sent as null', async () => {
    await mountAt('/public-holidays?id=new')

    await pickDate('holiday_date', '2027-01-07')
    setValue('#name_km', 'ទិវាជ័យជម្នះ')
    await submitPanel()

    expect(writes).toEqual([
      {
        method: 'POST',
        path: '/api/v1/public-holidays',
        body: JSON.stringify({ holiday_date: '2027-01-07', name_km: 'ទិវាជ័យជម្នះ', name_en: null, remarks: null }),
      },
    ])
  })

  it('needs a date and a Khmer name before sending', async () => {
    await mountAt('/public-holidays?id=new')

    await submitPanel()

    expect(writes).toEqual([])
    expect(inPanel('#holiday_date-error')?.textContent).toContain('Pick the date.')
    expect(inPanel('#name_km-error')?.textContent).toContain('Enter the Khmer name.')
  })

  it('shows a taken date under Date', async () => {
    saveAnswer = () =>
      json({ error: { code: 'DUPLICATE', message: 'Taken.', fields: { holiday_date: 'This date already has a holiday.' } } }, 409)
    await mountAt('/public-holidays?id=new')

    await pickDate('holiday_date', '2026-11-09')
    setValue('#name_km', 'ទិវាឯករាជ្យជាតិ')
    await submitPanel()

    expect(inPanel('#holiday_date-error')?.textContent).toContain('This date already has a holiday.')
  })

  it('sends only what changed', async () => {
    saveAnswer = () => json(holiday(4, { remarks: 'Half day' }))
    await mountAt('/public-holidays?id=4')

    setValue('#remarks', 'Half day')
    await submitPanel()

    expect(writes).toEqual([{ method: 'PATCH', path: '/api/v1/public-holidays/4', body: JSON.stringify({ remarks: 'Half day' }) }])
  })

  it('deletes after the confirm', async () => {
    saveAnswer = () => new Response(null, { status: 204 })
    await mountAt('/public-holidays?id=4')

    const del = [...panel()!.querySelectorAll('button')].find((b) => b.textContent?.includes('Delete'))!
    del.click()
    await flushPromises()
    expect(useConfirm().current.value?.confirmLabel).toBe('Delete holiday')
    useConfirm().answer(true)
    await flushPromises()

    expect(writes).toEqual([{ method: 'DELETE', path: '/api/v1/public-holidays/4', body: 'undefined' }])
    expect(useToast().toasts.value.map((t) => t.title)).toContain('Independence Day deleted')
  })

  it('is a real page in the sidebar', () => {
    const entry = NAV_GROUPS.flatMap((g) => g.items).find((i) => i.label === 'Public holidays')
    expect(entry?.route).toBe('public-holidays')
  })
})
