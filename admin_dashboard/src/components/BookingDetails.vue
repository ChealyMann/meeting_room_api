<script setup lang="ts">
// The Details tab of a booking pop-up (owner pick, 16 Nov 2026: "the same info as Pitika"), in To
// review (Pitika and the room owner), IT setup and My bookings: every session, the meeting, and who
// asks (ID, name, position and department, as kept when sent). Only meeting times, never IT's
// setup times. The Room section (owner pick, 17 Nov 2026, look A "Rows") comes right after When:
// the room, floor and building, the office with a map link, seats and type, and the owner of a
// private room ("You" when the reader owns it). It replaces the room line at the panel's top.
import { ExternalLink } from 'lucide-vue-next'
import { computed } from 'vue'

import type { BookingDetail } from '../api/types'
import { useSessionStore } from '../stores/session'
import { MEETING_TYPE_LABELS, ROUTE_LABELS } from '../utils/bookingLabels'
import { mapSearchUrl } from '../utils/mapLink'
import PanelSection from './PanelSection.vue'
import { formatDay, formatPhnomPenh } from '../utils/time'

const props = defineProps<{ booking: BookingDetail }>()
const session = useSessionStore()

const room = computed(() => props.booking.room)
const mapUrl = computed(() => mapSearchUrl(room.value.map_query))
const ownerIsMe = computed(() => !!room.value.owner && room.value.owner.id === session.user?.id)

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
    <PanelSection class="sessions-head" :title="`When · ${sessions.length} ${sessions.length === 1 ? 'session' : 'sessions'}`">
      <ul class="sessions">
        <li v-for="s in sessions" :key="`${s.date} ${s.start_time}`">
          <span>{{ formatDay(s.date) }}</span>
          <span class="mono">{{ hhmm(s.start_time) }}–{{ hhmm(s.end_time) }}</span>
        </li>
      </ul>
    </PanelSection>

    <PanelSection title="Room">
      <dl class="details">
        <div>
          <dt>Room</dt>
          <dd>
            {{ room.name_en }}<span v-if="room.is_private" class="private">Private</span>
            <span class="sub kh">{{ room.name_kh }}</span>
          </dd>
        </div>
        <div>
          <dt>Where</dt>
          <dd>{{ room.floor.floor_label }} <span class="sub">{{ room.building.name_en }}</span></dd>
        </div>
        <div>
          <dt>Office</dt>
          <dd>
            {{ room.location.name_en }}, {{ room.province.name_en }}
            <span v-if="mapUrl" class="sub">
              <a class="map" :href="mapUrl" target="_blank" rel="noopener">Open in Maps<ExternalLink :size="12" aria-hidden="true" /></a>
            </span>
          </dd>
        </div>
        <div>
          <dt>Seats</dt>
          <dd><span class="mono">{{ room.capacity }}</span> · {{ room.category.name_en }}</dd>
        </div>
        <div v-if="room.owner">
          <dt>Owner</dt>
          <dd>
            <template v-if="ownerIsMe">You</template>
            <template v-else>{{ room.owner.name_en }} <span class="sub kh">{{ room.owner.name_kh }}</span></template>
          </dd>
        </div>
      </dl>
    </PanelSection>

    <PanelSection title="Meeting">
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
    </PanelSection>

    <PanelSection title="Booker">
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
    </PanelSection>
  </div>
</template>

<style scoped>
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
.sessions li:last-child,
.details > div:last-child {
  border-bottom: 0;
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
/* "Private" after the room name: a quiet tag, not a status. */
.private {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 8px;
  border-radius: 999px;
  background: var(--color-field-disabled);
  color: var(--color-intaglio);
  font-size: 11.5px;
  vertical-align: 1px;
}
.map {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--color-ink);
  text-underline-offset: 3px;
}
.map:focus-visible {
  outline: 2px solid var(--color-ink);
  outline-offset: 2px;
  border-radius: 4px;
}
@media (max-width: 420px) {
  .details > div {
    grid-template-columns: 1fr;
    gap: 2px;
  }
}
</style>
