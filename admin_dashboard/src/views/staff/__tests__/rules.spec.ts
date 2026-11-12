import { describe, expect, it } from 'vitest'

import {
  busySpans,
  dayLabel,
  fits,
  foodGroupFirst,
  freeStarts,
  fromMeetingType,
  groupServices,
  lenText,
  matchesWords,
  mergeSessions,
  nowLine,
  roomHours,
  toMeetingType,
  toMin,
  toTime,
  workdaysFrom,
} from '../rules'

const D = '2026-11-13' // a Friday
const item = (start: string, end: string, masked = false, date = D) => ({
  date,
  start_time: start,
  end_time: end,
  booking_id: masked ? null : 1,
  reference_code: masked ? null : 'NBC-26-1',
  title: masked ? 'Reserved (Private Session)' : 'Budget',
  requester_name: masked ? null : 'Sok Dara',
  status: 'CONFIRMED',
  is_masked: masked,
})

describe('times', () => {
  it('turns HH:MM into minutes and back', () => {
    expect(toMin('07:30')).toBe(450)
    expect(toTime(450)).toBe('07:30')
  })

  it('names a day shortly', () => {
    expect(dayLabel('2026-11-13')).toBe('Fri 13 Nov')
  })

  it('says a length in words', () => {
    expect(lenText(90)).toBe('1 h 30 min')
    expect(lenText(60)).toBe('1 h')
    expect(lenText(30)).toBe('30 min')
  })
})

describe('workdaysFrom', () => {
  it('skips Saturday and Sunday', () => {
    expect(workdaysFrom(D, 3)).toEqual(['2026-11-13', '2026-11-16', '2026-11-17'])
  })
})

describe('free start times', () => {
  const hours = roomHours({ start_time: '07:30', end_time: '12:00' })

  it('reads the room hours', () => {
    expect(hours).toEqual({ open: 450, close: 720 })
  })

  it('offers nothing today once an hour no longer fits before closing', () => {
    expect(freeStarts([], hours, D, D, toMin('11:10'), 60)).toEqual([])
  })

  it('follows the room hours on another day', () => {
    const starts = freeStarts([], hours, '2026-11-16', D, toMin('11:10'), 60)
    expect(starts[0]).toBe(450)
    expect(starts[starts.length - 1]).toBe(660)
  })

  it('treats a masked private booking as busy and keeps it masked', () => {
    const busy = busySpans([item('09:00', '10:00', true)], D)
    expect(busy).toEqual([{ a: 540, b: 600, masked: true }])
    expect(fits(busy, hours, D, '2026-11-12', 0, 540, 60)).toBe(false)
    expect(fits(busy, hours, D, '2026-11-12', 0, 600, 60)).toBe(true)
  })

  it('ignores items of other days', () => {
    expect(busySpans([item('09:00', '10:00', false, '2026-11-16')], D)).toEqual([])
  })
})

describe('nowLine', () => {
  const hours = { open: 480, close: 1080 }
  const busy = [{ a: 840, b: 900, masked: false }]

  it('says until when a free room is free', () => {
    expect(nowLine(busy, hours, D, D, toMin('10:00'))).toEqual({ tone: 'ok', text: 'Free until 14:00' })
    expect(nowLine([], hours, D, D, toMin('10:00'))).toEqual({ tone: 'ok', text: 'Free all day' })
  })

  it('does not call it free when less than 30 minutes stay free', () => {
    expect(nowLine(busy, hours, D, D, toMin('13:55'))).toEqual({ tone: 'alert', text: 'Busy from 14:00' })
    expect(nowLine(busy, hours, D, D, toMin('13:30'))).toEqual({ tone: 'ok', text: 'Free until 14:00' })
    expect(nowLine([], hours, D, D, toMin('17:40'))).toEqual({ tone: 'off', text: 'Closes at 18:00' })
  })

  it('says until when a room is in use, through meetings that touch', () => {
    expect(nowLine(busy, hours, D, D, toMin('14:30'))).toEqual({ tone: 'alert', text: 'In use until 15:00' })
    const chain = [...busy, { a: 900, b: 960, masked: true }]
    expect(nowLine(chain, hours, D, D, toMin('14:30'))).toEqual({ tone: 'alert', text: 'In use until 16:00' })
  })

  it('says when it opens, or that it is closed', () => {
    expect(nowLine(busy, hours, D, D, toMin('07:00'))).toEqual({ tone: 'off', text: 'Opens at 08:00' })
    expect(nowLine(busy, hours, D, D, toMin('18:30'))).toEqual({ tone: 'off', text: 'Closed now' })
  })
})

describe('mergeSessions', () => {
  it('joins picks that touch on one day, and sorts them', () => {
    expect(
      mergeSessions([
        { date: '2026-11-16', a: 540, b: 600 },
        { date: D, a: 600, b: 660 },
        { date: D, a: 540, b: 600 },
      ]),
    ).toEqual([
      { date: D, a: 540, b: 660 },
      { date: '2026-11-16', a: 540, b: 600 },
    ])
  })
})

describe('meeting type', () => {
  it('maps the two choices to the four API values and back', () => {
    expect(toMeetingType(false, false)).toBe('INTERNAL')
    expect(toMeetingType(true, false)).toBe('EXTERNAL')
    expect(toMeetingType(false, true)).toBe('INTERNAL_WITH_GOVERNOR')
    expect(toMeetingType(true, true)).toBe('EXTERNAL_WITH_GOVERNOR')
    expect(fromMeetingType('INTERNAL')).toEqual({ external: false, governor: false })
    expect(fromMeetingType('EXTERNAL_WITH_GOVERNOR')).toEqual({ external: true, governor: true })
  })
})

describe('food order and search', () => {
  it('puts the food that suits the start time first', () => {
    expect(foodGroupFirst(toMin('08:00'))).toBe('BREAKFAST')
    expect(foodGroupFirst(toMin('11:00'))).toBe('MEALS')
    expect(foodGroupFirst(toMin('14:00'))).toBe('BREAKS')
  })

  it('matches the start of words only', () => {
    expect(matchesWords('Breakfast & Dim Sum Steamed dumplings', 'tea')).toBe(false)
    expect(matchesWords('Tea & Fresh Fruit', 'tea')).toBe(true)
    expect(matchesWords('Afternoon High Tea', 'high te')).toBe(true)
    expect(matchesWords('Anything', '')).toBe(true)
  })

  it('groups services in the given order, with no group last as Other', () => {
    const items = [
      { id: 1, name: 'Lunch Box', description: 'Rice and salad', group: 'MEALS' },
      { id: 2, name: 'Tea & Fruit', description: null, group: null },
      { id: 3, name: 'Coffee', description: 'Hot coffee, tea', group: 'BREAKFAST' },
    ]
    const groups = groupServices(items, ['BREAKFAST', 'MEALS', 'BREAKS'], '')
    expect(groups.map((g) => [g.group, g.items.map((i) => i.id)])).toEqual([
      ['BREAKFAST', [3]],
      ['MEALS', [1]],
      ['OTHER', [2]],
    ])
    expect(groupServices(items, ['BREAKFAST', 'MEALS', 'BREAKS'], 'tea').map((g) => g.group)).toEqual(['BREAKFAST', 'OTHER'])
    expect(groupServices(items, ['BREAKFAST'], 'zzz')).toEqual([])
  })
})
