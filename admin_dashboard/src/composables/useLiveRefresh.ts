// Keeps an open page up to date with no click (owner decision, 12 Nov 2026: "quiet refresh").
// The page's own quiet reload runs every 15 seconds while the tab is visible, at once when the
// tab or the window comes back, never twice at the same time, and never after the page closes.
// A failed refresh keeps what the page shows; the next one tries again.
//
// For the refresh button (owner pick, option 2): `run()` refreshes now (even in a hidden tab),
// `refreshing` while it works, `lastOk` = when the data last loaded, `failing` = the last try
// could not reach the server. The page's reload must throw when it fails, for `failing` to know.
import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

export const LIVE_REFRESH_MS = 15_000
/** A focus right after a refresh does not ask again (switching windows fires it often). */
const FOCUS_GAP_MS = 2_000

export interface LiveRefresh {
  run: () => Promise<void>
  refreshing: Ref<boolean>
  failing: Ref<boolean>
  lastOk: Ref<number>
}

export function useLiveRefresh(refresh: () => unknown, every = LIVE_REFRESH_MS): LiveRefresh {
  let timer: ReturnType<typeof setInterval> | undefined
  let inFlight: Promise<void> | null = null
  let lastRun = Date.now()
  let open = false
  const refreshing = ref(false)
  const failing = ref(false)
  const lastOk = ref(Date.now()) // the page loaded as it opened

  function attempt(): Promise<void> {
    if (inFlight) return inFlight
    lastRun = Date.now()
    refreshing.value = true
    inFlight = (async () => {
      try {
        await refresh()
        failing.value = false
        lastOk.value = Date.now()
      } catch {
        failing.value = true // what the page shows stays; the next tick tries again
      } finally {
        refreshing.value = false
        inFlight = null
      }
    })()
    return inFlight
  }
  /** The timer, the tab and the window: only while the page is open and in view. */
  const tick = () => (open && !document.hidden ? attempt() : undefined)
  /** The button: always, at once. */
  const run = () => attempt()

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

  return { run, refreshing, failing, lastOk }
}
