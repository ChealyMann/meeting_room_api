import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { useToast } from '../../composables/useToast'
import { useSessionStore } from '../../stores/session'
import { listItem } from '../../test-utils/bookings'
import BookingsView from '../BookingsView.vue'

enableAutoUnmount(afterEach)

const session = (id: number, date: string) => ({ id, date, start_time: '09:00', end_time: '10:30' })

const detail = (changes: Record<string, unknown> = {}) => ({
  ...listItem(12, { status: 'CONFIRMED', display_status: 'CONFIRMED', route: 'R2' }),
  requester_info: {
    name_en: 'Sok Dara',
    name_kh: 'សុខ ដារា',
    staff_id: 'NBC0042',
    position: 'Officer',
    division: 'Payments',
    department: 'Operations',
    office: 'Head Office',
    email: 'dara@nbc.gov.kh',
    phone: null,
  },
  meeting_purpose: 'Plan the 2027 budget',
  private_justification: 'Board members attend',
  participant_emails: ['a@nbc.gov.kh'],
  sessions: [session(1, '2026-11-10'), session(2, '2026-11-11'), session(3, '2026-11-12')],
  last_end: { date: '2026-11-12', time: '10:30' },
  catering: null,
  it: null,
  reviews: [
    { stage: 'PITIKA', decision: 'APPROVED', reviewer: { id: 9, name_en: 'Chan Pitika' }, notes: 'Fine', reviewed_at: '2026-11-04T02:00:00Z' },
  ],
  rejection: null,
  cancelled_at: null,
  cancel_reason: null,
  updated_at: '2026-11-04T02:00:00Z',
  ...changes,
})

const calls: string[] = []
const bodies: string[] = []
let current: ReturnType<typeof detail>
let doorPass: Record<string, unknown>
let actions: Record<string, unknown>
let actionAnswer: () => Response
const NO_ACTIONS = { cancel: false, approve: false, reject: false, stage: null }

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  calls.length = 0
  current = detail()
  doorPass = { passcode: 'NBC-48213', expires_at: '2026-11-12T03:30:00Z', expired: false }
  actions = NO_ACTIONS
  bodies.length = 0
  actionAnswer = () => {
    current = { ...current, status: 'CANCELLED', display_status: 'CANCELLED', version: 2 }
    return json(current)
  }
  URL.createObjectURL = vi.fn<typeof URL.createObjectURL>(() => 'blob:1')
  URL.revokeObjectURL = vi.fn<typeof URL.revokeObjectURL>()
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      calls.push(`${init?.method ?? 'GET'} ${url.pathname}`)
      if (url.pathname === '/api/v1/admin/bookings/12/actions') return json(actions)
      if (url.pathname.startsWith('/api/v1/admin/bookings/12/')) {
        bodies.push(String(init?.body))
        return actionAnswer()
      }
      if (url.pathname === '/api/v1/bookings/12/door-pass') return json(doorPass)
      if (url.pathname === '/api/v1/bookings/12/ics') return new Response('BEGIN:VCALENDAR', { headers: { 'Content-Type': 'text/calendar' } })
      if (url.pathname === '/api/v1/bookings/12') return json(current)
      if (url.pathname === '/api/v1/bookings') return json({ items: [listItem(12)], page: 1, size: 20, total: 1 })
      return json({ items: [], page: 1, size: 100, total: 0 })
    }),
  )
})
afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

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

const panel = () => document.body.querySelector('[role="dialog"]') as HTMLElement | null
const eye = (label: string) => panel()?.querySelector<HTMLElement>(`button[aria-label="${label}"]`) ?? undefined
const panelButton = (text: string) => [...(panel()?.querySelectorAll('button') ?? [])].find((b) => b.textContent?.trim() === text)
async function click(el: HTMLElement | undefined) {
  el!.click()
  await flushPromises()
}

