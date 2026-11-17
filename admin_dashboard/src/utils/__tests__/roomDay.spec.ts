import { describe, expect, it } from 'vitest'

import { blockKind, clockLabel, DAY_END, DAY_START, freeAtOptions, freeLabel, freeUntil, isOpenAt, lanePct, toMinutes } from '../roomDay'

const ROOM = { start_time: '07:30:00', end_time: '18:00:00' }
const item = (start: string, end: string) => ({ start_time: `${start}:00`, end_time: `${end}:00` })

describe('roomDay', () => {
  it('reads and writes clock times in minutes', () => {
    expect(toMinutes('10:45:00')).toBe(645)
    expect(toMinutes('10:45')).toBe(645)
    expect(clockLabel(645)).toBe('10:45')
    expect(clockLabel(7 * 60)).toBe('07:00')
  })

  it('places a time on the 07:00–18:00 lane, clamped at its ends', () => {
    expect([DAY_START, DAY_END]).toEqual([420, 1080])
    expect(lanePct(7 * 60)).toBe(0)
    expect(lanePct(18 * 60)).toBe(100)
    expect(lanePct(6 * 60)).toBe(0)
    expect(lanePct(19 * 60)).toBe(100)
    expect(lanePct(12 * 60 + 30)).toBe(50)
  })

  it('tells booked, waiting and masked bookings apart', () => {
    expect(blockKind({ status: 'CONFIRMED', is_masked: false })).toBe('booked')
    expect(blockKind({ status: 'SETUP_IN_PROGRESS', is_masked: false })).toBe('booked')
    expect(blockKind({ status: 'PENDING_PITIKA', is_masked: false })).toBe('waiting')
    expect(blockKind({ status: 'PENDING_OWNER', is_masked: false })).toBe('waiting')
    expect(blockKind({ status: 'CONFIRMED', is_masked: true })).toBe('masked')
  })

  it('a booking covers [start, end): free from its end, until the next one', () => {
    const day = [item('10:00', '10:45'), item('11:00', '12:30')]
    expect(freeUntil(ROOM, day, 600)).toBeNull() // 10:00, in the first booking
    expect(freeUntil(ROOM, day, 630)).toBeNull() // 10:30
    expect(freeUntil(ROOM, day, 645)).toBe(660) // 10:45 → free until 11:00
    expect(freeUntil(ROOM, day, 780)).toBe(1080) // 13:00 → until closing
    expect(freeUntil(ROOM, day, 540)).toBe(600) // 09:00 → until 10:00
  })

  it('closed hours are not free', () => {
    const room = { start_time: '08:00:00', end_time: '17:00:00' }
    expect(freeUntil(room, [], 7 * 60 + 30)).toBeNull()
    expect(freeUntil(room, [], 17 * 60)).toBeNull()
    expect(freeUntil(room, [], 16 * 60)).toBe(1020)
  })

  it('offers Any time, Now, then every half hour from 07:00 to 17:30', () => {
    const options = freeAtOptions()
    expect(options).toHaveLength(2 + 22)
    expect(options.slice(0, 3)).toEqual([
      { value: '', label: 'Any time' },
      { value: 'now', label: 'Now' },
      { value: '420', label: '07:00' },
    ])
    expect(options.at(-1)).toEqual({ value: '1050', label: '17:30' })
  })
})

describe('roomDay: labels true to the clock and the room hours (owner, 17 Nov 2026)', () => {
  const room = { start_time: '08:00:00', end_time: '17:00:00' }

  it('a free room says Free all day on another day, or today before it opens', () => {
    expect(freeLabel(room, [], false, 15 * 60)).toEqual({ text: 'Free all day', from: 480, to: 1020 })
    expect(freeLabel(room, [], true, 7 * 60 + 30)).toEqual({ text: 'Free all day', from: 480, to: 1020 })
  })

  it('today while it is open: Free until its closing time, over the time left', () => {
    expect(freeLabel(room, [], true, 14 * 60 + 24)).toEqual({ text: 'Free until 17:00', from: 864, to: 1020 })
  })

  it('today after it closes: Closed for today', () => {
    expect(freeLabel(room, [], true, 17 * 60)).toEqual({ text: 'Closed for today', from: 480, to: 1020 })
  })

  it('a room with bookings has no such label', () => {
    expect(freeLabel(room, [item('09:00', '10:00')], true, 14 * 60)).toBeNull()
  })

  it('knows when a room is open', () => {
    expect([isOpenAt(room, 7 * 60 + 59), isOpenAt(room, 8 * 60), isOpenAt(room, 16 * 60 + 59), isOpenAt(room, 17 * 60)]).toEqual([false, true, true, false])
  })

  it('today offers only Now and the half hours still to come', () => {
    const labels = freeAtOptions(14 * 60 + 24).map((o) => o.label)
    expect(labels.slice(0, 4)).toEqual(['Any time', 'Now', '14:30', '15:00'])
    expect(labels.at(-1)).toBe('17:30')
    expect(freeAtOptions(14 * 60 + 30).map((o) => o.label)[2]).toBe('14:30')
  })
})
