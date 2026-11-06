import { describe, expect, it } from 'vitest'

import type { ITTicketItem } from '../../api/types'
import { listItem } from '../../test-utils/bookings'
import { groupByDoneDay, groupBySetupDay, itItemIcon, itRing, itSummaryLine, itTabFrom, myTasksLine, setupText } from '../itQueue'

const ticket = (id: number, setup_date: string, changes: Record<string, unknown> = {}) =>
  ({
    id,
    status: 'RECEIVED',
    items: [{ id: 1, name: 'Projector setup' }],
    special_requirements: null,
    technician_notes: null,
    staff: [],
    setup_date,
    setup_time: '07:30',
    forwarded_at: '2026-11-04T02:00:00Z',
    assigned_at: null,
    ready_at: null,
    missed: false,
    review_notes: [],
    booking: listItem(100 + id, { first_session: { id: 1, date: setup_date, start_time: '08:00', end_time: '09:00' } }),
    ...changes,
  }) as unknown as ITTicketItem

describe('itTabFrom', () => {
  it('reads the tab, To assign by default', () => {
    expect(itTabFrom('in_progress')).toBe('in_progress')
    expect(itTabFrom(['ready'])).toBe('ready')
    expect(itTabFrom('x')).toBe('to_assign')
  })
})

describe('groupBySetupDay', () => {
  it('groups by the Phnom Penh setup day, earliest first', () => {
    // Today is Thu 5 Nov 2026; a setup at 07:30 on the 6th is Tomorrow (Review Focus 4).
    const groups = groupBySetupDay([ticket(1, '2026-11-05'), ticket(2, '2026-11-06'), ticket(3, '2026-11-08'), ticket(4, '2026-11-12')], '2026-11-05')
    expect(groups.map((g) => [g.key, g.items.map((t) => t.id)])).toEqual([
      ['today', [1]],
      ['tomorrow', [2]],
      ['week', [3]],
      ['later', [4]],
    ])
  })
})

describe('groupByDoneDay', () => {
  it('groups Ready by the day it was made ready and a missed one by its meeting day, newest first', () => {
    const items = [
      ticket(1, '2026-11-05', { status: 'READY', ready_at: '2026-11-05T03:00:00Z' }),
      ticket(2, '2026-11-04', { missed: true }),
      ticket(3, '2026-11-02', { status: 'READY', ready_at: '2026-11-01T17:30:00Z' }), // 00:30 on 2 Nov in Phnom Penh
    ]
    expect(groupByDoneDay(items, '2026-11-05').map((g) => [g.label, g.items.map((t) => t.id)])).toEqual([
      ['Today · Thu 5 Nov', [1]],
      ['Yesterday · Wed 4 Nov', [2]],
      ['Mon 2 Nov', [3]],
    ])
  })
})

describe('texts', () => {
  it('says when to set up', () => {
    expect(setupText(ticket(1, '2026-11-05'))).toBe('Set up by 07:30')
  })

  it.each([
    [{ to_assign: 2, in_progress: 1, ready_today: 4, due_today: 6, due_today_ready: 4 }, 'Today 4 of 6 setups ready · 2 to assign'],
    [{ to_assign: 2, in_progress: 0, ready_today: 0, due_today: 0, due_today_ready: 0 }, 'No setups today · 2 to assign'],
    [{ to_assign: 0, in_progress: 0, ready_today: 0, due_today: 0, due_today_ready: 0 }, 'No setups today · nothing to assign'],
  ])('%j → %s', (s, line) => {
    expect(itSummaryLine(s)).toBe(line)
  })

  it('draws the ring from today’s setups', () => {
    expect(itRing({ to_assign: 2, in_progress: 1, ready_today: 4, due_today: 6, due_today_ready: 4 })).toEqual({
      parts: [{ value: 4 / 6, tone: 'ok' }],
      label: '4/6',
      spoken: '4 of 6 setups ready today',
    })
    // Review Focus 5: nothing due today.
    expect(itRing({ to_assign: 2, in_progress: 0, ready_today: 0, due_today: 0, due_today_ready: 0 })).toEqual({
      parts: [],
      label: '0/0',
      spoken: 'No setups today',
    })
  })

  it('says what is next for IT Staff', () => {
    const room = { ...listItem(1).room, name_en: 'Mekong Room' }
    const items = [ticket(1, '2026-11-05', { booking: { ...listItem(101), room } }), ticket(2, '2026-11-07')]
    expect(myTasksLine(items, '2026-11-05')).toBe('2 setups to do · next: today 07:30, Mekong Room')
    expect(myTasksLine([ticket(2, '2026-11-07')], '2026-11-05')).toBe('1 setup to do · next: Sat 7 Nov 07:30, Mekong Room')
    expect(myTasksLine([], '2026-11-05')).toBe('Nothing to set up')
  })
})

describe('itItemIcon', () => {
  it('picks an icon from the item name, and a monitor for anything else', () => {
    const name = (text: string) => itItemIcon(text).key
    expect(['Projector setup', 'HDMI projector', 'Microphones', 'Wireless mic', 'Sound system', 'Speakers'].map(name)).toEqual([
      'Projector',
      'Projector',
      'Mic',
      'Mic',
      'Speaker',
      'Speaker',
    ])
    expect(['Video call', 'Zoom link', 'Laptop', 'Wi-Fi access', 'Cables', 'Printer', 'Something else'].map(name)).toEqual([
      'Video',
      'Video',
      'Laptop',
      'Wifi',
      'Cable',
      'Printer',
      'Monitor',
    ])
  })
})
