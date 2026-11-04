<script setup lang="ts">
// One booking, read only (DSH-B02 to B04): details, sessions, services and history. The Admin
// cannot approve, reject, cancel or edit, so there is no form. The door pass shows only when
// the Admin asks, and only for a confirmed booking (the API's own rule).
import { CalendarArrowDown, CircleAlert, Eye } from 'lucide-vue-next'
import { computed, ref } from 'vue'

import { api } from '../../api'
import { getBookingIcs, getDoorPass } from '../../api/bookings'
import { ApiError } from '../../api/errors'
import type { BookingDetail, DoorPassOut } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import { MEETING_TYPE_LABELS, ROUTE_LABELS, statusLabel } from '../../utils/bookingLabels'
import { formatDay, formatPhnomPenh } from '../../utils/time'

const props = defineProps<{ booking: BookingDetail }>()
const emit = defineEmits<{ close: [] }>()

type Tab = 'details' | 'sessions' | 'services' | 'history'
const tab = ref<Tab>('details')
const TABS: Array<{ id: Tab; label: () => string }> = [
  { id: 'details', label: () => 'Details' },
  { id: 'sessions', label: () => `Sessions ${props.booking.sessions.length}` },
  { id: 'services', label: () => 'Services' },
  { id: 'history', label: () => 'History' },
]

const hhmm = (time: string) => time.slice(0, 5)
const names = (list: Array<Record<string, unknown>>) => list.map((x) => String(x.name)).join(', ')

/** The booker as copied when the booking was sent (BR-FRM-06). */
const INFO_LABELS: Array<[string, string]> = [
  ['name_en', 'Name'],
  ['name_kh', 'Khmer name'],
  ['staff_id', 'Staff ID'],
  ['position', 'Position'],
  ['division', 'Division'],
  ['department', 'Department'],
  ['office', 'Office'],
  ['email', 'Email'],
  ['phone', 'Phone'],
]
const booker = computed(() =>
  INFO_LABELS.map(([key, label]) => ({ label, value: props.booking.requester_info[key] as string | null | undefined })),
)

const STAGES: Record<string, string> = { PITIKA: 'Pitika', OWNER: 'Room owner' }
const DECISIONS: Record<string, string> = { APPROVED: 'approved', REJECTED: 'rejected', NOT_REQUIRED: 'not needed' }
const REJECTED_BY: Record<string, string> = {
  PITIKA: 'Rejected by Pitika',
  OWNER: 'Rejected by the room owner',
  SYSTEM: 'Rejected by the system',
}
// The API writes a rejection twice: as a REJECTED review and as `rejection`. Show it once.
const reviews = computed(() =>
  props.booking.rejection ? props.booking.reviews.filter((r) => r.decision !== 'REJECTED') : props.booking.reviews,
)
const IT_STATUS: Record<string, string> = { RECEIVED: 'Received', ASSIGNED: 'Staff assigned', READY: 'Ready' }

// The door pass: undefined = hidden, else the API's answer or its refusal.
const doorPass = ref<DoorPassOut | undefined>(undefined)
const doorError = ref('')
const doorBusy = ref(false)
async function showDoorPass() {
  doorBusy.value = true
  doorError.value = ''
  try {
    doorPass.value = await getDoorPass(api, props.booking.id)
  } catch (err) {
    doorError.value = err instanceof ApiError ? err.message : 'Something went wrong.'
  } finally {
    doorBusy.value = false
  }
}
function hideDoorPass() {
  doorPass.value = undefined
  doorError.value = ''
}

