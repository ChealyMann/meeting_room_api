import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { useSessionStore } from '../../../stores/session'
import { listItem } from '../../../test-utils/bookings'
import DecidedList from '../DecidedList.vue'

enableAutoUnmount(afterEach)

const governor = { ...listItem(1).room, id: 13, name_en: 'Governor Room', name_kh: 'បន្ទប់ទេសាភិបាល' }
const decided = (id: number, decided_at: string, changes: Record<string, unknown> = {}) => ({
  ...listItem(id, { display_status: 'CONFIRMED', status: 'CONFIRMED', ...changes }),
  decided_at,
  decision_note: null,
})

// Now: Thu 5 Nov 2026, 13:40 in Phnom Penh.
const APPROVED = [
  decided(31, '2026-11-05T06:38:00Z', {
    meeting_title: 'Board risk review',
    reference_code: 'NBC-26-39730',
    room: governor,
    display_status: 'PENDING_OWNER',
    status: 'PENDING_OWNER',
    first_session: { id: 1, date: '2026-11-10', start_time: '14:00', end_time: '15:30' },
    requester: { id: 8, name_en: 'Touch Bunthoeun', name_kh: 'ទូច ប៊ុនធឿន' },
  }),
  { ...decided(32, '2026-11-05T06:36:00Z', { reference_code: 'NBC-26-57305' }), decision_note: 'Fine' },
  decided(33, '2026-11-04T09:00:00Z', { display_status: 'REJECTED', status: 'REJECTED' }),
]
const REJECTED = [{ ...decided(41, '2026-11-05T03:12:00Z', { display_status: 'REJECTED', status: 'REJECTED' }), decision_note: 'Room is closed for repair' }]

const calls: string[] = []
let answer: { items: unknown[]; total: number }

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-05T06:40:00Z'))
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  calls.length = 0
  answer = { items: APPROVED, total: APPROVED.length }
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input) => {
      const url = new URL(String(input))
      calls.push(`${url.pathname}${url.search}`)
      if (url.pathname === '/api/v1/pitika/bookings/decided') return json({ ...answer, page: 1, size: 20 })
      const one = /^\/api\/v1\/bookings\/(\d+)$/.exec(url.pathname)
      if (one) {
        const base = [...APPROVED, ...REJECTED].find((b) => b.id === Number(one[1]))!
        return json({
          ...base,
          requester_info: { name_en: 'Sok Dara', division: 'Payments' },
          meeting_purpose: null,
          private_justification: null,
          participant_emails: [],
          sessions: [base.first_session],
          last_end: { date: base.first_session.date, time: base.first_session.end_time },
          catering: null,
          it: null,
          reviews: [],
          rejection: null,
          cancelled_at: null,
          cancel_reason: null,
          cancelled_by: null,
        })
      }
      return json({ items: [], page: 1, size: 20, total: 0 })
    }),
  )
})
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

