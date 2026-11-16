<script setup lang="ts">
// One of my bookings, in the side panel (owner pick, 13 Nov 2026: "Photo header"): the room photo
// on top with the title on it; the status band; the steps bar; a note saying why it stopped
// (not approved, expired, cancelled); the door pass when confirmed; the sessions with their
// length; then tabs (owner pick, 16 Nov 2026): Details, Food & IT, Files, Approvals. Foot (owner pick, 13 Nov 2026: look C "one main button +
// menu"): Add to calendar as the main button, the slip beside it, and a ⋯ menu with Copy reference
// and Cancel booking. Cancel asks right there (reason optional) and sends the version that was
// read; if someone saved first it says so and offers Reload.
import { Ban, CalendarPlus, Check, CircleX, Clock, Copy, Ellipsis, FileText, X } from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

import { api } from '../../api'
import { getBooking, getBookingIcs, getDoorPass } from '../../api/bookings'
import { ApiError } from '../../api/errors'
import { cancelMyBooking } from '../../api/staff'
import type { AttachmentOut, BookingDetail, DoorPassOut } from '../../api/types'
import ApprovedBy from '../../components/ApprovedBy.vue'
import BookingFiles from '../../components/BookingFiles.vue'
import ProcessBar from '../../components/ProcessBar.vue'
import RoomPhoto from '../../components/RoomPhoto.vue'
import SecretReveal from '../../components/SecretReveal.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import { useLiveRefresh } from '../../composables/useLiveRefresh'
import { SLIP_LABEL, useRequestSlip } from '../../composables/useRequestSlip'
import { useToast } from '../../composables/useToast'
import { approvedBy } from '../../utils/approvals'
import { MEETING_TYPE_LABELS, statusLabel } from '../../utils/bookingLabels'
import { buildHistory, ROLE_LABELS, type HistoryEvent } from '../../utils/bookingHistory'
import { downloadBlob } from '../../utils/download'
import { formatPhnomPenh } from '../../utils/time'
import { dayLabel, lenText } from './rules'

const props = defineProps<{ bookingId: number; cover: string | null }>()
const emit = defineEmits<{ close: []; changed: [BookingDetail] }>()
const toast = useToast()

const booking = ref<BookingDetail | null>(null)
const failed = ref('')
async function load() {
  failed.value = ''
  try {
    booking.value = await getBooking(api, props.bookingId)
  } catch (error) {
    failed.value = error instanceof ApiError ? error.message : 'This booking could not load.'
  }
}
watch(() => props.bookingId, load, { immediate: true })
// Quiet refresh: a decision by Pitika, the owner or IT shows here with no click. Not while a
// cancel is on its way, and a failure keeps what is shown.
useLiveRefresh(async () => {
  if (busy.value || !booking.value) return
  const fresh = await getBooking(api, props.bookingId)
  if (!busy.value && fresh.id === props.bookingId) booking.value = fresh
})

// Files (owner, 16 Nov 2026): the booker adds or removes them until the booking is confirmed.
function setFiles(files: AttachmentOut[]) {
  if (booking.value) booking.value = { ...booking.value, attachments: files }
}

const history = computed(() => (booking.value ? buildHistory(booking.value) : { steps: [], events: [] }))
const open = computed(() => !!booking.value && ['PENDING_PITIKA', 'PENDING_OWNER', 'SETUP_IN_PROGRESS', 'CONFIRMED'].includes(booking.value.display_status))

// The status band under the photo (owner pick, 13 Nov 2026): "Confirmed · the room is yours" on a
// soft tone colour, with the day (or the number of sessions) at the end.
type Tone = 'ok' | 'bad' | 'off' | 'wait'
const tone = computed<Tone>(() => {
  const s = booking.value?.display_status
  return s === 'CONFIRMED' || s === 'COMPLETED' ? 'ok' : s === 'REJECTED' ? 'bad' : s === 'CANCELLED' ? 'off' : 'wait'
})
const TONE_ICON = { ok: Check, bad: X, off: Ban, wait: Clock } as const
const STATUS_LINES: Record<string, string> = {
  CONFIRMED: 'the room is yours',
  COMPLETED: 'the meeting is over',
  SETUP_IN_PROGRESS: 'IT is getting the room ready',
}
const statusLine = computed(() => STATUS_LINES[booking.value?.display_status ?? ''] ?? '')

