// Keeps an open page up to date with no click (owner decision, 12 Nov 2026: "quiet refresh").
// The page's own quiet reload runs every 15 seconds while the tab is visible, at once when the
// tab or the window comes back, never twice at the same time, and never after the page closes.
// A failed refresh is ignored: the next one tries again, and the page keeps what it shows.
import { onBeforeUnmount, onMounted } from 'vue'

export const LIVE_REFRESH_MS = 15_000
/** A focus right after a refresh does not ask again (switching windows fires it often). */
const FOCUS_GAP_MS = 2_000

export function useLiveRefresh(refresh: () => unknown, every = LIVE_REFRESH_MS) {
  let timer: ReturnType<typeof setInterval> | undefined
  let running = false
  let lastRun = Date.now()
  let open = false

  async function run() {
    if (!open || running || document.hidden) return
    running = true
    lastRun = Date.now()
    try {
      await refresh()
    } catch {
      // The next tick tries again; what the page shows stays.
    } finally {
      running = false
    }
  }
  const start = () => {
    stop()
    timer = setInterval(run, every)
  }
  function stop() {
    if (timer !== undefined) clearInterval(timer)
    timer = undefined
  }
  function onVisibility() {
    if (document.hidden) return stop()
    void run()
    start()
  }
  function onFocus() {
    if (Date.now() - lastRun >= FOCUS_GAP_MS) void run()
  }

  onMounted(() => {
    open = true
    lastRun = Date.now()
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

  return { run }
}
