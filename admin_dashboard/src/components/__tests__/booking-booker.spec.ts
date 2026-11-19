import { enableAutoUnmount, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { bookingDetail, bookingItem } from '../../test-utils/staff'
import { holidayMap } from '../../utils/holidays'
import BookingDetails from '../BookingDetails.vue'

enableAutoUnmount(afterEach)

beforeEach(() => setActivePinia(createPinia()))

function details(requester: Record<string, unknown>, sessions: string[] = ['2026-11-23'], holidays?: ReturnType<typeof holidayMap>) {
  const item = bookingItem(31, 'Demo2', 'PENDING_PITIKA', sessions[0]!)
  const booking = {
    ...bookingDetail(item),
    requester: { ...(item as { requester: object }).requester, ...requester },
    sessions: sessions.map((date, k) => ({ id: k + 1, date, start_time: '08:00:00', end_time: '12:00:00' })),
  }
  return mount(BookingDetails, { props: { booking: booking as never, holidays } })
}
const section = (w: ReturnType<typeof details>, title: string) => w.findAll('.panel-section').find((s) => s.find('h3').text().startsWith(title))!
const rows = (w: ReturnType<typeof details>, title: string) =>
  section(w, title).findAll('.details > div').map((d) => [d.find('dt').text(), d.find('dd').text().replace(/\s+/g, ' ').trim()])

// The Booker card gets the booker's current phone and email, each copied with a click
// (owner, 19 Nov 2026), so the Pitika can reach them.
describe('Booker section', () => {
  it('ends with the phone and the email, each one a click to copy', () => {
    const w = details({ phone: '012 345 678', email: 'heng.rathana@nbc.gov.kh' })
    expect(rows(w, 'Booker').slice(-2)).toEqual([
      ['Phone', '012 345 678'],
      ['Email', 'heng.rathana@nbc.gov.kh'],
    ])
    expect(section(w, 'Booker').findAll('.copy-value').map((b) => b.text())).toEqual(['012 345 678', 'heng.rathana@nbc.gov.kh'])
  })

  it('says "No phone" when the booker has none', () => {
    const w = details({ phone: null, email: 'a@nbc.gov.kh' })
    expect(rows(w, 'Booker').at(-2)).toEqual(['Phone', 'No phone'])
    expect(section(w, 'Booker').findAll('.copy-value')).toHaveLength(1)
  })
})

describe('When section, with holidays', () => {
  const HOLIDAYS = holidayMap([{ holiday_date: '2026-11-24', name_km: 'បុណ្យអុំទូក', name_en: 'Water Festival' }])

  it('marks the session on a holiday with its name, and says how many in the title', () => {
    const w = details({}, ['2026-11-24', '2026-11-26', '2026-11-27'], HOLIDAYS)
    const when = section(w, 'When')
    expect(when.get('h3 > span').text()).toBe('When · 3 sessions')
    expect(when.get('.holiday-flag').text()).toBe('1 on a holiday')
    const marked = when.findAll('.sessions li.holiday')
    expect(marked).toHaveLength(1)
    expect(marked[0]!.get('.holiday-name').text().replace(/\s+/g, ' ')).toBe('Public holiday · បុណ្យអុំទូក · Water Festival')
  })

  it('says "Holiday" for a one-session booking on a holiday', () => {
    const w = details({}, ['2026-11-24'], HOLIDAYS)
    expect(section(w, 'When').get('.holiday-flag').text()).toBe('Holiday')
  })

  it('marks nothing without holidays', () => {
    const w = details({}, ['2026-11-24'])
    expect(section(w, 'When').find('.holiday-flag').exists()).toBe(false)
    expect(w.find('.sessions li.holiday').exists()).toBe(false)
  })
})
