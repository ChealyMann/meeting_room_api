<script setup lang="ts">
// One of my bookings, in the side panel: photo, status and its steps, times, people, food, IT,
// notes; the door pass when confirmed; Add to calendar; Cancel booking (asks first, sends the
// version that was read; if someone saved first it says so and offers Reload).
import { CalendarPlus } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'

import { api } from '../../api'
import { getBooking, getBookingIcs, getDoorPass } from '../../api/bookings'
import { ApiError } from '../../api/errors'
import { cancelMyBooking } from '../../api/staff'
import type { BookingDetail, DoorPassOut } from '../../api/types'
import ProcessBar from '../../components/ProcessBar.vue'
import RoomPhoto from '../../components/RoomPhoto.vue'
import SecretReveal from '../../components/SecretReveal.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import { useConfirm } from '../../composables/useConfirm'
import { useToast } from '../../composables/useToast'
import { MEETING_TYPE_LABELS, statusLabel } from '../../utils/bookingLabels'
import { buildHistory } from '../../utils/bookingHistory'
import { dayLabel } from './rules'

const props = defineProps<{ bookingId: number; cover: string | null }>()
const emit = defineEmits<{ close: []; changed: [BookingDetail] }>()
const { confirm } = useConfirm()
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

const steps = computed(() => (booking.value ? buildHistory(booking.value).steps : []))
const names = (list: Array<Record<string, unknown>>) => list.map((x) => String(x.name)).join(', ')
const open = computed(() => !!booking.value && ['PENDING_PITIKA', 'PENDING_OWNER', 'SETUP_IN_PROGRESS', 'CONFIRMED'].includes(booking.value.display_status))

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
    const url = URL.createObjectURL(await getBookingIcs(api, booking.value.id))
    const link = document.createElement('a')
    link.href = url
    link.download = `${booking.value.reference_code}.ics`
    document.body.append(link)
    link.click()
    link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 0)
  } catch (error) {
    icsError.value = error instanceof ApiError ? error.message : 'The calendar file could not load.'
  }
}

