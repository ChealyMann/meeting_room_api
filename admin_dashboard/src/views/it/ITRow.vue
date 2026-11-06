<script setup lang="ts">
// One IT setup as a soft row (owner pick, 6 Nov 2026: "Clean 3 · Soft rows", the same row as
// To review): the meeting time first (no set-up time on the row: it stays in the panel), the
// room's photo with the reference, the title, the room, soft tags for what to set up and the
// staff, then the status and the buttons the ticket's state allows. IT sets up before every
// session (owner decision, 6 Nov 2026): a booking with several sessions comes once per session
// (`session`), with that session's time and "Session 2 of 5". Staff are for all of them, and can be
// assigned or changed while sessions remain, even on a confirmed booking; Mark ready is once, on
// the first session (owner decisions, 6 Nov 2026), and confirms the booking.
import { computed, toRef } from 'vue'

import type { ITSetup, ITTicketItem } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import SoftRow from '../../components/SoftRow.vue'
import StaffAvatar from '../../components/StaffAvatar.vue'
import { sessionDate } from '../../utils/itQueue'
import { startsAt } from '../../utils/reviewQueue'
import { formatDay, phnomPenhClock } from '../../utils/time'
import { useTicketFacts } from './ticketFacts'

const props = defineProps<{
  ticket: ITTicketItem
  /** One session's setup of a booking with several, or null (the booking as a whole). */
  session?: ITSetup | null
  /** The room's cover thumbnail, or null. */
  photo: string | null
  now: Date
  today: string
  /** false: read only (My tasks). */
  actions: boolean
  current?: boolean
}>()
const emit = defineEmits<{ open: []; assign: []; ready: [] }>()

const { b, isOpen, soon, needs, staffNames, state } = useTicketFacts(toRef(props, 'ticket'), toRef(props, 'now'), toRef(props, 'today'))
const hhmm = (time: string) => time.slice(0, 5)
const start = computed(() => props.session?.start_time ?? b.value.first_session.start_time)
const end = computed(() => props.session?.end_time ?? b.value.first_session.end_time)
const date = computed(() => (props.session ? sessionDate(props.session) : b.value.first_session.date))
const day = computed(() => (date.value === props.today ? 'Today' : formatDay(date.value).slice(0, -5)))
const more = computed(() => {
  if (props.session) return `Session ${props.session.session_number} of ${props.ticket.setups.length}`
  return b.value.session_count > 1 ? `+${b.value.session_count - 1} more` : null
})
/** A session after the first: a reminder, with no Mark ready of its own. */
const laterSession = computed(() => (props.session?.session_number ?? 1) > 1)
/** A session to come with nobody on it (also when the first session was missed). */
const needsStaff = computed(() => !!props.session && !staffNames.value.length)
/** How soon this row's session starts, while the setup is still to do. */
const startsSoon = computed(() => {
  if (!props.session) return soon.value
  return (isOpen.value || needsStaff.value) && props.session.date <= props.today ? startsAt(date.value, start.value, props.now) : null
})
/** Ready, missed, how soon it starts, or what comes next. */
const status = computed(() => {
  if (needsStaff.value) return startsSoon.value ? { text: startsSoon.value, tone: 'alert' } : { text: 'Next: Assign staff', tone: 'next' }
  const again = { text: 'Set up again for this session', tone: 'next' }
  // A later session of a booking made ready (or missed) once: the same staff set up again.
  if (laterSession.value && (state.value === 'ready' || state.value === 'missed')) return again
  if (state.value === 'missed') return { text: 'Missed · not marked ready', tone: 'alert' }
  if (state.value === 'ready') {
    const at = props.ticket.ready_at ? ` · ${phnomPenhClock(new Date(props.ticket.ready_at))}` : ''
    return { text: `Ready${at}`, tone: 'ok' }
  }
  if (startsSoon.value) return { text: startsSoon.value, tone: 'alert' }
  if (state.value === 'staffed') return laterSession.value ? again : { text: 'Next: Mark ready', tone: 'next' }
  return { text: 'Next: Assign staff', tone: 'next' }
})
</script>

<template>
  <SoftRow
    :class="`state-${state}`"
    :data-ticket="ticket.id"
    :start="hhmm(start)"
    :end="hhmm(end)"
    :day="day"
    :more="more"
    :photo="photo"
    :photo-alt="b.room.name_en"
    :reference="b.reference_code"
    :title="b.meeting_title"
    :current="current"
    @open="emit('open')"
  >
    <template #line>
      <span class="kh">{{ b.room.name_kh }}</span> · {{ b.room.name_en }}
    </template>
    <template #tags>
      <span v-for="n in needs" :key="n.name" class="soft-tag chk"><component :is="n.icon" aria-hidden="true" />{{ n.name }}</span>
      <span v-if="ticket.special_requirements" class="soft-tag note" :title="ticket.special_requirements">
        Note<span class="sr-only">: {{ ticket.special_requirements }}</span>
      </span>
      <span v-if="!staffNames.length" class="soft-tag warn staff">No staff yet</span>
      <span v-else class="soft-tag ink people" :title="staffNames.join(', ')">
        <span class="faces"><StaffAvatar v-for="s in ticket.staff" :key="s.id" :name="s.name_en" :photo="s.avatar_url ?? null" :size="18" /></span>
        <span class="staff">{{ staffNames.join(', ') }}</span>
      </span>
    </template>
    <template #status>
      <span class="state-word" :class="status.tone">{{ status.text }}</span>
    </template>
    <template v-if="actions && (isOpen || session)" #actions>
      <BaseButton v-if="ticket.status === 'RECEIVED'" variant="primary" @click="emit('assign')">Assign staff</BaseButton>
      <template v-else>
        <BaseButton aria-label="Change staff" class="change" @click="emit('assign')">Change</BaseButton>
        <BaseButton v-if="isOpen && !laterSession" variant="primary" @click="emit('ready')">Mark ready</BaseButton>
      </template>
    </template>
  </SoftRow>
</template>

<style scoped>
.kh {
  font-family: var(--font-kh);
  font-weight: 500;
  color: var(--color-ink);
}
.soft-tag :deep(svg.lucide) {
  flex: none;
  width: 13px;
  height: 13px;
}
.faces {
  display: inline-flex;
}
.faces > :deep(.staff-avatar) {
  box-shadow: 0 0 0 2px var(--color-field-disabled);
}
.faces > :deep(.staff-avatar + .staff-avatar) {
  margin-left: -5px;
}
.state-word {
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}
.state-word.alert {
  color: var(--color-crimson);
}
.state-word.ok {
  color: var(--color-ok);
}
.state-word.next {
  font-weight: 400;
  color: var(--color-intaglio);
}
.change {
  border-color: transparent;
  background: var(--color-field-disabled);
}
</style>
