<script setup lang="ts">
// One booking waiting for the Pitika (spec 2026-11-05-pitika-review-design, "The side panel"):
// the room's photo, the full process bar, what is special about it, the meeting, the food and
// the IT help, then Reject and Approve. Decisions happen in the page's confirm pop-up.
import { Check, FileText, TriangleAlert } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'

import type { BookingDetail } from '../../api/types'
import ApprovedBy from '../../components/ApprovedBy.vue'
import BaseButton from '../../components/base/BaseButton.vue'
import BookingFiles from '../../components/BookingFiles.vue'
import BookingServices from '../../components/BookingServices.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import ProcessBar from '../../components/ProcessBar.vue'
import { SLIP_LABEL, useRequestSlip } from '../../composables/useRequestSlip'
import RoomPhoto from '../../components/RoomPhoto.vue'
import { MEETING_TYPE_LABELS, ROUTE_LABELS, statusLabel } from '../../utils/bookingLabels'
import { buildHistory } from '../../utils/bookingHistory'
import { approvedBy } from '../../utils/approvals'
import { formatDay } from '../../utils/time'

const props = defineProps<{
  booking: BookingDetail
  /** The room's cover photo (full size), or null. */
  photoPath: string | null
  /** "Starts in …" for a booking starting today, else null. */
  startsIn: string | null
  /** A booking already decided: where it is now, and only Close (spec 2026-11-05-pitika-decided). */
  readOnly?: boolean
  /** The subtitle while it waits ("Waiting for Pitika", "Waiting for room owner"). */
  waitingLabel?: string
  /** One note for the reviewer on amber wash (the R4 note, the Pitika's notes), or null. */
  note?: string | null
}>()
const emit = defineEmits<{ close: []; approve: []; reject: [] }>()

// The request slip (ប័ណ្ណស្នើ): only on a decided, confirmed booking.
const slip = useRequestSlip(() => (props.readOnly ? props.booking : null))

const steps = computed(() => buildHistory(props.booking).steps)
const hhmm = (time: string) => time.slice(0, 5)
const info = (key: string) => (props.booking.requester_info[key] as string | null | undefined) || null

const approvals = computed(() => approvedBy(props.booking))

// Tabs (owner pick, 16 Nov 2026): the photo, the steps and the buttons stay; the rest is split.
// A count on Food & IT says there is something to check; Files shows only when there are files.
type Tab = 'details' | 'services' | 'files' | 'approvals'
const tab = ref<Tab>('details')
watch(
  () => props.booking.id,
  () => (tab.value = 'details'),
)
const count = (n: number) => (n ? ` ${n}` : '')
const tabs = computed(() => {
  const services = (props.booking.catering?.packages.length ?? 0) + (props.booking.it?.items.length ?? 0)
  const files = props.booking.attachments?.length ?? 0
  const list: Array<{ id: Tab; label: string }> = [
    { id: 'details', label: 'Details' },
    { id: 'services', label: `Food & IT${count(services)}` },
  ]
  if (files) list.push({ id: 'files', label: `Files${count(files)}` })
  list.push({ id: 'approvals', label: `Approvals${count(approvals.value.length)}` })
  return list
})
/** Every session, in order: a booking can run over several days (up to 20 sessions). */
const sessions = computed(() =>
  [...(props.booking.sessions.length ? props.booking.sessions : [props.booking.first_session])].sort((a, b) =>
    `${a.date} ${a.start_time}`.localeCompare(`${b.date} ${b.start_time}`),
  ),
)
</script>