// Cancel: an optional reason (5 characters or more when given), then the confirm question.
const reason = ref('')
const cancelError = ref('')
const stale = ref(false)
const busy = ref(false)
const reasonBad = computed(() => reason.value.trim().length > 0 && reason.value.trim().length < 5)
async function cancel() {
  if (!booking.value || busy.value) return
  if (reasonBad.value) {
    cancelError.value = 'Write at least 5 characters, or leave the reason empty.'
    return
  }
  const yes = await confirm({
    title: 'Cancel this booking?',
    text: `${booking.value.meeting_title} in ${booking.value.room.name_en}. This cannot be undone.`,
    confirmLabel: 'Cancel booking',
    cancelLabel: 'Keep it',
    icon: 'warning',
  })
  if (!yes) return
  busy.value = true
  cancelError.value = ''
  stale.value = false
  try {
    const updated = await cancelMyBooking(api, booking.value.id, booking.value.version, reason.value.trim() || undefined)
    booking.value = updated
    reason.value = ''
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
    :subtitle="booking ? statusLabel(booking.display_status) : undefined"
    :serial="booking?.reference_code"
    @close="emit('close')"
  >
    <p v-if="failed" class="msg" role="alert">{{ failed }}</p>
    <div v-else-if="booking" class="bd">
      <div class="ph"><RoomPhoto :path="cover" :alt="booking.room.name_en" /></div>
      <ProcessBar :steps="steps" size="large" />

      <dl>
        <div>
          <dt>{{ booking.sessions.length === 1 ? 'Time' : `${booking.sessions.length} sessions` }}</dt>
          <dd>
            <span v-for="s in booking.sessions" :key="s.id" class="line"
              >{{ dayLabel(s.date) }} · <span class="mono">{{ s.start_time.slice(0, 5) }}–{{ s.end_time.slice(0, 5) }}</span></span
            >
          </dd>
        </div>
        <div><dt>Room</dt><dd>{{ booking.room.name_en }}</dd></div>
        <div><dt>Meeting</dt><dd>{{ MEETING_TYPE_LABELS[booking.meeting_type] ?? booking.meeting_type }} · {{ booking.attendees }} people</dd></div>
        <div><dt>Food &amp; drinks</dt><dd>{{ booking.catering ? names(booking.catering.packages) : 'None' }}</dd></div>
        <div><dt>IT help</dt><dd>{{ booking.it ? names(booking.it.items) : 'None' }}</dd></div>
        <div v-if="booking.private_justification"><dt>Why this room</dt><dd>{{ booking.private_justification }}</dd></div>
        <div v-if="booking.meeting_purpose"><dt>Notes</dt><dd>{{ booking.meeting_purpose }}</dd></div>
        <div v-if="booking.rejection"><dt>Not approved</dt><dd>{{ booking.rejection.reason }}</dd></div>
        <div v-if="booking.cancel_reason"><dt>Cancel reason</dt><dd>{{ booking.cancel_reason }}</dd></div>
        <div v-if="booking.status === 'CONFIRMED' && booking.display_status !== 'COMPLETED'" class="pass">
          <dt>Door pass</dt>
          <dd>
            <SecretReveal label="door pass" :reveal="revealDoorPass" @hide="doorPass = undefined">
              <template #extra><span v-if="doorPass?.expired" class="expired">Expired</span></template>
            </SecretReveal>
          </dd>
        </div>
      </dl>

      <p v-if="icsError" class="msg" role="alert">{{ icsError }}</p>
    </div>

    <!-- The actions stay in the panel's foot, like every dashboard panel; the reason sits right
         above the button it belongs to. -->
    <template v-if="booking && open" #foot>
      <div class="foot">
        <textarea v-model="reason" class="reason" rows="1" placeholder="Reason to cancel (optional)" aria-label="Reason to cancel (optional)" />
        <p v-if="cancelError" class="msg" role="alert">
          {{ cancelError }}<button v-if="stale" type="button" class="reload" @click="reload">Reload</button>
        </p>
        <div class="row">
          <button type="button" class="danger" :disabled="busy" @click="cancel">Cancel booking</button>
          <button type="button" class="cal" @click="addToCalendar"><CalendarPlus :size="16" aria-hidden="true" />Add to calendar</button>
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
.ph {
  height: 160px;
  overflow: hidden;
  border-radius: 16px;
}
.ph :deep(.room-photo),
.ph :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
dl {
  display: grid;
  gap: 12px;
  margin: 0;
}
dl > div {
  display: grid;
  grid-template-columns: 130px 1fr;
  gap: 12px;
  font-size: 14px;
}
dt {
  color: var(--color-ink-off);
}
dd {
  display: grid;
  gap: 4px;
  margin: 0;
}
.expired {
  color: var(--color-crimson);
  font-size: 12.5px;
}
.cal,
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
  transition: background-color 160ms ease, transform 160ms var(--ease-out-quint);
}
.cal {
  background: var(--color-field-disabled);
  color: var(--color-ink);
}
/* Cancel sits apart at the start of the foot; Add to calendar at the end. */
.danger {
  margin-right: auto;
}
.foot {
  display: grid;
  flex: 1;
  gap: 10px;
}
.row {
  display: flex;
  gap: 8px;
}
.reason {
  box-sizing: border-box;
  min-height: 42px;
  max-height: 120px;
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
.danger {
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
}
.danger:disabled {
  opacity: 0.6;
  cursor: default;
}
.cal:active,
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
  .cal:hover {
    background: var(--color-rule);
  }
  .danger:not(:disabled):hover {
    background: var(--color-crimson-fill);
    color: #fff;
  }
}
@media (prefers-reduced-motion: reduce) {
  .cal,
  .danger {
    transition: none;
  }
}
</style>
