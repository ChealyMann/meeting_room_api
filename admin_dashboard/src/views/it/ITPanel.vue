<script setup lang="ts">
// One IT setup in the side panel (spec Part B, "Panel"): the room photo, the booking's full
// process bar, what to set up, and the meeting. The foot has Close and the row's buttons.
import { Check } from 'lucide-vue-next'
import { computed } from 'vue'

import type { BookingDetail, ITTicketItem } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import ProcessBar from '../../components/ProcessBar.vue'
import RoomPhoto from '../../components/RoomPhoto.vue'
import { buildHistory } from '../../utils/bookingHistory'
import { sessionDate } from '../../utils/itQueue'
import { formatDay } from '../../utils/time'

const props = defineProps<{
  ticket: ITTicketItem
  /** The full booking (for the process bar), or null while it loads or when it failed. */
  detail: BookingDetail | null
  photo: string | null
  place: string | null
  actions: boolean
}>()
const emit = defineEmits<{ close: []; assign: []; ready: [] }>()

const b = computed(() => props.ticket.booking)
const steps = computed(() => (props.detail ? buildHistory(props.detail).steps : []))
const hhmm = (time: string) => time.slice(0, 5)
const names = computed(() => props.ticket.items.map((i) => String((i as Record<string, unknown>).name)).join(', '))
const staffText = computed(() => (props.ticket.staff.length ? props.ticket.staff.map((s) => s.name_en).join(', ') : 'No staff yet'))
const isOpen = computed(() => !props.ticket.missed && props.ticket.status !== 'READY')
/** IT sets up before every session (owner decision, 6 Nov 2026): all of them, in order. */
const setups = computed(() =>
  props.ticket.setups?.length
    ? props.ticket.setups
    : [{ session_number: 1, date: props.ticket.setup_date, setup_time: props.ticket.setup_time, start_time: b.value.first_session.start_time, end_time: b.value.first_session.end_time }],
)
const subtitle = computed(() => {
  if (props.ticket.missed) return 'Missed · not marked ready'
  if (props.ticket.status === 'READY') return 'Ready'
  return props.ticket.staff.length ? 'Staff set · not ready' : 'Needs staff'
})
</script>

<template>
  <SidePanel :open="true" :title="b.meeting_title" :subtitle="subtitle" :serial="b.reference_code" @close="emit('close')">
    <div class="it-panel">
      <figure class="hero">
        <RoomPhoto class="photo" :path="photo" :alt="b.room.name_en" />
        <figcaption>
          <span class="kh">{{ b.room.name_kh }}</span>
          <span>{{ b.room.name_en }}<template v-if="place"> · {{ place }}</template></span>
        </figcaption>
      </figure>

      <ProcessBar v-if="steps.length" :steps="steps" size="large" />

      <h3>When <span class="count">· {{ setups.length }} {{ setups.length === 1 ? 'session' : 'sessions' }}</span></h3>
      <ul class="setups">
        <li v-for="s in setups" :key="s.session_number">
          <span>{{ formatDay(sessionDate(s)) }}</span>
          <span class="mono">{{ hhmm(s.start_time) }}–{{ hhmm(s.end_time) }}</span>
        </li>
      </ul>

      <h3>Setup</h3>
      <dl class="details">
        <div><dt>Items</dt><dd>{{ names }}</dd></div>
        <div>
          <dt>Special needs</dt>
          <dd class="wrap" :class="{ none: !ticket.special_requirements }">{{ ticket.special_requirements || 'None' }}</dd>
        </div>
        <div>
          <dt>Technician notes</dt>
          <dd class="wrap" :class="{ none: !ticket.technician_notes }">{{ ticket.technician_notes || 'None' }}</dd>
        </div>
        <div>
          <dt>Staff</dt>
          <dd :class="{ none: !ticket.staff.length }">{{ staffText }}</dd>
        </div>
      </dl>

      <h3>Meeting</h3>
      <dl class="details">
        <div><dt>Attendees</dt><dd>{{ b.attendees }}</dd></div>
        <div><dt>Booker</dt><dd>{{ b.requester.name_en }}</dd></div>
      </dl>
    </div>

    <template #foot>
      <div class="foot">
        <BaseButton variant="quiet" @click="emit('close')">Close</BaseButton>
        <template v-if="actions && isOpen">
          <span class="spacer" />
          <BaseButton v-if="ticket.status === 'RECEIVED'" variant="primary" @click="emit('assign')">Assign staff</BaseButton>
          <template v-else>
            <BaseButton variant="quiet" @click="emit('assign')">Change staff</BaseButton>
            <BaseButton variant="primary" @click="emit('ready')"><Check aria-hidden="true" />Mark ready</BaseButton>
          </template>
        </template>
      </div>
    </template>
  </SidePanel>
</template>

<style scoped>
.hero {
  position: relative;
  margin: -16px -20px 16px;
}
.hero .photo {
  height: 188px;
}
.hero figcaption {
  position: absolute;
  inset: auto 0 0;
  display: grid;
  gap: 1px;
  padding: 28px 20px 12px;
  background: linear-gradient(to top, rgba(26, 6, 6, 0.74), rgba(26, 6, 6, 0));
  color: #fff;
  font-size: 12.5px;
}
.hero .kh {
  font-family: var(--font-kh);
  font-size: 15px;
  font-weight: 500;
}
h3 {
  margin: 20px 0 4px;
  font-size: 13px;
  font-weight: 600;
}
h3 .count {
  font-weight: 400;
  color: var(--color-intaglio);
}
.setups {
  margin: 0;
  padding: 0;
  list-style: none;
}
.setups li {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 7px 0;
  border-bottom: 1px solid var(--color-rule);
  font-size: 13.5px;
}
.details {
  margin: 0;
}
.details > div {
  display: grid;
  grid-template-columns: 116px minmax(0, 1fr);
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--color-rule);
}
.details dt {
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.details dd {
  margin: 0;
  font-size: 13.5px;
  overflow-wrap: anywhere;
}
.wrap {
  white-space: pre-line;
}
.none {
  color: var(--color-ink-off);
}
.mono {
  font-family: var(--font-mono);
}
.foot {
  display: flex;
  flex: 1;
  gap: 8px;
}
.spacer {
  flex: 1;
}
</style>