describe('BookingPanel', () => {
  it('opens the booking from the address', async () => {
    await mountAt('/bookings?id=12')

    expect(calls).toContain('GET /api/v1/bookings/12')
    expect(panel()?.textContent).toContain('Budget review')
    expect(panel()?.textContent).toContain('NBC-26-48213')
    expect(panel()?.textContent).toContain('Private room, owner approves')
    expect(panel()?.textContent).toContain('NBC0042')
  })

  it('lists every session', async () => {
    await mountAt('/bookings?id=12')

    await click(panel()!.querySelector<HTMLElement>('#tab-sessions')!)

    expect(panel()!.querySelectorAll('#tabpanel-sessions li')).toHaveLength(3)
    expect(panel()!.querySelector('#tabpanel-sessions')!.textContent).toContain('Ends Thu 12 Nov 2026 10:30')
  })

  it('says when no food or IT help was asked', async () => {
    await mountAt('/bookings?id=12')

    const services = panel()!.querySelector('#tabpanel-services')!.textContent
    expect(services).toContain('No food ordered.')
    expect(services).toContain('No IT help asked.')
  })

  it('shows the reviews and the rejection in History', async () => {
    current = detail({
      status: 'REJECTED',
      display_status: 'REJECTED',
      rejection: { rejected_by: 'OWNER', actor: { id: 5, name_en: 'Keo Owner' }, reason: 'Room is closed that day.', decided_at: '2026-11-04T03:00:00Z' },
    })
    await mountAt('/bookings?id=12')

    const history = panel()!.querySelector('#tabpanel-history')!.textContent
    expect(history).toContain('Pitika approved')
    expect(history).toContain('Chan Pitika')
    expect(history).toContain('Rejected by the room owner')
    expect(history).toContain('Room is closed that day.')
  })

  it('shows a rejection once, though the API also sends it as a review', async () => {
    const reason = 'Room is closed that day.'
    current = detail({
      status: 'REJECTED',
      display_status: 'REJECTED',
      reviews: [
        { stage: 'PITIKA', decision: 'APPROVED', reviewer: { id: 9, name_en: 'Chan Pitika' }, notes: 'Fine', reviewed_at: '2026-11-04T02:00:00Z' },
        { stage: 'OWNER', decision: 'REJECTED', reviewer: { id: 5, name_en: 'Keo Owner' }, notes: reason, reviewed_at: '2026-11-04T03:00:00Z' },
      ],
      rejection: { rejected_by: 'OWNER', actor: { id: 5, name_en: 'Keo Owner' }, reason, decided_at: '2026-11-04T03:00:00Z' },
    })
    await mountAt('/bookings?id=12')

    const history = panel()!.querySelector('#tabpanel-history')!
    expect(history.querySelectorAll('li')).toHaveLength(3)
    expect(history.textContent!.split(reason)).toHaveLength(2)
    expect(history.textContent).toContain('Rejected by the room owner')
  })

  it('shows the door pass only when asked', async () => {
    await mountAt('/bookings?id=12')
    expect(panel()?.textContent).not.toContain('NBC-48213')
    expect(calls).not.toContain('GET /api/v1/bookings/12/door-pass')

    await click(eye('Show door pass'))

    expect(calls).toContain('GET /api/v1/bookings/12/door-pass')
    expect(panel()?.querySelector('.door-pass .secret-code')?.textContent).toBe('NBC-48213')
    expect(panel()?.querySelector('.door-pass')?.textContent).not.toContain('Valid until')
    expect(panel()?.querySelector('.door-pass')?.textContent).not.toContain('Expired')

    await click(eye('Hide door pass'))
    expect(panel()?.textContent).not.toContain('NBC-48213')
  })

  it('marks an expired door pass', async () => {
    doorPass = { ...doorPass, expired: true }
    await mountAt('/bookings?id=12')

    await click(eye('Show door pass'))

    expect(panel()?.querySelector('.door-pass')?.textContent).toContain('Expired')
  })

  it('has no door pass button before the booking is confirmed', async () => {
    current = detail({ status: 'PENDING_PITIKA', display_status: 'PENDING_PITIKA' })
    await mountAt('/bookings?id=12')

    expect(eye('Show door pass')).toBeUndefined()
  })

  it('downloads the calendar file', async () => {
    const revokedAtClick: boolean[] = []
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
      revokedAtClick.push(vi.mocked(URL.revokeObjectURL).mock.calls.length > 0 || !this.isConnected)
    })
    await mountAt('/bookings?id=12')

    await click(panelButton('Calendar file'))

    expect(calls).toContain('GET /api/v1/bookings/12/ics')
    expect(URL.createObjectURL).toHaveBeenCalled()
    // Safari needs the link in the page and the file URL alive until the download starts.
    expect(revokedAtClick).toEqual([false])
    await new Promise((done) => setTimeout(done, 0))
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:1')
  })

  it('is read only', async () => {
    await mountAt('/bookings?id=12')

    const labels = [...panel()!.querySelectorAll('button')].map((b) => b.textContent?.trim())
    for (const word of ['Save changes', 'Approve', 'Reject', 'Cancel booking', 'Edit']) {
      expect(labels).not.toContain(word)
    }
  })
})

