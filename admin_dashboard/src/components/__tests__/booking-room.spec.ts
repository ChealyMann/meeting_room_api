import { enableAutoUnmount, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { useSessionStore } from '../../stores/session'
import { bookingDetail, bookingItem } from '../../test-utils/staff'
import BookingDetails from '../BookingDetails.vue'
import BookingServices from '../BookingServices.vue'

enableAutoUnmount(afterEach)

// The Room section of the booking pop-ups (owner pick, 17 Nov 2026, look A "Rows"), and the
// "Set up at" line on IT's card.
const ROOM = {
  id: 16,
  name_en: 'Chinit River',
  name_kh: 'ស្ទឹងជីនិត',
  is_private: false,
  location: { id: 3, name_en: 'Head Office', name_kh: 'x' },
  province: { code: 'PHNOM_PENH', name_en: 'Phnom Penh', name_kh: 'x' },
  building: { id: 3, name_en: 'Headquarters Building', name_kh: 'x', short_name: 'HQ' },
  floor: { id: 7, floor_label: 'Floor 18 - Executive Suite' },
  capacity: 60,
  category: { id: 4, name_en: 'Grand Hall', name_kh: 'x' },
  owner: null as null | { id: number; name_en: string; name_kh: string },
  map_query: 'NBC Headquarters, Phnom Penh' as string | null,
}
const OWNER = { id: 17, name_en: 'Jonathan Vance', name_kh: 'ចូណាថាន វ៉ាន់' }

beforeEach(() => setActivePinia(createPinia()))

function details(room: Partial<typeof ROOM>) {
  const booking = bookingDetail(bookingItem(31, 'The Black Swan V2', 'CONFIRMED', '2026-11-17', { room: { ...ROOM, ...room } }))
  return mount(BookingDetails, { props: { booking: booking as never } })
}
const roomRows = (w: ReturnType<typeof details>) =>
  w.findAll('.panel-section').find((s) => s.find('h3').text() === 'Room')!.findAll('.details > div').map((d) => [d.find('dt').text(), d.find('dd').text().replace(/\s+/g, ' ').trim()])

describe('Room section', () => {
  it('comes right after When, with the room, where, office, seats and type', () => {
    const w = details({})
    expect(w.findAll('.panel-section > h3').map((h) => h.text().replace(/\s+/g, ' '))).toEqual(['When · 1 session', 'Room', 'Meeting', 'Booker'])
    expect(roomRows(w)).toEqual([
      ['Room', 'Chinit Riverស្ទឹងជីនិត'],
      ['Where', 'Floor 18 - Executive Suite Headquarters Building'],
      ['Office', 'Head Office, Phnom Penh Open in Maps'],
      ['Seats', '60 · Grand Hall'],
    ])
  })

  it('opens the office on Google Maps in a new tab', () => {
    const link = details({}).get('a.map')
    expect(link.attributes('href')).toBe('https://www.google.com/maps/search/?api=1&query=NBC%20Headquarters%2C%20Phnom%20Penh')
    expect(link.attributes('target')).toBe('_blank')
    expect(link.attributes('rel')).toBe('noopener')
  })

  it('has no map link when the office has no map text', () => {
    expect(details({ map_query: null }).find('a.map').exists()).toBe(false)
  })

  it('marks a private room and names its owner', () => {
    const rows = roomRows(details({ is_private: true, owner: OWNER }))
    expect(rows[0]).toEqual(['Room', 'Chinit RiverPrivateស្ទឹងជីនិត'])
    expect(rows.at(-1)).toEqual(['Owner', 'Jonathan Vance ចូណាថាន វ៉ាន់'])
  })

  it('says "You" when the reader owns the room', () => {
    useSessionStore().user = { id: OWNER.id } as never
    expect(roomRows(details({ is_private: true, owner: OWNER })).at(-1)).toEqual(['Owner', 'You'])
  })
})

describe('Set up at, on the IT card', () => {
  const booking = { display_status: 'CONFIRMED', sessions: [], catering: null, it: { items: [{ id: 1, name: 'Projector' }], special_requirements: null, staff: [], technician_notes: null, ready_at: null, status: 'RECEIVED' } }

  it('shows where IT sets up when the IT panel gives the place', () => {
    const w = mount(BookingServices, {
      props: { booking: booking as never, viewer: 'staff', setupAt: { place: 'Chinit River · Floor 18', area: 'Headquarters Building, Head Office' } },
    })
    expect(w.get('.setup-at').text().replace(/\s+/g, ' ')).toBe('Set up at Chinit River · Floor 18Headquarters Building, Head Office')
  })

  it('is not shown anywhere else', () => {
    expect(mount(BookingServices, { props: { booking: booking as never, viewer: 'staff' } }).find('.setup-at').exists()).toBe(false)
  })
})