// Why it stopped: the last rejection, expiry or cancel in the history, with who and when.
const STOPS = ['rejected', 'expired', 'cancelled']
function roleOf(e: HistoryEvent): string | null {
  if (e.role === 'admin') return e.forRole ? `Admin for ${ROLE_LABELS[e.forRole]}` : 'Admin'
  return e.role && e.role !== 'booker' ? ROLE_LABELS[e.role] : null
}
function stopHead(e: HistoryEvent): string {
  if (e.kind === 'rejected') return `Not approved by ${ROLE_LABELS[e.forRole ?? e.role ?? 'pitika']}`
  if (e.kind === 'expired') return 'Expired'
  if (e.role === 'booker') return 'You cancelled it'
  return e.role === 'system' ? 'Cancelled by the system' : 'Cancelled by Admin'
}
const stopNote = computed(() => {
  const e = [...history.value.events].reverse().find((x) => STOPS.includes(x.kind))
  if (!e) return null
  return {
    tone: e.kind === 'cancelled' ? 'off' : 'bad',
    head: stopHead(e),
    text: e.note || (e.kind === 'cancelled' ? 'No reason given.' : ''),
    who: [e.name, roleOf(e), e.at].filter(Boolean).join(' · '),
  }
})

// Sessions: day, time, length; the total when there are several.
const minutes = (t: string) => {
  const [h, m] = t.split(':')
  return Number(h) * 60 + Number(m)
}
const sessions = computed(() =>
  (booking.value?.sessions ?? []).map((s) => ({
    id: s.id,
    day: dayLabel(s.date),
    time: `${s.start_time.slice(0, 5)}–${s.end_time.slice(0, 5)}`,
    len: minutes(s.end_time) - minutes(s.start_time),
  })),
)
const totalLen = computed(() => sessions.value.reduce((sum, s) => sum + s.len, 0))
const invited = computed(() => {
  const n = booking.value?.participant_emails.length ?? 0
  return n ? `${n} by email` : null
})

// Tabs (owner pick, 16 Nov 2026, like To review): the status, the steps and the buttons stay; the
// rest is split into Details, Food & IT, Files and Approvals. Files shows while files can still be
// added, or when there are some. A new booking opens on Details.
type Tab = 'details' | 'services' | 'files' | 'approvals'
const tab = ref<Tab>('details')
watch(
  () => props.bookingId,
  () => (tab.value = 'details'),
)
const count = (n: number) => (n ? ` ${n}` : '')
const showFiles = computed(() => !!booking.value && (booking.value.attachments.length > 0 || booking.value.attachments_open))
const tabs = computed(() => {
  const b = booking.value
  const services = (b?.catering?.packages.length ?? 0) + (b?.it?.items.length ?? 0)
  const list: Array<{ id: Tab; label: string }> = [
    { id: 'details', label: 'Details' },
    { id: 'services', label: `Food & IT${count(services)}` },
  ]
  if (showFiles.value) list.push({ id: 'files', label: `Files${count(b?.attachments.length ?? 0)}` })
  list.push({ id: 'approvals', label: `Approvals${count(b ? approvedBy(b).length : 0)}` })
  return list
})
const hhmm = (time: string) => time.slice(0, 5)

// Food & IT (owner pick, 16 Nov 2026): each item, the booker's note, and the answer. Food is
// checked by Pitika when they approve; IT moves from received to the room being ready.
type Pill = { text: string; tone: 'ok' | 'wait' }
const foodPill = computed<Pill | null>(() => {
  const c = booking.value?.catering
  if (!c) return null
  if (c.decided_at) return { text: 'Approved', tone: 'ok' }
  return open.value ? { text: 'Waiting', tone: 'wait' } : null
})
const itPill = computed<Pill | null>(() => {
  const it = booking.value?.it
  if (!it) return null
  if (it.status === 'READY') return { text: 'Room ready', tone: 'ok' }
  if (!open.value) return null
  if (it.status === 'ASSIGNED') return { text: 'Setting up', tone: 'wait' }
  return { text: it.forwarded_at ? 'Sent to IT' : 'Waiting', tone: 'wait' }
})

const doorPass = ref<DoorPassOut | undefined>(undefined)
async function revealDoorPass(): Promise<string> {
  doorPass.value = await getDoorPass(api, props.bookingId)
  return doorPass.value.passcode
}

