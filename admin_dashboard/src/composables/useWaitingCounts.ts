// How many bookings wait for this user now, per menu item (spec 2026-11-05-owner-and-it-pages
// -design, "Shared"): the Pitika's To review and the owner's. Loaded when the rail mounts and
// again after each decision (the To review page sends REVIEW_DECIDED_EVENT).
import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

import { api } from '../api'
import { getOwnerSummary, getPitikaSummary } from '../api/bookings'
import type { ReviewSummary } from '../api/types'
import { useSessionStore } from '../stores/session'

export const REVIEW_DECIDED_EVENT = 'review:decided'

const SOURCES: Array<{ role: string; route: string; load: () => Promise<ReviewSummary> }> = [
  { role: 'PITIKA', route: 'review', load: () => getPitikaSummary(api) },
  { role: 'ROOM_OWNER', route: 'owner-review', load: () => getOwnerSummary(api) },
]

/** Route name → bookings waiting. A failed load leaves its key out (no number shown). */
export function useWaitingCounts(): Ref<Record<string, number>> {
  const session = useSessionStore()
  const counts = ref<Record<string, number>>({})

  async function load() {
    const mine = SOURCES.filter((s) => session.roleCodes.includes(s.role))
    const answers = await Promise.allSettled(mine.map((s) => s.load()))
    const next: Record<string, number> = {}
    answers.forEach((a, k) => {
      if (a.status === 'fulfilled') next[mine[k]!.route] = a.value.waiting
    })
    counts.value = next
  }

  onMounted(() => {
    void load()
    window.addEventListener(REVIEW_DECIDED_EVENT, load)
  })
  onBeforeUnmount(() => window.removeEventListener(REVIEW_DECIDED_EVENT, load))
  return counts
}
