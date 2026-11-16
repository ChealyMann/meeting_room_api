import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useSessionStore } from '../../stores/session'
import BookingFiles from '../BookingFiles.vue'

const URL_A = '/api/v1/bookings/7/attachments/1'
const A = { id: 1, file_name: 'agenda.pdf', content_type: 'application/pdf', size_bytes: 839680, created_at: '2026-11-12T03:00:00Z', url: URL_A }
const B = { id: 2, file_name: 'notes.pdf', content_type: 'application/pdf', size_bytes: 2048, created_at: '2026-11-12T03:05:00Z', url: '/api/v1/bookings/7/attachments/2' }

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
let calls: string[]
let answer: (key: string) => Response

beforeEach(() => {
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  calls = []
  answer = (key) => {
    if (key === `GET ${URL_A}`) return new Response('%PDF-1', { headers: { 'Content-Type': 'application/pdf' } })
    if (key === 'POST /api/v1/bookings/7/attachments') return json(B, 201)
    if (key === `DELETE ${URL_A}`) return new Response(null, { status: 204 })
    return json({}, 404)
  }
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const key = `${init?.method ?? 'GET'} ${new URL(String(input)).pathname}`
      calls.push(key)
      return answer(key)
    }),
  )
  URL.createObjectURL = vi.fn<typeof URL.createObjectURL>(() => 'blob:1')
  URL.revokeObjectURL = vi.fn<typeof URL.revokeObjectURL>()
})
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

async function pick(w: ReturnType<typeof mount>, file: File) {
  const input = w.get('input[type="file"]')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  await input.trigger('change')
  await flushPromises()
}

describe('BookingFiles', () => {
  it('downloads a file under its own name', async () => {
    const clicked: string[] = []
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
      clicked.push(this.download)
    })
    const w = mount(BookingFiles, { props: { bookingId: 7, files: [A] } })
    await w.get('.att-name').trigger('click')
    await flushPromises()
    expect(calls).toEqual([`GET ${URL_A}`])
    expect(clicked).toEqual(['agenda.pdf'])
  })

  it('is read only unless editable', () => {
    const w = mount(BookingFiles, { props: { bookingId: 7, files: [A] } })
    expect(w.text()).not.toContain('Add file')
  })

  it('uploads a new file and gives back the new list', async () => {
    const w = mount(BookingFiles, { props: { bookingId: 7, files: [A], editable: true } })
    await pick(w, new File(['%PDF-1'], 'notes.pdf'))
    expect(calls).toEqual(['POST /api/v1/bookings/7/attachments'])
    expect(w.emitted('update')).toEqual([[[A, B]]])
  })

  it('removes a file and gives back the new list', async () => {
    const w = mount(BookingFiles, { props: { bookingId: 7, files: [A, B], editable: true } })
    await w.get('[aria-label="Remove agenda.pdf"]').trigger('click')
    await flushPromises()
    expect(calls).toEqual([`DELETE ${URL_A}`])
    expect(w.emitted('update')).toEqual([[[B]]])
  })

  it("shows the server's reason when an upload is refused", async () => {
    answer = () => json({ error: { code: 'UNSUPPORTED_FILE_TYPE', message: 'Only PDF, Word or Excel files.', fields: {} } }, 415)
    const w = mount(BookingFiles, { props: { bookingId: 7, files: [], editable: true } })
    await pick(w, new File(['x'], 'fake.pdf'))
    expect(w.get('[role="alert"]').text()).toBe('Only PDF, Word or Excel files.')
    expect(w.emitted('update')).toBeUndefined()
  })

  it('asks for a reload when the booking was confirmed meanwhile', async () => {
    answer = () => json({ error: { code: 'INVALID_TRANSITION', message: 'Files are locked once the booking is confirmed.', fields: {} } }, 409)
    const w = mount(BookingFiles, { props: { bookingId: 7, files: [], editable: true } })
    await pick(w, new File(['%PDF-1'], 'a.pdf'))
    expect(w.get('[role="alert"]').text()).toBe('Files are locked once the booking is confirmed.')
    expect(w.emitted('locked')).toHaveLength(1)
  })
})
