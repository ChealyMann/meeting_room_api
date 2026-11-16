import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import { ApiError } from '../../api/errors'
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
    vi.advanceTimersByTime(30_000) // after a failure it waits 30 s, not 15
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
      vi.setSystemTime(new Date('2026-11-12T03:02:03Z')) // a click 2 s later or more
      await live.run()
      expect(live.failing.value).toBe(false)
      expect(live.lastOk.value).toBe(Date.parse('2026-11-12T03:02:03Z'))
    })

    it('refreshes on request even while the tab is hidden', async () => {
      const refresh = vi.fn()
      host(refresh)
      hidden = true
      await live.run()
      expect(refresh).toHaveBeenCalledTimes(1)
    })
  })

  describe('not too many requests', () => {
    it('sends one request for quick clicks, and another once 2 s have passed', async () => {
      const refresh = vi.fn()
      host(refresh)
      await live.run()
      vi.setSystemTime(Date.now() + 500)
      await live.run()
      vi.setSystemTime(Date.now() + 500)
      await live.run()
      expect(refresh).toHaveBeenCalledTimes(1)
      vi.setSystemTime(Date.now() + 1_500)
      await live.run()
      expect(refresh).toHaveBeenCalledTimes(2)
    })

    it('waits as long as the server asks after "too many requests", button included', async () => {
      const refresh = vi.fn(async () => {
        throw new ApiError(429, 'RATE_LIMITED', 'Too many requests.', {}, 30)
      })
      host(refresh)
      await live.run()
      expect(live.failing.value).toBe(true)
      expect(live.waitUntil.value).toBe(Date.now() + 30_000)
      vi.setSystemTime(Date.now() + 5_000)
      await live.run() // the button waits too
      vi.advanceTimersByTime(15_000) // and the timer
      await flushPromises()
      expect(refresh).toHaveBeenCalledTimes(1)
      vi.advanceTimersByTime(15_000) // 35 s after: allowed again
      await flushPromises()
      expect(refresh).toHaveBeenCalledTimes(2)
    })

    it('waits 60 s after "too many requests" when the server does not say how long', async () => {
      const refresh = vi.fn(async () => {
        throw new ApiError(429, 'RATE_LIMITED', 'Too many requests.')
      })
      host(refresh)
      const start = Date.now()
      await live.run()
      expect(live.waitUntil.value).toBe(start + 60_000)
    })

    it('slows down while the server is down (30 s, 60 s, 2 min at most), and is back to 15 s after it works', async () => {
      let down = true
      const refresh = vi.fn(async () => {
        if (down) throw new Error('offline')
      })
      host(refresh)
      const ticks = async (seconds: number) => {
        for (let t = 0; t < seconds; t += 15) {
          vi.advanceTimersByTime(15_000)
          await flushPromises()
        }
      }
      await ticks(15) // fails (1)
      expect(refresh).toHaveBeenCalledTimes(1)
      await ticks(30) // 30 s later: fails (2)
      expect(refresh).toHaveBeenCalledTimes(2)
      await ticks(45)
      expect(refresh).toHaveBeenCalledTimes(2) // waits 60 s now
      await ticks(15) // fails (3)
      expect(refresh).toHaveBeenCalledTimes(3)
      await ticks(105)
      expect(refresh).toHaveBeenCalledTimes(3) // waits 2 min now
      down = false
      await ticks(15) // works
      await ticks(15)
      expect(refresh).toHaveBeenCalledTimes(5) // every 15 s again
    })

    it('Try again works at once while the server is down', async () => {
      const refresh = vi.fn(async () => {
        throw new Error('offline')
      })
      host(refresh)
      vi.advanceTimersByTime(15_000)
      await flushPromises()
      vi.setSystemTime(Date.now() + 3_000)
      await live.run()
      expect(refresh).toHaveBeenCalledTimes(2)
    })
  })
})