const icsBusy = ref(false)
const icsError = ref('')
async function downloadIcs() {
  icsBusy.value = true
  icsError.value = ''
  try {
    const blob = await getBookingIcs(api, props.booking.id)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${props.booking.reference_code}.ics`
    // Safari needs the link in the page, and the file URL alive until the download starts.
    document.body.append(link)
    link.click()
    link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 0)
  } catch (err) {
    icsError.value = err instanceof ApiError ? err.message : 'Something went wrong.'
  } finally {
    icsBusy.value = false
  }
}
</script>

<template>
  <SidePanel
    :open="true"
    :title="booking.meeting_title"
    :subtitle="statusLabel(booking.display_status)"
    :serial="booking.reference_code"
    @close="emit('close')"
  >
    <div class="tabs" role="tablist" aria-label="Booking">
      <button
        v-for="t in TABS"
        :id="`tab-${t.id}`"
        :key="t.id"
        type="button"
        role="tab"
        :aria-selected="tab === t.id"
        :aria-controls="`tabpanel-${t.id}`"
        @click="tab = t.id"
      >
        {{ t.label() }}
      </button>
    </div>

    <section v-show="tab === 'details'" id="tabpanel-details" role="tabpanel" aria-labelledby="tab-details">
      <dl class="details">
        <div>
          <dt>Room</dt>
          <dd>
            <RouterLink class="room" :to="{ name: 'home', query: { room: String(booking.room.id) } }">
              <span class="kh">{{ booking.room.name_kh }}</span>
              <span class="en">{{ booking.room.name_en }} · {{ booking.room.location.name_en }}</span>
            </RouterLink>
          </dd>
        </div>
        <div><dt>Route</dt><dd>{{ ROUTE_LABELS[booking.route] ?? booking.route }}</dd></div>
        <div><dt>Meeting type</dt><dd>{{ MEETING_TYPE_LABELS[booking.meeting_type] ?? booking.meeting_type }}</dd></div>
        <div><dt>Purpose</dt><dd class="wrap" :class="{ none: !booking.meeting_purpose }">{{ booking.meeting_purpose || 'None' }}</dd></div>
        <div><dt>Attendees</dt><dd class="mono">{{ booking.attendees }}</dd></div>
        <div v-if="booking.private_justification"><dt>Why private</dt><dd class="wrap">{{ booking.private_justification }}</dd></div>
        <div>
          <dt>Participants</dt>
          <dd :class="{ none: !booking.participant_emails.length }">
            <template v-if="booking.participant_emails.length">
              <span v-for="email in booking.participant_emails" :key="email" class="line">{{ email }}</span>
            </template>
            <template v-else>None</template>
          </dd>
        </div>
        <div v-if="booking.status === 'CONFIRMED'">
          <dt>Door pass</dt>
          <dd class="door-pass">
            <template v-if="doorPass === undefined && !doorError">
              <span class="none">Hidden</span>
              <BaseButton class="small" :busy="doorBusy" @click="showDoorPass">
                <Eye v-if="!doorBusy" aria-hidden="true" />
                Show door pass
              </BaseButton>
            </template>
            <template v-else>
              <span v-if="doorError" class="refused">{{ doorError }}</span>
              <template v-else-if="doorPass">
                <span class="mono code">{{ doorPass.passcode }}</span>
                <span class="until">Valid until {{ formatPhnomPenh(doorPass.expires_at) }}</span>
                <span v-if="doorPass.expired" class="expired">Expired</span>
              </template>
              <BaseButton variant="quiet" class="small" @click="hideDoorPass">Hide</BaseButton>
            </template>
          </dd>
        </div>
      </dl>

      <h3>Booker</h3>
      <dl class="details">
        <div v-for="row in booker" :key="row.label">
          <dt>{{ row.label }}</dt>
          <dd :class="{ none: !row.value, kh: row.label === 'Khmer name' }">{{ row.value || 'None' }}</dd>
        </div>
        <div><dt>Sent</dt><dd class="mono">{{ formatPhnomPenh(booking.created_at) }}</dd></div>
      </dl>
    </section>

    <section v-show="tab === 'sessions'" id="tabpanel-sessions" role="tabpanel" aria-labelledby="tab-sessions">
      <ul class="sessions">
        <li v-for="s in booking.sessions" :key="s.id">
          <span>{{ formatDay(s.date) }}</span>
          <span class="mono">{{ hhmm(s.start_time) }}–{{ hhmm(s.end_time) }}</span>
        </li>
      </ul>
      <p class="ends">Ends {{ formatDay(booking.last_end.date) }} {{ hhmm(booking.last_end.time) }}</p>
    </section>

    <section v-show="tab === 'services'" id="tabpanel-services" role="tabpanel" aria-labelledby="tab-services">
      <h3>Food</h3>
      <p v-if="!booking.catering" class="none">No food ordered.</p>
      <dl v-else class="details">
        <div><dt>Packages</dt><dd>{{ names(booking.catering.packages) }}</dd></div>
        <div><dt>Servings</dt><dd class="mono">{{ booking.catering.servings }}</dd></div>
        <div><dt>Delivery</dt><dd>{{ formatDay(booking.catering.delivery_date) }} {{ hhmm(booking.catering.delivery_time) }}</dd></div>
        <div><dt>Remarks</dt><dd class="wrap" :class="{ none: !booking.catering.remarks }">{{ booking.catering.remarks || 'None' }}</dd></div>
        <div><dt>Pitika notes</dt><dd class="wrap" :class="{ none: !booking.catering.approver_notes }">{{ booking.catering.approver_notes || 'None' }}</dd></div>
        <div v-if="booking.catering.decided_at">
          <dt>Approved</dt>
          <dd>{{ booking.catering.decided_by?.name_en ?? 'Unknown' }} · <span class="mono">{{ formatPhnomPenh(booking.catering.decided_at) }}</span></dd>
        </div>
      </dl>

      <h3>IT help</h3>
      <p v-if="!booking.it" class="none">No IT help asked.</p>
      <dl v-else class="details">
        <div><dt>Items</dt><dd>{{ names(booking.it.items) }}</dd></div>
        <div><dt>Special needs</dt><dd class="wrap" :class="{ none: !booking.it.special_requirements }">{{ booking.it.special_requirements || 'None' }}</dd></div>
        <div><dt>Status</dt><dd>{{ IT_STATUS[booking.it.status] ?? booking.it.status }}</dd></div>
        <div>
          <dt>Staff</dt>
          <dd :class="{ none: !booking.it.staff.length }">{{ booking.it.staff.map((s) => s.name_en).join(', ') || 'None yet' }}</dd>
        </div>
        <div><dt>Setup</dt><dd>{{ formatDay(booking.it.setup_date) }} {{ hhmm(booking.it.setup_time) }}</dd></div>
        <div><dt>Technician notes</dt><dd class="wrap" :class="{ none: !booking.it.technician_notes }">{{ booking.it.technician_notes || 'None' }}</dd></div>
        <div v-if="booking.it.forwarded_at"><dt>Sent to IT</dt><dd class="mono">{{ formatPhnomPenh(booking.it.forwarded_at) }}</dd></div>
        <div v-if="booking.it.assigned_at"><dt>Assigned</dt><dd class="mono">{{ formatPhnomPenh(booking.it.assigned_at) }}</dd></div>
        <div v-if="booking.it.ready_at"><dt>Ready</dt><dd class="mono">{{ formatPhnomPenh(booking.it.ready_at) }}</dd></div>
      </dl>
    </section>

    <section v-show="tab === 'history'" id="tabpanel-history" role="tabpanel" aria-labelledby="tab-history">
      <ol class="history">
        <li>
          <b>Sent</b>
          <span>{{ booking.requester.name_en }}</span>
          <span class="mono">{{ formatPhnomPenh(booking.created_at) }}</span>
        </li>
        <li v-for="(r, i) in reviews" :key="i">
          <b>{{ STAGES[r.stage] ?? r.stage }} {{ DECISIONS[r.decision] ?? r.decision }}</b>
          <span v-if="r.reviewer">{{ r.reviewer.name_en }}</span>
          <span class="mono">{{ formatPhnomPenh(r.reviewed_at) }}</span>
          <span v-if="r.notes" class="note">{{ r.notes }}</span>
        </li>
        <li v-if="booking.rejection">
          <b>{{ REJECTED_BY[booking.rejection.rejected_by] ?? booking.rejection.rejected_by }}</b>
          <span v-if="booking.rejection.actor">{{ booking.rejection.actor.name_en }}</span>
          <span class="mono">{{ formatPhnomPenh(booking.rejection.decided_at) }}</span>
          <span class="note">{{ booking.rejection.reason }}</span>
        </li>
        <li v-if="booking.cancelled_at">
          <b>Cancelled</b>
          <span class="mono">{{ formatPhnomPenh(booking.cancelled_at) }}</span>
          <span v-if="booking.cancel_reason" class="note">{{ booking.cancel_reason }}</span>
        </li>
      </ol>
    </section>

    <div v-if="icsError" class="summary" role="alert">
      <CircleAlert aria-hidden="true" />
      <b>{{ icsError }}</b>
    </div>

    <template #foot>
      <BaseButton variant="quiet" class="close" @click="emit('close')">Close</BaseButton>
      <BaseButton :busy="icsBusy" @click="downloadIcs">
        <CalendarArrowDown v-if="!icsBusy" aria-hidden="true" />
        Calendar file
      </BaseButton>
    </template>
  </SidePanel>
</template>

<style scoped>
.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--color-rule);
}
.tabs button {
  margin-bottom: -1px;
  padding: 8px 10px;
  border: 0;
  border-bottom: 2px solid transparent;
  background: none;
  color: var(--color-intaglio);
  font-size: 13px;
  cursor: pointer;
}
.tabs button[aria-selected='true'] {
  border-bottom-color: var(--color-crimson);
  color: var(--color-ink);
  font-weight: 500;
}
h3 {
  margin: 20px 0 4px;
  font-size: 13px;
  font-weight: 600;
}
section > h3:first-child {
  margin-top: 0;
}
.details {
  margin: 0;
}
.details > div {
  display: grid;
  grid-template-columns: 128px minmax(0, 1fr);
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
.room {
  color: inherit;
  text-decoration: none;
}
.room:hover .en {
  text-decoration: underline;
}
.kh {
  display: block;
  font-family: var(--font-kh);
  font-weight: 500;
}
.en {
  display: block;
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.line {
  display: block;
}
.wrap {
  white-space: pre-line;
}
.none {
  margin: 0;
  color: var(--color-ink-off);
  font-size: 13px;
}
.door-pass {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.code {
  font-size: 15px;
  letter-spacing: 0.04em;
}
.until {
  font-size: 12px;
  color: var(--color-intaglio);
}
.expired {
  padding: 1px 6px;
  border: 1px solid var(--color-crimson);
  border-radius: 6px;
  color: var(--color-crimson);
  font-size: 11.5px;
  font-weight: 500;
}
.refused {
  color: var(--color-crimson);
  font-size: 13px;
}
.sessions,
.history {
  margin: 0;
  padding: 0;
  list-style: none;
  border-top: 1px solid var(--color-rule);
}
.sessions li {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--color-rule);
  font-size: 13.5px;
}
.ends {
  margin: 12px 0 0;
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.history li {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--color-rule);
  font-size: 13px;
}
.history b {
  font-weight: 500;
}
.history .mono {
  color: var(--color-intaglio);
  font-size: 12px;
}
.history .note {
  flex-basis: 100%;
  white-space: pre-line;
  overflow-wrap: anywhere;
}
.small {
  min-height: 28px;
  padding: 0 10px;
  font-size: 12.5px;
}
.close {
  margin-right: auto;
}
</style>