async function mountList(decision: 'APPROVED' | 'REJECTED', path = '/review?tab=approved') {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/review', name: 'review', component: DecidedList }] })
  await router.push(path)
  const wrapper = mount(DecidedList, { props: { decision, covers: {} }, global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}

const card = (wrapper: Awaited<ReturnType<typeof mountList>>['wrapper'], id: number) => wrapper.get(`[data-booking="${id}"]`)
const panel = () => document.body.querySelector('.review-panel')?.closest('[role="dialog"]') as HTMLElement | null

describe('DecidedList', () => {
  it('asks for my approvals, 20 a page', async () => {
    await mountList('APPROVED')
    expect(calls).toContain('/api/v1/pitika/bookings/decided?decision=APPROVED&page=1&size=20')
  })

  it('groups the cards under decision days with their counts', async () => {
    const { wrapper } = await mountList('APPROVED')

    const heads = wrapper.findAll('.day-head').map((h) => [h.get('h2').text(), h.get('.n').text()])
    expect(heads).toEqual([
      ['Today · Thu 5 Nov', '2 approved'],
      ['Yesterday · Wed 4 Nov', '1 approved'],
    ])
  })

  it('shows the decision, the booking, its number, where it is now and when I decided', async () => {
    const { wrapper } = await mountList('APPROVED')

    const c = card(wrapper, 31)
    expect(c.find('.mark.ok').exists()).toBe(true)
    expect(c.get('.title').text()).toContain('Board risk review')
    expect(c.get('.ref').text()).toBe('NBC-26-39730')
    expect(c.get('.meta').text()).toBe('Governor Room · Tue 10 Nov, 14:00 · Touch Bunthoeun')
    expect(c.get('.now').text()).toBe('Room owner next')
    expect(c.get('.now').classes()).toContain('warn')
    expect(c.get('.time').text()).toBe('13:38')
    expect(card(wrapper, 32).get('.note').text()).toBe('Notes: “Fine”')
  })

  it('lets a screen reader read the whole card, not only its number', async () => {
    const { wrapper } = await mountList('APPROVED')
    expect(card(wrapper, 31).attributes('aria-label')).toBeUndefined()
  })

  it('shows a booking I approved that was rejected later with a crimson Rejected pill', async () => {
    const { wrapper } = await mountList('APPROVED')

    expect(card(wrapper, 33).get('.now').text()).toBe('Rejected')
    expect(card(wrapper, 33).get('.now').classes()).toContain('no')
  })

  it('shows the reason on a rejection', async () => {
    answer = { items: REJECTED, total: 1 }
    const { wrapper } = await mountList('REJECTED', '/review?tab=rejected')

    expect(calls).toContain('/api/v1/pitika/bookings/decided?decision=REJECTED&page=1&size=20')
    expect(card(wrapper, 41).find('.mark.no').exists()).toBe(true)
    expect(card(wrapper, 41).get('.note').text()).toBe('Reason: “Room is closed for repair”')
    expect(wrapper.get('.day-head .n').text()).toBe('1 rejected')
  })

  it.each([
    ['APPROVED', 'No approved bookings yet', 'Bookings you approve show here.'],
    ['REJECTED', 'No rejected bookings', 'Bookings you reject show here.'],
  ] as const)('says when there is nothing on %s', async (decision, title, text) => {
    answer = { items: [], total: 0 }
    const { wrapper } = await mountList(decision)

    expect(wrapper.text()).toContain(title)
    expect(wrapper.text()).toContain(text)
  })

  it('says when nothing matches the filters, with Clear filters', async () => {
    answer = { items: [], total: 0 }
    const { wrapper, router } = await mountList('APPROVED', '/review?tab=approved&q=zzz')

    expect(wrapper.text()).toContain('No bookings match')
    await wrapper.findAll('button').find((b) => b.text() === 'Clear filters')!.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/review?tab=approved')
  })

  it('opens a card read only: where it is now, and only Close', async () => {
    const { wrapper, router } = await mountList('APPROVED')

    await card(wrapper, 32).trigger('keydown', { key: 'Enter' })
    await flushPromises()

    expect(router.currentRoute.value.query.id).toBe('32')
    expect(calls).toContain('/api/v1/bookings/32')
    expect(panel()?.textContent).toContain('Confirmed')
    expect(panel()?.textContent).not.toContain('Waiting for Pitika')
    const buttons = [...(panel()?.querySelectorAll('button') ?? [])].map((b) => b.textContent?.trim())
    expect(buttons).not.toContain('Approve')
    expect(buttons).not.toContain('Reject')
    expect(buttons).toContain('Close')
  })

  it('pages after 20', async () => {
    answer = { items: APPROVED, total: 25 }
    const { wrapper } = await mountList('APPROVED')

    expect(wrapper.get('.range').text()).toContain('25')
    await mountList('APPROVED', '/review?tab=approved&page=2')
    expect(calls).toContain('/api/v1/pitika/bookings/decided?decision=APPROVED&page=2&size=20')
  })
})
