<script setup lang="ts">
// One booking (DSH-B02 to B04): details, sessions, services and history. There is no form; the
// Admin's only changes are the actions the API allows (cancel, and approve or reject as backup
// reviewer). The door pass shows only when the Admin asks, and only for a confirmed booking.
import { CalendarArrowDown, CircleAlert } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'

import { api } from '../../api'
import { adminApprove, adminCancel, adminReject, getAdminActions, getBooking, getBookingIcs, getDoorPass } from '../../api/bookings'
import { ApiError } from '../../api/errors'
import type { AdminActionsOut, BookingDetail, DoorPassOut } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import SecretReveal from '../../components/SecretReveal.vue'
import BookingActionDialog, { type BookingAction } from './BookingActionDialog.vue'
import BookingHistory from './BookingHistory.vue'
import { useToast } from '../../composables/useToast'
import { MEETING_TYPE_LABELS, ROUTE_LABELS, statusLabel } from '../../utils/bookingLabels'
import { formatDay, formatPhnomPenh } from '../../utils/time'

const props = defineProps<{ booking: BookingDetail }>()
const emit = defineEmits<{ close: []; changed: [booking: BookingDetail] }>()

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

const IT_STATUS: Record<string, string> = { RECEIVED: 'Received', ASSIGNED: 'Staff assigned', READY: 'Ready' }

// The door pass, fetched only when the eye is pressed; an expired one gets a small tag. Its end
// time is on the Sessions tab ("Ends …"), so the row stays one line.
const doorPass = ref<DoorPassOut | undefined>(undefined)
async function revealDoorPass(): Promise<string> {
  doorPass.value = await getDoorPass(api, props.booking.id)
  return doorPass.value.passcode
}

// The Admin's actions (B-33, B-34): the buttons follow what the API allows now, and each
// opens a confirm pop-up (BookingActionDialog) with an optional reason (D-35) before anything
// is sent.
type Action = BookingAction
const actions = ref<AdminActionsOut | null>(null)
const step = ref<Action | null>(null)
const stepText = ref('')
const stepBusy = ref(false)
const stepError = ref('')
const fieldError = ref('')
const toast = useToast()

async function loadActions() {
  try {
    actions.value = await getAdminActions(api, props.booking.id)
  } catch {
    actions.value = null // no buttons; the booking still shows
  }
}
onMounted(loadActions)

const STEP_WORDS: Record<Action, { title: string; confirm: string; label: string; max: number; done: string }> = {
  cancel: { title: 'Cancel this booking?', confirm: 'Cancel booking', label: 'Reason (optional)', max: 500, done: 'cancelled' },
  approve: { title: 'Approve this booking?', confirm: 'Approve', label: 'Notes (optional)', max: 1000, done: 'approved' },
  reject: { title: 'Reject this booking?', confirm: 'Reject', label: 'Reason (optional)', max: 1000, done: 'rejected' },
}
const stepWords = computed(() => (step.value ? STEP_WORDS[step.value] : null))
const actingFor = computed(() =>
  actions.value?.stage === 'PITIKA' ? 'You act for Pitika.' : actions.value?.stage === 'OWNER' ? 'You act for the room owner.' : '',
)
const stepEffect = computed(() => {
  if (step.value === 'cancel') return 'The room is free again. The booker sees the reason when they open the booking.'
  if (step.value === 'reject') return 'The booking stops and the room is free again.'
  if (actions.value?.stage === 'PITIKA' && props.booking.route === 'R2') return 'It goes to the room owner next.'
  return props.booking.has_it ? 'It goes to IT setup next.' : 'It is confirmed, with a door pass.'
})

// The first session's times, and how many more there are: "14:00–15:30 +2 more".
const stepTimes = computed(() => {
  const first = props.booking.first_session
  const more = props.booking.session_count - 1
  return `${hhmm(first.start_time)}–${hhmm(first.end_time)}${more > 0 ? ` +${more} more` : ''}`
})

function openStep(action: Action) {
  step.value = action
  stepText.value = ''
  stepError.value = ''
  fieldError.value = ''
}

