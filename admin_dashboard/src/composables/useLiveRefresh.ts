// Keeps an open page up to date with no click (owner decision, 12 Nov 2026: "quiet refresh").
// The page's own quiet reload runs every 15 seconds while the tab is visible, at once when the
// tab or the window comes back, never twice at the same time, and never after the page closes.
// A failed refresh keeps what the page shows; the next one tries again.
//
// For the refresh button (owner pick, option 2): `run()` refreshes now (even in a hidden tab),
// `refreshing` while it works, `lastOk` = when the data last loaded, `failing` = the last try
// could not reach the server. The page's reload must throw when it fails, for `failing` to know.
//
// Not too many requests (owner, 12 Nov 2026):
// - quick clicks: one request per 2 seconds; the clicks in between send nothing;
// - "too many requests" (429): nothing at all — timer or button — until the server's Retry-After
//   (60 s when it does not say); `waitUntil` tells the button and the note;
// - the server down: the timer slows down after each failure (30 s, 60 s, then 2 min at most);
//   Try again still works at once; one success brings back every 15 s.
import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

import { ApiError } from '../api/errors'

export const LIVE_REFRESH_MS = 15_000
/** A focus right after a refresh does not ask again (switching windows fires it often). */
const FOCUS_GAP_MS = 2_000
/** Clicks closer than this to the last request send nothing. */
const CLICK_GAP_MS = 2_000
/** "Too many requests" with no Retry-After: wait this long. */
const RATE_LIMIT_WAIT_MS = 60_000
/** The slowest the timer gets while the server is down. */
const MAX_BACKOFF_MS = 120_000

export interface LiveRefresh {
  run: () => Promise<void>
  refreshing: Ref<boolean>
  failing: Ref<boolean>
  lastOk: Ref<number>
  /** After "too many requests": no refresh before this time (ms); 0 = none. */
  waitUntil: Ref<number>
}

export function useLiveRefresh(refresh: () => unknown, every = LIVE_REFRESH_MS): LiveRefresh {
  let timer: ReturnType<typeof setInterval> | undefined
  let inFlight: Promise<void> | null = null
  let lastRun = Date.now()
  let lastStart = 0 // the last request sent
  let failures = 0 // in a row
  let open = false
  const refreshing = ref(false)
  const failing = ref(false)
  const lastOk = ref(Date.now()) // the page loaded as it opened
  const waitUntil = ref(0)

  /** The timer waits longer after each failure in a row: 30 s, 60 s, then 2 min at most. */
  const backoff = () => (failures ? Math.min(every * 2 ** failures, MAX_BACKOFF_MS) : 0)

  function attempt(manual: boolean): Promise<void> {
    if (inFlight) return inFlight
    const now = Date.now()
    if (now < waitUntil.value) return Promise.resolve() // the server asked us to wait
    if (manual && now - lastStart < CLICK_GAP_MS) return Promise.resolve() // quick clicks
    if (!manual && failures && now - lastStart < backoff()) return Promise.resolve() // the server is down
    lastRun = now
    lastStart = now
    refreshing.value = true
    inFlight = (async () => {
      try {
        await refresh()
        failing.value = false
        failures = 0
        waitUntil.value = 0
        lastOk.value = Date.now()
      } catch (err) {
        failing.value = true // what the page shows stays
        if (err instanceof ApiError && err.status === 429) {
          const wait = err.retryAfterSeconds ? err.retryAfterSeconds * 1000 : RATE_LIMIT_WAIT_MS
          waitUntil.value = Date.now() + wait
        } else {
          failures += 1
        }
      } finally {
        refreshing.value = false
        inFlight = null
      }
    })()
    return inFlight
  }
  /** The timer, the tab and the window: only while the page is open and in view. */
  const tick = () => (open && !document.hidden ? attempt(false) : undefined)
  /** The button and Try again: at once, but not more than once per 2 s. */
  const run = () => attempt(true)

  const start = () => {
    stop()
    timer = setInterval(tick, every)
  }
  function stop() {
    if (timer !== undefined) clearInterval(timer)
    timer = undefined
  }
  function onVisibility() {
    if (document.hidden) return stop()
    void tick()
    start()
  }
  function onFocus() {
    if (Date.now() - lastRun >= FOCUS_GAP_MS) void tick()
  }

  onMounted(() => {
    open = true
    lastRun = Date.now()
    lastOk.value = Date.now()
    start()
    document.addEventListener('visibilitychange', onVisibility)
    window.addEventListener('focus', onFocus)
  })
  onBeforeUnmount(() => {
    open = false
    stop()
    document.removeEventListener('visibilitychange', onVisibility)
    window.removeEventListener('focus', onFocus)
  })

  return { run, refreshing, failing, lastOk, waitUntil }
}
