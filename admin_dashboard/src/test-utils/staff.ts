// Shapes the Staff page tests share.
export const building = (id: number, name: string) => ({ id, name_en: name, name_kh: 'អគារ', short_name: null })
export const roomItem = (id: number, name: string, extra: Record<string, unknown> = {}) => ({
  id,
  name_en: name,
  name_kh: 'បន្ទប់',
  short_desc: '4K screen / VC',
  capacity: 14,
  size_sqm: 50,
  start_time: '08:00',
  end_time: '17:00',
  category: { id: 1, name_en: 'Meeting room', name_kh: 'x' },
  floor: { id: 2, floor_label: 'Floor 2' },
  building: building(1, 'Head office'),
  location: { id: 1, name_en: 'NBC', name_kh: 'x' },
  province: { code: 'PHNOM_PENH', name_en: 'Phnom Penh', name_kh: 'x' },
  owner: null,
  cover_photo: null,
  photo_count: 0,
  is_active: true,
  is_bookable: true,
  is_private: false,
  ...extra,
})


export const roomDetail = (id: number, name: string, extra: Record<string, unknown> = {}) => ({
  ...roomItem(id, name),
  description: null,
  photos: [],
  equipment: [],
  created_at: '2026-11-01T00:00:00Z',
  updated_at: '2026-11-01T00:00:00Z',
  ...extra,
})

export const scheduleItem = (date: string, start: string, end: string, masked = false) => ({
  date,
  start_time: start,
  end_time: end,
  booking_id: masked ? null : 9,
  reference_code: masked ? null : 'NBC-26-9',
  title: masked ? 'Reserved (Private Session)' : 'Budget',
  requester_name: masked ? null : 'Sok Dara',
  status: 'CONFIRMED',
  is_masked: masked,
})

export const service = (id: number, name: string, group: string | null, description: string | null = null) => ({
  id,
  name,
  description,
  group,
  icon: null,
  sort_order: id,
  is_active: true,
  version: 1,
  created_at: '2026-11-01T00:00:00Z',
  updated_at: '2026-11-01T00:00:00Z',
})

export interface StubAnswers {
  schedule?: unknown[]
  holidays?: unknown[]
  foods?: unknown[]
  its?: unknown[]
  check?: () => [unknown, number?]
  send?: () => [unknown, number?]
  /** The answer to the n-th file upload (0 first); a 201 with the file by default. */
  upload?: (n: number) => [unknown, number?]
}

/** A fetch for the booking pages: the room, its week, holidays, food and IT, check and send.
 *  Every call is kept in `calls` as "METHOD /path?query" with its JSON body in `bodies`. */
export function bookingStubs(room: { id: number }, answers: StubAnswers = {}) {
  const calls: string[] = []
  const bodies: Record<string, unknown> = {}
  let uploads = 0
  const json = (body: unknown, status = 200) =>
    new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
  const page = (items: unknown[]) => json({ items, page: 1, size: 100, total: items.length })
  const fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input))
    const method = init?.method ?? 'GET'
    const key = `${method} ${url.pathname}`
    calls.push(`${key}${url.search}`)
    if (typeof init?.body === 'string') bodies[key] = JSON.parse(init.body)
    if (method === 'POST' && /^\/api\/v1\/bookings\/\d+\/attachments$/.test(url.pathname)) {
      const file = (init?.body as FormData).get('file') as File
      const n = uploads++
      const made = { id: n + 1, file_name: file.name, content_type: 'application/pdf', size_bytes: file.size, created_at: '2026-11-12T03:00:00Z', url: `${url.pathname}/${n + 1}` }
      const [body, status] = answers.upload?.(n) ?? [made, 201]
      return json(body, status)
    }
    if (key === `GET /api/v1/rooms/${room.id}`) return json(room)
    if (key === `GET /api/v1/rooms/${room.id}/schedule`) {
      const items = answers.schedule ?? [scheduleItem('2026-11-13', '10:00', '11:00', true)]
      return json({ items, total: items.length })
    }
    if (key === 'GET /api/v1/public-holidays')
      return page(answers.holidays ?? [{ id: 1, holiday_date: '2026-11-17', name_km: 'x', name_en: 'Test holiday' }])
    if (key === 'GET /api/v1/catering-packages') return page(answers.foods ?? [])
    if (key === 'GET /api/v1/it-services') return page(answers.its ?? [])
    if (key === 'POST /api/v1/bookings/check') {
      const [body, status] = answers.check?.() ?? [{ route: 'R1', first_status: 'PENDING_PITIKA', steps: ['PITIKA', 'CONFIRMED'], problem: null, warnings: [] }]
      return json(body, status)
    }
    if (key === 'POST /api/v1/bookings') {
      const [body, status] = answers.send?.() ?? [{ id: 77, reference_code: 'NBC-26-77', status: 'PENDING_PITIKA', version: 1 }]
      return json(body, status)
    }
    return json({}, 404)
  }
  return { fetch, calls, bodies }
}

/** A booking in "My bookings" (the list shape). */
export const bookingItem = (id: number, title: string, status: string, date: string, extra: Record<string, unknown> = {}) => ({
  id,
  reference_code: `NBC-26-${id}`,
  room: {
    id: 12,
    name_en: 'Mekong Room',
    name_kh: 'x',
    is_private: false,
    location: { id: 1, name_en: 'NBC', name_kh: 'x' },
    province: { code: 'PHNOM_PENH', name_en: 'Phnom Penh', name_kh: 'x' },
    building: { id: 2, name_en: 'Building A', name_kh: 'x', short_name: 'A' },
    floor: { id: 4, floor_label: '2nd floor' },
    capacity: 20,
    category: { id: 1, name_en: 'Meeting Room', name_kh: 'x' },
    owner: null,
    map_query: null,
  },
  meeting_title: title,
  meeting_type: 'INTERNAL',
  route: 'R1',
  status: status === 'COMPLETED' ? 'CONFIRMED' : status,
  display_status: status,
  requester: { id: 5, name_en: 'Sok Dara', name_kh: 'x', phone: '012 345 678', email: 'sok.dara@nbc.gov.kh' },
  first_session: { id: id * 10, date, start_time: '09:00', end_time: '10:00' },
  // The first session not ended yet; none once the booking is over or stopped.
  next_session: ['COMPLETED', 'CANCELLED', 'REJECTED'].includes(status) ? null : { id: id * 10, date, start_time: '09:00', end_time: '10:00' },
  session_count: 1,
  attendees: 8,
  has_catering: false,
  has_it: false,
  created_at: '2026-11-10T02:00:00Z',
  version: 3,
  ...extra,
})

/** The same booking with its details (GET /bookings/{id}). */
export const bookingDetail = (item: ReturnType<typeof bookingItem>, extra: Record<string, unknown> = {}) => ({
  ...item,
  requester_info: { name_en: 'Sok Dara' },
  meeting_purpose: null,
  private_justification: null,
  participant_emails: [],
  sessions: [item.first_session],
  last_end: { date: item.first_session.date, time: '10:00' },
  catering: null,
  it: null,
  reviews: [],
  rejection: null,
  cancelled_at: null,
  cancel_reason: null,
  cancelled_by: null,
  updated_at: '2026-11-10T02:00:00Z',
  attachments: [],
  attachments_open: ['PENDING_PITIKA', 'PENDING_OWNER', 'SETUP_IN_PROGRESS'].includes(item.status),
  ...extra,
})
