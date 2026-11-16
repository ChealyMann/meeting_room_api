<script setup lang="ts">
// The Details tab of a booking pop-up (owner pick, 16 Nov 2026: "the same info as Pitika"), in To
// review (Pitika and the room owner), IT setup and My bookings: every session, the meeting, and who
// asks (ID, name, position and department, as kept when sent). Only meeting times, never IT's
// setup times.
import { computed } from 'vue'

import type { BookingDetail } from '../api/types'
import { MEETING_TYPE_LABELS, ROUTE_LABELS } from '../utils/bookingLabels'
import { formatDay, formatPhnomPenh } from '../utils/time'

const props = defineProps<{ booking: BookingDetail }>()

const hhmm = (time: string) => time.slice(0, 5)
const info = (key: string) => (props.booking.requester_info[key] as string | null | undefined) || null
/** Every session, in order: a booking can run over several days (up to 20 sessions). */
const sessions = computed(() =>
  [...(props.booking.sessions.length ? props.booking.sessions : [props.booking.first_session])].sort((a, b) =>
    `${a.date} ${a.start_time}`.localeCompare(`${b.date} ${b.start_time}`),
  ),
)
const invited = computed(() => {
  const n = props.booking.participant_emails.length
  return n ? `${n} by email` : null
})
</script>

<template>
  <div class="booking-details">
    <h3 class="sessions-head">
      When <span>· {{ sessions.length }} {{ sessions.length === 1 ? 'session' : 'sessions' }}</span>
    </h3>
    <ul class="sessions">
      <li v-for="s in sessions" :key="`${s.date} ${s.start_time}`">
        <span>{{ formatDay(s.date) }}</span>
        <span class="mono">{{ hhmm(s.start_time) }}–{{ hhmm(s.end_time) }}</span>
      </li>
    </ul>

    <h3>Meeting</h3>
    <dl class="details">
      <div><dt>Meeting type</dt><dd>{{ MEETING_TYPE_LABELS[booking.meeting_type] ?? booking.meeting_type }}</dd></div>
      <div><dt>Attendees</dt><dd class="mono">{{ booking.attendees }}</dd></div>
      <div><dt>Purpose</dt><dd class="wrap" :class="{ none: !booking.meeting_purpose }">{{ booking.meeting_purpose || 'None' }}</dd></div>
      <div><dt>Route</dt><dd>{{ ROUTE_LABELS[booking.route] ?? booking.route }}</dd></div>
      <div v-if="booking.route === 'R2'">
        <dt>Why private</dt>
        <dd class="wrap" :class="{ none: !booking.private_justification }">{{ booking.private_justification || 'No reason given' }}</dd>
      </div>
      <div><dt>Invited</dt><dd :class="{ none: !invited }">{{ invited ?? 'No one' }}</dd></div>
      <div><dt>Sent</dt><dd class="mono">{{ formatPhnomPenh(booking.created_at) }}</dd></div>
    </dl>

    <h3>Booker</h3>
    <dl class="details booker">
      <div><dt>Staff ID</dt><dd class="mono" :class="{ none: !info('staff_id') }">{{ info('staff_id') ?? 'None' }}</dd></div>
      <div>
        <dt>Name</dt>
        <dd>{{ info('name_en') ?? booking.requester.name_en }} <span v-if="info('name_kh')" class="sub kh">{{ info('name_kh') }}</span></dd>
      </div>
      <div><dt>Position</dt><dd :class="{ none: !info('position') }">{{ info('position') ?? 'None' }}</dd></div>
      <div>
        <dt>Department</dt>
        <dd :class="{ none: !info('department') && !info('division') }">{{ info('department') ?? info('division') ?? 'None' }} <span v-if="info('department') && info('division')" class="sub">{{ info('division') }}</span></dd>
      </div>
    </dl>
  </div>
</template>

<style scoped>
h3 {
  margin: 20px 0 4px;
  font-size: 13px;
  font-weight: 600;
}
h3:first-child {
  margin-top: 0;
}
.sessions-head span {
  font-weight: 400;
  color: var(--color-intaglio);
}
/* Every session on its own line: the day, then the times at the end. */
.sessions {
  margin: 0;
  padding: 0;
  list-style: none;
}
.sessions li {
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
.sub {
  display: block;
  font-size: 12.5px;
  color: var(--color-intaglio);
}
@media (max-width: 420px) {
  .details > div {
    grid-template-columns: 1fr;
    gap: 2px;
  }
}
</style>
