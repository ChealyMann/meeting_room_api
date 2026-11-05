// How many bookings wait for this user now, per menu item (spec 2026-11-05-owner-and-it-pages
// -design, "Shared"): the Pitika's To review and the owner's. Loaded when the rail mounts; the
// To review page then reports each summary it loads (reportWaiting), so the menu and the ring
// always show the same number with no extra call.
import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

import { api } from '../api'
import { getOwnerSummary, getPitikaSummary } from '../api/bookings'
import { getItSummary, listTicketPage } from '../api/it'
import { useSessionStore } from '../stores/session'

export const REVIEW_SUMMARY_EVENT = 'review:summary'

/** The To review page says how many wait now for its route (`review`, `owner-review`). */
export function reportWaiting(route: string, waiting: number): void {
  window.dispatchEvent(new CustomEvent(REVIEW_SUMMARY_EVENT, { detail: { route, waiting } }))
}

// What waits for me: bookings to decide; for the IT Lead, setups to assign; for IT Staff, my tasks.
const SOURCES: Array<{ role: string; route: string; load: () => Promise<number> }> = [
  { role: 'PITIKA', route: 'review', load: async () => (await getPitikaSummary(api)).waiting },
  { role: 'ROOM_OWNER', route: 'owner-review', load: async () => (await getOwnerSummary(api)).waiting },
  { role: 'IT_LEAD', route: 'it-setup', load: async () => (await getItSummary(api)).to_assign },
  {
    role: 'IT_STAFF',
    route: 'my-tasks',
    load: async () => (await listTicketPage(api, { state: 'in_progress', mine: true, page: 1, size: 1 })).total,
  },
]

/** Route name → bookings waiting. A failed load leaves its key out (no number shown). */
export function useWaitingCounts(): Ref<Record<string, number>> {
  const session = useSessionStore()
  const counts = ref<Record<string, number>>({})
  // Routes the page already reported: newer than the rail's first load, which must not undo them.
  const reported = new Set<string>()

  function onReport(event: Event) {
    const { route, waiting } = (event as CustomEvent<{ route: string; waiting: number }>).detail
    reported.add(route)
    counts.value = { ...counts.value, [route]: waiting }
  }

  async function loadFirst() {
    const mine = SOURCES.filter((s) => session.roleCodes.includes(s.role))
    const answers = await Promise.allSettled(mine.map((s) => s.load()))
    const next = { ...counts.value }
    answers.forEach((a, k) => {
      const route = mine[k]!.route
      if (a.status === 'fulfilled' && !reported.has(route)) next[route] = a.value
    })
    counts.value = next
  }

  onMounted(() => {
    window.addEventListener(REVIEW_SUMMARY_EVENT, onReport)
    void loadFirst()
  })
  onBeforeUnmount(() => window.removeEventListener(REVIEW_SUMMARY_EVENT, onReport))
  return counts
}