const icsError = ref('')
async function addToCalendar() {
  if (!booking.value) return
  icsError.value = ''
  try {
    downloadBlob(await getBookingIcs(api, booking.value.id), `${booking.value.reference_code}.ics`)
  } catch (error) {
    icsError.value = error instanceof ApiError ? error.message : 'The calendar file could not load.'
  }
}

// The request slip (ប័ណ្ណស្នើ): for a confirmed booking, also after the meeting is over.
const slip = useRequestSlip(booking)

// The ⋯ menu: a click outside or Escape closes it (Escape closes only the menu, not the panel).
const menuOpen = ref(false)
const moreBox = ref<HTMLElement | null>(null)
const moreBtn = ref<HTMLButtonElement | null>(null)
function onOutside(event: PointerEvent) {
  if (!moreBox.value?.contains(event.target as Node)) closeMenu()
}
async function openMenu() {
  menuOpen.value = true
  document.addEventListener('pointerdown', onOutside)
  await nextTick()
  moreBox.value?.querySelector<HTMLButtonElement>('[role="menuitem"]')?.focus()
}
function closeMenu(refocus = false) {
  menuOpen.value = false
  document.removeEventListener('pointerdown', onOutside)
  if (refocus) moreBtn.value?.focus()
}
onBeforeUnmount(() => document.removeEventListener('pointerdown', onOutside))
async function copyRef() {
  closeMenu()
  if (!booking.value) return
  try {
    await navigator.clipboard.writeText(booking.value.reference_code)
    toast.show('Reference copied', booking.value.reference_code)
  } catch {
    toast.show('Could not copy', booking.value.reference_code)
  }
}

// Cancel: "Cancel booking" opens the question in the foot (an optional reason, 5 characters or
// more when given); "Yes, cancel booking" sends it, "Keep it" closes the question.
const asking = ref(false)
const reason = ref('')
const reasonBox = ref<HTMLTextAreaElement | null>(null)
const cancelError = ref('')
const stale = ref(false)
const busy = ref(false)
const reasonBad = computed(() => reason.value.trim().length > 0 && reason.value.trim().length < 5)
async function ask() {
  closeMenu()
  asking.value = true
  await nextTick()
  reasonBox.value?.focus()
}
function keep() {
  asking.value = false
  reason.value = ''
  cancelError.value = ''
  stale.value = false
}
async function cancel() {
  if (!booking.value || busy.value) return
  if (reasonBad.value) {
    cancelError.value = 'Write at least 5 characters, or leave the reason empty.'
    return
  }
  busy.value = true
  cancelError.value = ''
  stale.value = false
  try {
    const updated = await cancelMyBooking(api, booking.value.id, booking.value.version, reason.value.trim() || undefined)
    booking.value = updated
    keep()
    emit('changed', updated)
    toast.show('Booking cancelled', updated.reference_code)
  } catch (error) {
    stale.value = error instanceof ApiError && error.code === 'STALE_VERSION'
    cancelError.value = stale.value ? 'This item changed. Reload it.' : error instanceof ApiError ? error.message : 'The booking could not be cancelled.'
  } finally {
    busy.value = false
  }
}
async function reload() {
  await load()
  stale.value = false
  cancelError.value = ''
  if (booking.value) emit('changed', booking.value)
}
</script>