async function confirmStep() {
  if (!step.value) return
  const action = step.value
  const text = stepText.value.trim() || null
  const version = props.booking.version
  stepBusy.value = true
  stepError.value = ''
  fieldError.value = ''
  try {
    const updated =
      action === 'cancel'
        ? await adminCancel(api, props.booking.id, { reason: text, version })
        : action === 'approve'
          ? await adminApprove(api, props.booking.id, { notes: text, version })
          : await adminReject(api, props.booking.id, { reason: text, version })
    toast.show(`${updated.reference_code} ${STEP_WORDS[action].done}`, statusLabel(updated.display_status))
    step.value = null
    emit('changed', updated)
    await loadActions()
  } catch (err) {
    if (err instanceof ApiError) {
      fieldError.value = err.fields.reason ?? err.fields.notes ?? ''
      stepError.value = fieldError.value ? '' : err.message
      // Someone else acted, or the booking moved on: show the booking as it is now, so a retry
      // sends its new version, and offer only what is still allowed.
      if (err.status === 403 || err.status === 409) {
        try {
          emit('changed', await getBooking(api, props.booking.id))
        } catch {
          // the message already says to reload
        }
        await loadActions()
      }
    } else {
      stepError.value = 'Something went wrong.'
    }
  } finally {
    stepBusy.value = false
  }
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
        <div v-if="booking.status === 'CONFIRMED'" class="secret-row">
          <dt>Door pass</dt>
          <dd class="door-pass">
            <SecretReveal label="door pass" :reveal="revealDoorPass" @hide="doorPass = undefined">
              <template #extra>
                <span v-if="doorPass?.expired" class="expired">Expired</span>
              </template>
            </SecretReveal>
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
      <BookingHistory :booking="booking" />
    </section>

    <div v-if="icsError" class="summary" role="alert">
      <CircleAlert aria-hidden="true" />
      <b>{{ icsError }}</b>
    </div>

    <template #foot>
      <!-- Two groups that share one row when they fit; on a narrow panel the decisions move
           to their own row above, so no button is ever pushed out of the panel. -->
      <div class="booking-foot">
        <div class="foot-group">
          <BaseButton variant="quiet" @click="emit('close')">Close</BaseButton>
          <BaseButton :busy="icsBusy" @click="downloadIcs">
            <CalendarArrowDown v-if="!icsBusy" aria-hidden="true" />
            Calendar file
          </BaseButton>
        </div>
        <div v-if="actions && (actions.cancel || actions.reject || actions.approve)" class="foot-group decide">
          <BaseButton v-if="actions.cancel" variant="quiet" class="danger" @click="openStep('cancel')">Cancel booking</BaseButton>
          <BaseButton v-if="actions.reject" @click="openStep('reject')">Reject</BaseButton>
          <BaseButton v-if="actions.approve" variant="primary" @click="openStep('approve')">Approve</BaseButton>
        </div>
      </div>
    </template>
  </SidePanel>

  <BookingActionDialog
    v-if="step && stepWords"
    v-model="stepText"
    :action="step"
    :title="stepWords.title"
    :confirm-label="stepWords.confirm"
    :field-label="stepWords.label"
    :max="stepWords.max"
    :meeting="booking.meeting_title"
    :reference="booking.reference_code"
    :day="formatDay(booking.first_session.date)"
    :times="stepTimes"
    :acting-for="step !== 'cancel' ? actingFor : ''"
    :effect="stepEffect"
    :busy="stepBusy"
    :allowed="!!actions?.[step]"
    :error="stepError"
    :field-error="fieldError"
    @back="step = null"
    @confirm="confirmStep"
  />
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
.details > .secret-row {
  align-items: center;
  padding: 4px 0;
}
.expired {
  flex: none;
  padding: 0 5px;
  line-height: 18px;
  border: 1px solid var(--color-crimson);
  border-radius: 6px;
  color: var(--color-crimson);
  font-size: 11px;
  font-weight: 500;
}
.sessions {
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
.booking-foot {
  display: flex;
  flex: 1;
  flex-wrap: wrap-reverse;
  gap: 8px;
  min-width: 0;
}
.foot-group {
  display: flex;
  gap: 8px;
}
.foot-group.decide {
  margin-left: auto;
}
.danger {
  color: var(--color-crimson);
}
</style>
