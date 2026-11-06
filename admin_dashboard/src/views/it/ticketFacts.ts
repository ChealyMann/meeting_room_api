// What an IT setup row shows besides the booking itself: whether it is still to do, how soon it
// starts, the IT items with their icons, the staff, and its state.
import { computed, type Ref } from 'vue'

import type { ITTicketItem } from '../../api/types'
import { itItemIcon } from '../../utils/itQueue'
import { startsIn } from '../../utils/reviewQueue'

export function useTicketFacts(ticket: Ref<ITTicketItem>, now: Ref<Date>, today: Ref<string>) {
  const b = computed(() => ticket.value.booking)
  /** Still to do: not Ready and not missed. */
  const isOpen = computed(() => !ticket.value.missed && ticket.value.status !== 'READY')
  const soon = computed(() => (isOpen.value && ticket.value.setup_date <= today.value ? startsIn(b.value, now.value) : null))
  const needs = computed(() =>
    ticket.value.items.map((item) => {
      const name = String((item as Record<string, unknown>).name)
      return { name, ...itItemIcon(name) }
    }),
  )
  const staffNames = computed(() => ticket.value.staff.map((s) => s.name_en))
  /** Needs staff, has staff, ready, or missed. */
  const state = computed(() =>
    ticket.value.missed ? 'missed' : ticket.value.status === 'READY' ? 'ready' : ticket.value.staff.length ? 'staffed' : 'waiting',
  )
  return { b, isOpen, soon, needs, staffNames, state }
}
