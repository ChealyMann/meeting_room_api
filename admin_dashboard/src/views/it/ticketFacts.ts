// What a setup row and a setup card both show (owner decision, 6 Nov 2026: Rows or Cards).
import { computed, type Ref } from 'vue'

import type { ITTicketItem } from '../../api/types'
import { itItemIcon } from '../../utils/itQueue'
import { startsIn } from '../../utils/reviewQueue'
import { formatDay } from '../../utils/time'

export function useTicketFacts(ticket: Ref<ITTicketItem>, now: Ref<Date>, today: Ref<string>) {
  const b = computed(() => ticket.value.booking)
  const hhmm = (time: string) => time.slice(0, 5)
  /** Still to do: not Ready and not missed. */
  const isOpen = computed(() => !ticket.value.missed && ticket.value.status !== 'READY')
  const soon = computed(() => (isOpen.value && ticket.value.setup_date <= today.value ? startsIn(b.value, now.value) : null))
  /** "Today", or "Fri 6 Nov": the setup day. */
  const setupDay = computed(() => (ticket.value.setup_date === today.value ? 'Today' : formatDay(ticket.value.setup_date).slice(0, -5)))
  const setupTime = computed(() => hhmm(ticket.value.setup_time))
  const meetingTimes = computed(() => `${hhmm(b.value.first_session.start_time)}–${hhmm(b.value.first_session.end_time)}`)
  const needs = computed(() =>
    ticket.value.items.map((item) => {
      const name = String((item as Record<string, unknown>).name)
      return { name, ...itItemIcon(name) }
    }),
  )
  const staffNames = computed(() => ticket.value.staff.map((s) => s.name_en))
  /** The dot on the time line: needs staff, has staff, ready, or missed. */
  const state = computed(() =>
    ticket.value.missed ? 'missed' : ticket.value.status === 'READY' ? 'ready' : ticket.value.staff.length ? 'staffed' : 'waiting',
  )
  return { b, isOpen, soon, setupDay, setupTime, meetingTimes, needs, staffNames, state }
}
