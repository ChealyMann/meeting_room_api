import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useSessionStore } from '../../stores/session'
import { mountConfirmHost } from '../../test-utils/confirm'
import RoomDetailPanel from '../rooms/RoomDetailPanel.vue'

enableAutoUnmount(afterEach)

const ROOM = {
  id: 12,
  name_en: 'Mekong Room',
  name_kh: 'បន្ទប់មេគង្គ',
  capacity: 12,
  size_sqm: null,
  start_time: '08:00:00',
  end_time: '17:00:00',
  short_desc: null,
  description: null,
  category: { id: 1, name_en: 'Meeting room', name_kh: 'បន្ទប់ប្រជុំ' },
  floor: { id: 7, floor_label: '3rd floor' },
  building: { id: 5, name_en: 'Building A', name_kh: 'អគារ A', short_name: null },
  location: { id: 3, name_en: 'Head Office', name_kh: 'ការិយាល័យកណ្តាល' },
  province: { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' },
  owner: null,
  cover_photo: null,
  is_active: true,
  is_bookable: true,
  is_private: true,
  photos: [],
  equipment: [],
  created_at: '2026-10-01T02:00:00Z',
  updated_at: '2026-10-23T06:51:03Z',
}

const item = (changes: Record<string, unknown> = {}) => ({
  date: '2026-11-05',
  start_time: '09:00',
  end_time: '10:30',
  booking_id: 7,
  reference_code: 'NBC-26-48213',
  title: 'Budget review',
  requester_name: 'Sok Dara',
  status: 'CONFIRMED',
  is_masked: false,
  ...changes,
})

const scheduleCalls: string[] = []
let schedule: unknown[]

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-04T01:00:00Z'))
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  scheduleCalls.length = 0
  schedule = [
    item(),
    item({ start_time: '13:00', end_time: '14:00', booking_id: 8, reference_code: 'NBC-26-10001', title: 'Team sync' }),
    item({
      date: '2026-11-06',
      booking_id: null,
      reference_code: null,
      requester_name: null,
      title: 'Reserved (Private Session)',
      is_masked: true,
      status: 'PENDING_OWNER',
    }),
  ]
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input) => {
      const url = new URL(String(input))
      if (url.pathname === '/api/v1/rooms/12/schedule') {
        scheduleCalls.push(url.search)
        return json({ items: schedule, total: schedule.length })
      }
      if (url.pathname === '/api/v1/rooms/12') return json(ROOM)
      return json({ items: [], page: 1, size: 100, total: 0 })
    }),
  )
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

async function mountPanel(step?: 'schedule') {
  mountConfirmHost()
  const wrapper = mount(RoomDetailPanel, {
    props: { roomId: 12, step },
    global: { stubs: { teleport: true } },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

type Wrapper = Awaited<ReturnType<typeof mountPanel>>
async function click(wrapper: Wrapper, text: string) {
  await wrapper.findAll('button').find((b) => b.text() === text)!.trigger('click')
  await flushPromises()
}

describe('RoomSchedule', () => {
  it('loads this week only when its tab opens', async () => {
    const wrapper = await mountPanel()
    expect(scheduleCalls).toEqual([])

    await click(wrapper, 'Schedule')

    expect(scheduleCalls).toEqual(['?from=2026-11-04&to=2026-11-10'])
  })

  it('moves a week at a time', async () => {
    const wrapper = await mountPanel('schedule')

    await click(wrapper, 'Next week')
    expect(scheduleCalls[scheduleCalls.length - 1]).toBe('?from=2026-11-11&to=2026-11-17')

    await click(wrapper, 'This week')
    expect(scheduleCalls[scheduleCalls.length - 1]).toBe('?from=2026-11-04&to=2026-11-10')
  })

  it('groups the sessions by day', async () => {
    const wrapper = await mountPanel('schedule')

    const days = wrapper.findAll('#tabpanel-schedule .day')
    expect(days.map((d) => d.find('h4').text())).toEqual(['Thu 5 Nov 2026', 'Fri 6 Nov 2026'])
    const first = days[0]!.findAll('li')
    expect(first).toHaveLength(2)
    expect(first[0]!.text()).toContain('09:00–10:30')
    expect(first[0]!.text()).toContain('Budget review')
    expect(first[0]!.text()).toContain('NBC-26-48213')
    expect(first[0]!.text()).toContain('Sok Dara')
    expect(first[0]!.text()).toContain('Confirmed')
  })

  it('shows a masked session with a lock and no booking details', async () => {
    const wrapper = await mountPanel('schedule')

    const masked = wrapper.findAll('#tabpanel-schedule .day')[1]!.find('li')
    expect(masked.classes()).toContain('masked')
    expect(masked.find('svg.lock').exists()).toBe(true)
    expect(masked.text()).toContain('Reserved (Private Session)')
    expect(masked.text()).not.toContain('NBC-')
  })

  it('says when the week is free', async () => {
    schedule = []
    const wrapper = await mountPanel('schedule')

    expect(wrapper.get('#tabpanel-schedule').text()).toContain('No bookings this week.')
  })
})
