import { describe, expect, it } from 'vitest'

import { blockKind, clockLabel, DAY_END, DAY_START, dayStatus, freeAtOptions, freeUntil, isOpenAt, lanePct, roomStatus, toMinutes } from '../roomDay'

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

describe('roomDay: one status per room, true to the clock and the room hours (owner, 17 Nov 2026)', () => {
  const room = { start_time: '08:00:00', end_time: '17:00:00' }
  const booked = (start: string, end: string, status = 'CONFIRMED', is_masked = false) => ({ ...item(start, end), status, is_masked })

  it('free: until the next booking or the closing time', () => {
    expect(roomStatus(room, [booked('14:00', '15:00')], 10 * 60 + 20)).toEqual({ kind: 'free', text: 'Free until 14:00' })
    expect(roomStatus(room, [], 15 * 60)).toEqual({ kind: 'free', text: 'Free until 17:00' })
  })

  it('booked: until the last of back-to-back bookings ends', () => {
    const day = [booked('09:00', '10:30'), booked('10:30', '11:30'), booked('13:00', '14:00')]
    expect(roomStatus(room, day, 10 * 60)).toEqual({ kind: 'booked', text: 'Booked until 11:30' })
  })

  it('a private booking the reader may not see is still booked', () => {
    expect(roomStatus(room, [booked('09:00', '10:00', 'CONFIRMED', true)], 9 * 60)).toEqual({ kind: 'booked', text: 'Booked until 10:00' })
  })

  it('waiting: a booking not approved yet', () => {
    expect(roomStatus(room, [booked('14:00', '16:00', 'PENDING_PITIKA')], 15 * 60)).toEqual({ kind: 'waiting', text: 'Waiting approval until 16:00' })
  })

  it('closed: before it opens, and after it closes', () => {
    expect(roomStatus(room, [], 7 * 60 + 30)).toEqual({ kind: 'closed', text: 'Opens at 08:00' })
    expect(roomStatus(room, [], 17 * 60)).toEqual({ kind: 'closed', text: 'Closed after 17:00' })
  })

  it('the whole day (Any time): free all day, or how many bookings', () => {
    expect(dayStatus([])).toEqual({ kind: 'free', text: 'Free all day' })
    expect(dayStatus([booked('09:00', '10:00')])).toEqual({ kind: 'some', text: '1 booking' })
    expect(dayStatus([booked('09:00', '10:00'), booked('11:00', '12:00')])).toEqual({ kind: 'some', text: '2 bookings' })
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