<template>
  <SidePanel
    :open="true"
    :title="booking?.meeting_title ?? 'Booking'"
    :subtitle="booking ? `${booking.room.name_en} · ${booking.room.location.name_en}` : undefined"
    :serial="booking?.reference_code"
    @close="emit('close')"
  >
    <template v-if="cover && booking" #cover><RoomPhoto :path="cover" :alt="booking.room.name_en" /></template>
    <p v-if="failed" class="msg" role="alert">{{ failed }}</p>
    <div v-else-if="booking" class="bd">
      <div class="band" :class="tone">
        <span class="dot"><component :is="TONE_ICON[tone]" :size="13" :stroke-width="2.5" aria-hidden="true" /></span>
        <span class="say-status"
          >{{ statusLabel(booking.display_status) }}<template v-if="statusLine"> · {{ statusLine }}</template></span
        >
        <small v-if="sessions.length">{{ sessions.length > 1 ? `${sessions.length} sessions` : sessions[0]!.day }}</small>
      </div>
      <ProcessBar :steps="history.steps" size="large" />

      <div v-if="stopNote" class="callout" :class="stopNote.tone">
        <span class="h">{{ stopNote.head }}</span>
        <p v-if="stopNote.text" class="say">{{ stopNote.text }}</p>
        <span v-if="stopNote.who" class="who">{{ stopNote.who }}</span>
      </div>

      <div v-if="booking.status === 'CONFIRMED' && booking.display_status !== 'COMPLETED'" class="block">
        <div class="lbl"><span>Door pass</span></div>
        <SecretReveal label="door pass" :reveal="revealDoorPass" @hide="doorPass = undefined">
          <template #extra><span v-if="doorPass?.expired" class="expired">Expired</span></template>
        </SecretReveal>
      </div>

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

      <section v-show="tab === 'details'" id="tabpanel-details" class="pane" role="tabpanel" aria-labelledby="tab-details">
        <div class="block">
          <div class="lbl">
            <span>{{ sessions.length === 1 ? 'Time' : `${sessions.length} sessions` }}</span>
            <span v-if="sessions.length > 1">{{ lenText(totalLen) }} in all</span>
          </div>
          <table class="sessions">
            <tbody>
              <tr v-for="s in sessions" :key="s.id">
                <td>{{ s.day }}</td>
                <td class="mono">{{ s.time }}</td>
                <td class="len">{{ lenText(s.len) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <dl class="facts">
          <div>
            <dt>Meeting</dt>
            <dd>{{ MEETING_TYPE_LABELS[booking.meeting_type] ?? booking.meeting_type }} · {{ booking.attendees }} people</dd>
          </div>
          <div>
            <dt>Invited</dt>
            <dd :class="{ none: !invited }">{{ invited ?? 'No one' }}</dd>
          </div>
          <div v-if="booking.private_justification" class="full">
            <dt>Why this room</dt>
            <dd>{{ booking.private_justification }}</dd>
          </div>
          <div v-if="booking.meeting_purpose" class="full">
            <dt>Notes</dt>
            <dd>{{ booking.meeting_purpose }}</dd>
          </div>
          <div class="full">
            <dt>Sent</dt>
            <dd class="mono">{{ formatPhnomPenh(booking.created_at) }}</dd>
          </div>
        </dl>
      </section>

      <section v-show="tab === 'services'" id="tabpanel-services" class="pane" role="tabpanel" aria-labelledby="tab-services">
        <div v-if="booking.catering" class="svc-card" data-kind="food">
          <div class="svc-h">
            <h3>Food &amp; drinks</h3>
            <span v-if="foodPill" class="pill" :class="foodPill.tone">{{ foodPill.text }}</span>
          </div>
          <ul class="svc-items">
            <li v-for="p in booking.catering.packages" :key="String(p.id)"><span>{{ p.name }}</span> <span class="q mono">× {{ booking.catering.servings }}</span></li>
          </ul>
          <dl class="svc-rows">
            <div>
              <dt>Bring it at</dt>
              <dd v-if="sessions.length > 1">The start of every session ({{ sessions.length }} times)</dd>
              <dd v-else>{{ dayLabel(booking.catering.delivery_date) }} · <span class="mono">{{ hhmm(booking.catering.delivery_time) }}</span></dd>
            </div>
            <div v-if="booking.catering.remarks">
              <dt>Your note</dt>
              <dd class="quote">“{{ booking.catering.remarks }}”</dd>
            </div>
            <div v-if="booking.catering.decided_by && booking.catering.decided_at">
              <dt>Checked by</dt>
              <dd>
                {{ booking.catering.decided_by.name_en }} · <span class="mono">{{ formatPhnomPenh(booking.catering.decided_at) }}</span>
                <span v-if="booking.catering.approver_notes" class="sub quote">“{{ booking.catering.approver_notes }}”</span>
              </dd>
            </div>
          </dl>
        </div>
        <p v-else class="none-line">No food ordered.</p>

        <div v-if="booking.it" class="svc-card" data-kind="it">
          <div class="svc-h">
            <h3>IT help</h3>
            <span v-if="itPill" class="pill" :class="itPill.tone">{{ itPill.text }}</span>
          </div>
          <ul class="svc-items">
            <li v-for="x in booking.it.items" :key="String(x.id)">{{ x.name }}</li>
          </ul>
          <dl class="svc-rows">
            <div v-if="booking.it.special_requirements">
              <dt>Your note</dt>
              <dd class="quote">“{{ booking.it.special_requirements }}”</dd>
            </div>
            <div v-if="booking.it.staff.length">
              <dt>IT staff</dt>
              <dd>{{ booking.it.staff.map((s) => s.name_en).join(', ') }}</dd>
            </div>
            <div v-if="booking.it.ready_at">
              <dt>Ready at</dt>
              <dd>
                <span class="mono">{{ formatPhnomPenh(booking.it.ready_at) }}</span>
                <span v-if="booking.it.technician_notes" class="sub quote">“{{ booking.it.technician_notes }}”</span>
              </dd>
            </div>
            <div v-else-if="open">
              <dt>Setup starts</dt>
              <dd>{{ dayLabel(booking.it.setup_date) }} · <span class="mono">{{ hhmm(booking.it.setup_time) }}</span></dd>
            </div>
          </dl>
        </div>
        <p v-else class="none-line">No IT help asked.</p>
      </section>

      <section v-if="showFiles" v-show="tab === 'files'" id="tabpanel-files" class="pane" role="tabpanel" aria-labelledby="tab-files">
        <BookingFiles :booking-id="booking.id" :files="booking.attachments" :editable="booking.attachments_open" @update="setFiles" @locked="load" />
      </section>

      <section v-show="tab === 'approvals'" id="tabpanel-approvals" class="pane" role="tabpanel" aria-labelledby="tab-approvals">
        <ApprovedBy :booking="booking" />
      </section>

      <p v-if="icsError" class="msg" role="alert">{{ icsError }}</p>
      <p v-if="slip.error.value" class="msg" role="alert">{{ slip.error.value }}</p>
    </div>

    <template v-if="booking && (open || slip.hasSlip.value)" #foot>
      <div v-if="asking" class="foot">
        <p class="ask">Cancel this booking? <span>This cannot be undone.</span></p>
        <textarea ref="reasonBox" v-model="reason" class="reason" rows="2" placeholder="Reason (optional)" aria-label="Reason to cancel (optional)" />
        <p v-if="cancelError" class="msg" role="alert">{{ cancelError }}<button v-if="stale" type="button" class="reload" @click="reload">Reload</button></p>
        <div class="row">
          <button type="button" class="cal" :disabled="busy" @click="keep">Keep it</button>
          <button type="button" class="danger" :disabled="busy" @click="cancel">Yes, cancel booking</button>
        </div>
      </div>
      <div v-else class="foot">
        <div class="bar">
          <button v-if="open" type="button" class="main" @click="addToCalendar"><CalendarPlus :size="16" aria-hidden="true" />Add to calendar</button>
          <button v-if="slip.hasSlip.value" type="button" class="kh" :class="open ? 'cal' : 'main'" :disabled="slip.busy.value" @click="slip.download">
            <FileText :size="16" aria-hidden="true" />{{ SLIP_LABEL }}
          </button>
          <div ref="moreBox" class="more" @keydown.esc.prevent="closeMenu(true)">
            <button
              ref="moreBtn"
              type="button"
              class="cal sq"
              aria-label="More actions"
              aria-haspopup="menu"
              :aria-expanded="menuOpen"
              @click="menuOpen ? closeMenu() : openMenu()"
            >
              <Ellipsis :size="18" aria-hidden="true" />
            </button>
            <Transition name="menu">
              <div v-if="menuOpen" class="menu" role="menu">
                <button type="button" role="menuitem" @click="copyRef"><Copy :size="16" aria-hidden="true" />Copy reference</button>
                <template v-if="open">
                  <hr />
                  <button type="button" role="menuitem" class="red" @click="ask"><CircleX :size="16" aria-hidden="true" />Cancel booking</button>
                </template>
              </div>
            </Transition>
          </div>
        </div>
      </div>
    </template>
  </SidePanel>
</template>

<style scoped>
.bd {
  display: grid;
  gap: 18px;
}
/* Full width right under the photo (it cancels the body's padding): a soft wash of the tone,
   a filled dot with the icon, the status, and the day at the end. */
.band {
  --tone: var(--color-ok);
  display: flex;
  align-items: center;
  gap: 10px;
  margin: -16px -20px 0;
  padding: 12px 20px;
  background: color-mix(in srgb, var(--tone) 11%, var(--color-sheet));
  color: var(--tone);
  font-size: 13.5px;
  font-weight: 500;
}
.band.bad {
  --tone: var(--color-crimson);
}
.band.wait {
  --tone: var(--color-warn);
}
.band.off {
  --tone: var(--color-intaglio);
}
.band .dot {
  display: grid;
  flex: none;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--tone);
  color: var(--color-sheet);
}
.band .say-status {
  min-width: 0;
}
.band small {
  flex: none;
  margin-left: auto;
  font-size: 12px;
  font-weight: 400;
  color: var(--color-intaglio);
}
.callout {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 12px;
  background: var(--color-paper);
}
.callout.bad {
  background: var(--color-crimson-wash);
}
.callout .h {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--color-intaglio);
}
.callout.bad .h {
  color: var(--color-crimson);
}
.say {
  margin: 0;
  font-size: 14.5px;
  line-height: 1.55;
  overflow-wrap: anywhere;
}
.who {
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.block {
  display: grid;
  gap: 6px;
}
.lbl {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
  color: var(--color-intaglio);
}
.sessions {
  width: 100%;
  border-collapse: collapse;
  font-size: 13.5px;
}
.sessions td {
  padding: 7px 0;
  border-bottom: 1px solid var(--color-rule);
  white-space: nowrap;
}
.sessions tr:last-child td {
  border-bottom: 0;
}
.sessions .len {
  text-align: right;
  font-size: 12.5px;
  color: var(--color-ink-off);
}
.facts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px 16px;
  margin: 0;
}
.facts > div {
  min-width: 0;
}
.facts .full {
  grid-column: 1 / -1;
}
dt {
  font-size: 12px;
  color: var(--color-intaglio);
}
dd {
  margin: 2px 0 0;
  font-size: 14px;
  overflow-wrap: anywhere;
}
dd.none {
  color: var(--color-ink-off);
}
/* Tabs, like To review; the bar sticks to the top while the panel scrolls. */
.tabs {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  gap: 4px;
  margin: 0 -20px -4px;
  padding: 0 20px;
  overflow-x: auto;
  border-bottom: 1px solid var(--color-rule);
  background: var(--color-sheet);
}
.tabs button {
  flex: none;
  margin-bottom: -1px;
  padding: 10px 10px;
  border: 0;
  border-bottom: 2px solid transparent;
  background: none;
  color: var(--color-intaglio);
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}
.tabs button[aria-selected='true'] {
  border-bottom-color: var(--color-ink);
  color: var(--color-ink);
  font-weight: 500;
}
.tabs button:focus-visible {
  outline: 2px solid var(--color-ink);
  outline-offset: -2px;
}
.pane {
  display: grid;
  gap: 18px;
}
/* Food & IT: one card each, the items, then the notes and the answer. */
.svc-card {
  display: grid;
  gap: 8px;
  padding: 12px 14px;
  border: 1px solid var(--color-rule);
  border-radius: 12px;
}
.svc-h {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.svc-h h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}
.pill {
  flex: none;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 500;
  white-space: nowrap;
}
.pill.ok {
  background: color-mix(in srgb, var(--color-ok) 12%, var(--color-sheet));
  color: var(--color-ok);
}
.pill.wait {
  background: color-mix(in srgb, var(--color-warn) 12%, var(--color-sheet));
  color: var(--color-warn);
}
.svc-items {
  margin: 0;
  padding: 0;
  list-style: none;
}
.svc-items li {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 0;
  font-size: 13.5px;
  overflow-wrap: anywhere;
}
.svc-items li + li {
  border-top: 1px solid var(--color-rule);
}
.svc-items .q {
  flex: none;
  font-size: 12.5px;
  color: var(--color-ink-off);
}
.svc-rows {
  display: grid;
  margin: 0;
}
.svc-rows > div {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  gap: 10px;
  padding: 7px 0;
  border-top: 1px solid var(--color-rule);
}
.svc-rows dd {
  margin: 0;
  font-size: 13.5px;
}
.quote {
  color: var(--color-intaglio);
}
.sub {
  display: block;
  margin-top: 2px;
  font-size: 12.5px;
}
.none-line {
  margin: 0;
  font-size: 13px;
  color: var(--color-ink-off);
}
@media (max-width: 420px) {
  .svc-rows > div {
    grid-template-columns: 1fr;
    gap: 2px;
  }
}
.expired {
  color: var(--color-crimson);
  font-size: 12.5px;
}
.cal,
.main,
.danger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 42px;
  padding: 0 16px;
  border: 0;
  border-radius: 12px;
  font: inherit;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition:
    background-color 160ms ease,
    color 160ms ease,
    transform 160ms var(--ease-out-quint);
}
.cal {
  background: var(--color-field-disabled);
  color: var(--color-ink);
}
/* One main button (dark ink) that takes the free width, the slip beside it, then ⋯. */
.main {
  flex: 1;
  min-width: 0;
  background: var(--color-ink);
  color: var(--color-sheet);
  white-space: nowrap;
}
.danger {
  margin-left: auto;
  background: var(--color-crimson-fill);
  color: #fff;
}
.bar {
  display: flex;
  gap: 8px;
}
.bar .cal {
  white-space: nowrap;
}
.more {
  position: relative;
  flex: none;
}
.sq {
  width: 42px;
  padding: 0;
}
/* The menu opens above the ⋯ button, from its corner. */
.menu {
  position: absolute;
  right: 0;
  bottom: calc(100% + 8px);
  z-index: 2;
  display: grid;
  min-width: 210px;
  padding: 6px;
  border: 1px solid var(--color-rule);
  border-radius: 12px;
  background: var(--color-sheet);
  box-shadow: var(--shadow-toast);
  transform-origin: bottom right;
}
.menu button {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 38px;
  padding: 0 10px;
  border: 0;
  border-radius: 8px;
  background: none;
  color: var(--color-ink);
  font: inherit;
  font-size: 13.5px;
  text-align: left;
  cursor: pointer;
}
.menu button:focus-visible {
  outline: 2px solid var(--color-ink);
  outline-offset: -2px;
}
.menu .red {
  color: var(--color-crimson);
}
.menu hr {
  margin: 4px 2px;
  border: 0;
  border-top: 1px solid var(--color-rule);
}
.menu-enter-active,
.menu-leave-active {
  transition:
    opacity 150ms ease,
    transform 150ms var(--ease-out-quint);
}
.menu-enter-from,
.menu-leave-to {
  opacity: 0;
  transform: scale(0.96);
}
.cal:disabled,
.main:disabled,
.danger:disabled {
  opacity: 0.6;
  cursor: default;
}
.foot {
  display: grid;
  flex: 1;
  gap: 10px;
}
.ask {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
}
.ask span {
  font-weight: 400;
  color: var(--color-intaglio);
}
.row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.reason {
  box-sizing: border-box;
  min-height: 64px;
  max-height: 140px;
  padding: 11px 14px;
  field-sizing: content;
  line-height: 20px;
  border: 0;
  border-radius: 12px;
  outline: none;
  background: var(--color-field-disabled);
  color: var(--color-ink);
  font: inherit;
  font-size: 14px;
  resize: none;
}
.reason:focus {
  background: var(--color-sheet);
  box-shadow: 0 0 0 1.5px var(--color-ink);
}
.cal:active:not(:disabled),
.main:active:not(:disabled),
.danger:active:not(:disabled) {
  transform: scale(0.97);
}
.msg {
  margin: 0;
  color: var(--color-crimson);
  font-size: 13px;
}
.reload {
  margin-left: 8px;
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  font-weight: 600;
  text-decoration: underline;
  cursor: pointer;
}
@media (hover: hover) and (pointer: fine) {
  .cal:not(:disabled):hover {
    background: var(--color-rule);
  }
  .main:not(:disabled):hover {
    background: color-mix(in srgb, var(--color-ink) 86%, var(--color-sheet));
  }
  .menu button:hover {
    background: var(--color-row-hover);
  }
  .menu .red:hover {
    background: var(--color-crimson-wash);
  }
  .danger:not(:disabled):hover {
    background: var(--color-crimson-deep);
  }
}
@media (prefers-reduced-motion: reduce) {
  .cal,
  .main,
  .danger,
  .menu-enter-active,
  .menu-leave-active {
    transition: none;
  }
}
</style>
