import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import { LIVE_REFRESH_MS, useLiveRefresh } from '../useLiveRefresh'

let hidden = false
beforeEach(() => {
  hidden = false
  vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'Date'] })
  Object.defineProperty(document, 'hidden', { configurable: true, get: () => hidden })
})
afterEach(() => {
  vi.useRealTimers()
})

function host(refresh: () => unknown) {
  return mount(
    defineComponent({
      setup() {
        useLiveRefresh(refresh)
        return () => h('div')
      },
    }),
  )
}
function setHidden(value: boolean) {
  hidden = value
  document.dispatchEvent(new Event('visibilitychange'))
}

describe('useLiveRefresh', () => {
  it('refreshes every 15 seconds while the page is open', async () => {
    const refresh = vi.fn()
    host(refresh)
    expect(LIVE_REFRESH_MS).toBe(15_000)
    expect(refresh).not.toHaveBeenCalled()
    vi.advanceTimersByTime(15_000)
    await flushPromises()
    expect(refresh).toHaveBeenCalledTimes(1)
    vi.advanceTimersByTime(15_000)
    await flushPromises()
    expect(refresh).toHaveBeenCalledTimes(2)
  })

  it('stops while the tab is hidden and refreshes at once when it comes back', async () => {
    const refresh = vi.fn()
    host(refresh)
    setHidden(true)
    vi.advanceTimersByTime(60_000)
    await flushPromises()
    expect(refresh).not.toHaveBeenCalled()
    setHidden(false)
    await flushPromises()
    expect(refresh).toHaveBeenCalledTimes(1)
  })

  it('refreshes when the window gets focus again, but not twice in a row', async () => {
    const refresh = vi.fn()
    host(refresh)
    vi.setSystemTime(Date.now() + 5_000)
    window.dispatchEvent(new Event('focus'))
    await flushPromises()
    window.dispatchEvent(new Event('focus'))
    await flushPromises()
    expect(refresh).toHaveBeenCalledTimes(1)
  })

  it('never runs two refreshes at the same time', async () => {
    let finish!: () => void
    const refresh = vi.fn(() => new Promise<void>((resolve) => (finish = resolve)))
    host(refresh)
    vi.advanceTimersByTime(15_000)
    vi.advanceTimersByTime(15_000)
    await flushPromises()
    expect(refresh).toHaveBeenCalledTimes(1)
    finish()
    await flushPromises()
    vi.advanceTimersByTime(15_000)
    await flushPromises()
    expect(refresh).toHaveBeenCalledTimes(2)
  })

  it('keeps going after a failed refresh, and stops when the page closes', async () => {
    const refresh = vi.fn(async () => {
      throw new Error('offline')
    })
    const w = host(refresh)
    vi.advanceTimersByTime(15_000)
    await flushPromises()
    vi.advanceTimersByTime(15_000)
    await flushPromises()
    expect(refresh).toHaveBeenCalledTimes(2)
    w.unmount()
    vi.advanceTimersByTime(60_000)
    await flushPromises()
    expect(refresh).toHaveBeenCalledTimes(2)
  })
})