describe('BookingPanel Admin actions', () => {
  const step = () => panel()!.querySelector('.action-step') as HTMLElement | null
  const reason = () => step()!.querySelector('textarea') as HTMLTextAreaElement

  it('shows only the actions the API allows', async () => {
    actions = { cancel: true, approve: false, reject: false, stage: null }
    await mountAt('/bookings?id=12')

    expect(calls).toContain('GET /api/v1/admin/bookings/12/actions')
    expect(panelButton('Cancel booking')).toBeDefined()
    expect(panelButton('Approve')).toBeUndefined()
    expect(panelButton('Reject')).toBeUndefined()
  })

  it('cancels after a confirm step, with no reason', async () => {
    actions = { cancel: true, approve: false, reject: false, stage: null }
    await mountAt('/bookings?id=12')

    await click(panelButton('Cancel booking'))
    expect(step()?.textContent).toContain('Cancel this booking?')
    await click(step()!.querySelector<HTMLElement>('button.confirm')!)

    expect(calls).toContain('POST /api/v1/admin/bookings/12/cancel')
    expect(bodies).toEqual([JSON.stringify({ reason: null, version: 1 })])
    expect(useToast().toasts.value.map((t) => t.title)).toContain('NBC-26-48213 cancelled')
    expect(panel()?.textContent).toContain('Cancelled')
    expect(step()).toBeNull()
  })

  it('shows a refusal in the step and reloads the actions', async () => {
    actions = { cancel: true, approve: false, reject: false, stage: null }
    actionAnswer = () => json({ error: { code: 'INVALID_TRANSITION', message: 'This booking has ended.', fields: {} } }, 409)
    await mountAt('/bookings?id=12')

    await click(panelButton('Cancel booking'))
    actions = NO_ACTIONS
    await click(step()!.querySelector<HTMLElement>('button.confirm')!)

    expect(step()?.textContent).toContain('This booking has ended.')
    expect(calls.filter((c) => c.endsWith('/actions'))).toHaveLength(2)
    expect(step()!.querySelector<HTMLButtonElement>('button.confirm')!.disabled).toBe(true)
    await click(panelButton('Back'))
    expect([...panel()!.querySelectorAll('.panel-foot button')].map((b) => b.textContent?.trim())).not.toContain('Cancel booking')
  })

  it('reloads the booking after someone else changed it, so a retry sends the new version', async () => {
    actions = { cancel: true, approve: false, reject: false, stage: null }
    let stale = true
    actionAnswer = () => {
      if (stale) {
        stale = false
        current = { ...current, status: 'CONFIRMED', display_status: 'CONFIRMED', version: 2 }
        return json({ error: { code: 'STALE_VERSION', message: 'This booking changed. Reload it.', fields: {} } }, 409)
      }
      current = { ...current, status: 'CANCELLED', display_status: 'CANCELLED', version: 3 }
      return json(current)
    }
    await mountAt('/bookings?id=12')
    const detailReads = () => calls.filter((c) => c === 'GET /api/v1/bookings/12').length
    const before = detailReads()

    await click(panelButton('Cancel booking'))
    await click(step()!.querySelector<HTMLElement>('button.confirm')!)
    expect(step()?.textContent).toContain('This booking changed. Reload it.')
    expect(detailReads()).toBe(before + 1)

    await click(step()!.querySelector<HTMLElement>('button.confirm')!)
    expect(bodies).toEqual([JSON.stringify({ reason: null, version: 1 }), JSON.stringify({ reason: null, version: 2 })])
    expect(panel()?.textContent).toContain('Cancelled')
  })

  it('shows a 403 on approve and reloads the actions', async () => {
    actions = { cancel: true, approve: true, reject: true, stage: 'PITIKA' }
    actionAnswer = () => json({ error: { code: 'FORBIDDEN', message: 'This office has an active Pitika. Ask them to decide.', fields: {} } }, 403)
    await mountAt('/bookings?id=12')

    await click(panelButton('Approve'))
    expect(step()?.textContent).toContain('You act for Pitika')
    await click(step()!.querySelector<HTMLElement>('button.confirm')!)

    expect(step()?.textContent).toContain('This office has an active Pitika. Ask them to decide.')
    expect(calls.filter((c) => c.endsWith('/actions'))).toHaveLength(2)
  })

  it('shows a reason the API refuses under the box', async () => {
    actions = { cancel: false, approve: true, reject: true, stage: 'OWNER' }
    actionAnswer = () => json({ error: { code: 'VALIDATION_ERROR', message: 'Invalid request.', fields: { reason: 'HTML is not allowed.' } } }, 422)
    await mountAt('/bookings?id=12')

    await click(panelButton('Reject'))
    expect(step()?.textContent).toContain('You act for the room owner')
    reason().value = '<b>no</b>'
    reason().dispatchEvent(new Event('input'))
    await click(step()!.querySelector<HTMLElement>('button.confirm')!)

    expect(bodies).toEqual([JSON.stringify({ reason: '<b>no</b>', version: 1 })])
    expect(step()?.querySelector('.field-error')?.textContent).toBe('HTML is not allowed.')
  })

  it('names who acted in the history', async () => {
    current = detail({
      status: 'CANCELLED',
      display_status: 'CANCELLED',
      cancelled_at: '2026-11-04T05:00:00Z',
      cancel_reason: 'Room closed.',
      cancelled_by: { id: 3, name_en: 'Chan Admin' },
      reviews: [
        { stage: 'PITIKA', decision: 'APPROVED', reviewer: { id: 3, name_en: 'Chan Admin' }, notes: null, reviewed_at: '2026-11-04T02:00:00Z', by_admin: true },
      ],
    })
    await mountAt('/bookings?id=12')

    const history = panel()!.querySelector('#tabpanel-history')!.textContent
    expect(history).toContain('Chan Admin (Admin, for Pitika)')
    expect(history).toContain('Cancelled by Chan Admin')
  })
})
