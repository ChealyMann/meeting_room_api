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

let live!: ReturnType<typeof useLiveRefresh>
function host(refresh: () => unknown) {
  return mount(
    defineComponent({
      setup() {
        live = useLiveRefresh(refresh)
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

  describe('status for the refresh button', () => {
    it('refreshes at once on request, and says when it last worked', async () => {
      vi.setSystemTime(new Date('2026-11-12T03:00:00Z'))
      let finish!: () => void
      const refresh = vi.fn(() => new Promise<void>((resolve) => (finish = resolve)))
      host(refresh)
      expect(live.lastOk.value).toBe(Date.parse('2026-11-12T03:00:00Z')) // the page's first load
      vi.setSystemTime(new Date('2026-11-12T03:01:00Z'))
      const done = live.run()
      expect(refresh).toHaveBeenCalledTimes(1)
      expect(live.refreshing.value).toBe(true)
      finish()
      await done
      expect(live.refreshing.value).toBe(false)
      expect(live.lastOk.value).toBe(Date.parse('2026-11-12T03:01:00Z'))
      expect(live.failing.value).toBe(false)
    })

    it('says it cannot reach the server, keeps the last good time, and clears when it works again', async () => {
      vi.setSystemTime(new Date('2026-11-12T03:00:00Z'))
      let fail = true
      host(async () => {
        if (fail) throw new Error('offline')
      })
      vi.setSystemTime(new Date('2026-11-12T03:02:00Z'))
      await live.run()
      expect(live.failing.value).toBe(true)
      expect(live.lastOk.value).toBe(Date.parse('2026-11-12T03:00:00Z'))
      fail = false
      await live.run()
      expect(live.failing.value).toBe(false)
      expect(live.lastOk.value).toBe(Date.parse('2026-11-12T03:02:00Z'))
    })

    it('refreshes on request even while the tab is hidden', async () => {
      const refresh = vi.fn()
      host(refresh)
      hidden = true
      await live.run()
      expect(refresh).toHaveBeenCalledTimes(1)
    })
  })
})
