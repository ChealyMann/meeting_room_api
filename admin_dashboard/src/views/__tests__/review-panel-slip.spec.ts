import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useSessionStore } from '../../stores/session'
import { bookingDetail, bookingItem } from '../../test-utils/staff'
import ReviewPanel from '../bookings/ReviewPanel.vue'

enableAutoUnmount(afterEach)

// The Pitika's panel on a decided booking (read only): the request slip of a confirmed one.
const SLIP = 'ប័ណ្ណស្នើ (Word)'
const calls: string[] = []
let saved: string[]

beforeEach(() => {
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  calls.length = 0
  saved = []
  URL.createObjectURL = vi.fn<typeof URL.createObjectURL>(() => 'blob:1')
  URL.revokeObjectURL = vi.fn<typeof URL.revokeObjectURL>()
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
    saved.push(this.download)
  })
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input) => {
      calls.push(new URL(String(input)).pathname)
      return new Response('docx', { headers: { 'Content-Type': 'application/octet-stream' } })
    }),
  )
})
afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  document.body.innerHTML = ''
})

function open(status: string, readOnly = true) {
  const booking = bookingDetail(bookingItem(31, 'Budget review', status, '2026-11-13'))
  mount(ReviewPanel, { props: { booking: booking as never, photoPath: null, startsIn: null, readOnly }, attachTo: document.body })
  return document.body.querySelector('[role="dialog"]')!
}
const button = (root: Element) => [...root.querySelectorAll('button')].find((b) => b.textContent?.trim() === SLIP) as HTMLButtonElement | undefined

describe('ReviewPanel request slip', () => {
  it('downloads the Word slip of a confirmed booking', async () => {
    const panel = open('CONFIRMED')
    button(panel)!.click()
    await flushPromises()
    expect(calls).toEqual(['/api/v1/bookings/31/request-slip'])
    expect(saved).toEqual(['request-slip-NBC-26-31.docx'])
  })

  it('offers it for a completed meeting too', () => {
    expect(button(open('COMPLETED'))).toBeTruthy()
  })

  it.each(['REJECTED', 'CANCELLED'])('has no slip for a %s booking', (status) => {
    expect(button(open(status))).toBeUndefined()
  })

  it('has no slip while the booking still waits for the decision', () => {
    expect(button(open('PENDING_PITIKA', false))).toBeUndefined()
  })
})