<template>
  <SidePanel
    :open="true"
    :title="booking.meeting_title"
    :subtitle="readOnly ? statusLabel(booking.display_status) : (waitingLabel ?? 'Waiting for Pitika')"
    :serial="booking.reference_code"
    @close="emit('close')"
  >
    <div class="review-panel">
      <figure class="hero">
        <RoomPhoto class="photo" :path="photoPath" :alt="booking.room.name_en" />
        <figcaption>
          <span class="kh">{{ booking.room.name_kh }}</span>
          <span>{{ booking.room.name_en }} · {{ booking.room.location.name_en }}</span>
        </figcaption>
      </figure>

      <ProcessBar :steps="steps" size="large" />

      <p v-if="startsIn && !readOnly" class="note">
        <TriangleAlert aria-hidden="true" />
        <span>{{ startsIn }}. If nobody decides before it starts, it is rejected by the system.</span>
      </p>
      <p v-if="note" class="note">
        <TriangleAlert aria-hidden="true" />
        <span>{{ note }}</span>
      </p>

      <div class="tabs" role="tablist" aria-label="Booking">
        <button
          v-for="t in tabs"
          :id="`tab-${t.id}`"
          :key="t.id"
          type="button"
          role="tab"
          :aria-selected="tab === t.id"
          :aria-controls="`tabpanel-${t.id}`"
          @click="tab = t.id"
        >
          {{ t.label }}
        </button>
      </div>

      <section v-show="tab === 'details'" id="tabpanel-details" role="tabpanel" aria-labelledby="tab-details">
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
        </dl>

        <!-- Who asks (owner, 16 Nov 2026): ID, name, position and department, as kept when sent. -->
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
      </section>

      <section v-show="tab === 'approvals'" id="tabpanel-approvals" role="tabpanel" aria-labelledby="tab-approvals">
        <h3>Approved by</h3>
        <ApprovedBy :booking="booking" />
      </section>

      <section v-show="tab === 'services'" id="tabpanel-services" role="tabpanel" aria-labelledby="tab-services">
        <BookingServices :booking="booking" viewer="staff" />
      </section>

      <section
        v-if="booking.attachments?.length"
        v-show="tab === 'files'"
        id="tabpanel-files"
        role="tabpanel"
        aria-labelledby="tab-files"
      >
        <h3>Files</h3>
        <BookingFiles :booking-id="booking.id" :files="booking.attachments" />
      </section>
    </div>

    <template #foot>
      <div class="foot">
        <BaseButton variant="quiet" @click="emit('close')">Close</BaseButton>
        <template v-if="slip.hasSlip.value">
          <span class="spacer" />
          <span v-if="slip.error.value" class="slip-error" role="alert">{{ slip.error.value }}</span>
          <BaseButton class="kh" :busy="slip.busy.value" @click="slip.download"><FileText aria-hidden="true" />{{ SLIP_LABEL }}</BaseButton>
        </template>
        <template v-if="!readOnly">
          <span class="spacer" />
          <BaseButton variant="danger" @click="emit('reject')">Reject</BaseButton>
          <BaseButton variant="primary" @click="emit('approve')"><Check aria-hidden="true" />Approve</BaseButton>
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
.note {
  display: flex;
  gap: 8px;
  margin: 12px 0 0;
  padding: 10px 12px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--color-warn) 10%, var(--color-sheet));
  color: var(--color-warn);
  font-size: 12.5px;
  font-weight: 500;
}
.note :deep(svg.lucide) {
  flex: none;
  width: 16px;
  height: 16px;
  margin-top: 1px;
}
h3 {
  margin: 20px 0 4px;
  font-size: 13px;
  font-weight: 600;
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
.sessions .mono {
  font-variant-numeric: tabular-nums;
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
  margin: 0;
  color: var(--color-ink-off);
  font-size: 13px;
}
/* Tabs, like the Admin's booking panel; the bar sticks to the top while the panel scrolls. */
.tabs {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  gap: 4px;
  margin: 16px 0 14px;
  overflow-x: auto;
  border-bottom: 1px solid var(--color-rule);
  background: var(--color-sheet);
}
.tabs button {
  flex: none;
  margin-bottom: -1px;
  padding: 9px 10px;
  border: 0;
  border-bottom: 2px solid transparent;
  background: none;
  color: var(--color-intaglio);
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}
.tabs button[aria-selected='true'] {
  border-bottom-color: var(--color-crimson);
  color: var(--color-ink);
  font-weight: 500;
}
[role='tabpanel'] > h3:first-child {
  margin-top: 0;
}
.sub {
  display: block;
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.foot {
  display: flex;
  flex: 1;
  gap: 8px;
}
.spacer {
  flex: 1;
}
.slip-error {
  align-self: center;
  font-size: 13px;
  color: var(--color-crimson);
}
</style>
