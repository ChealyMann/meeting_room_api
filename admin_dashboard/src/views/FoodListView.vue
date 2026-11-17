<script setup lang="ts">
// The day's food list (GET /pitika/catering, spec B-12): every food order of bookings in IT setup
// or confirmed whose first session is on that day. The Admin sees every province; nothing is
// changed here. The day lives in the address (?date=2026-11-04); none means today in Phnom Penh.
// Look A (owner pick, 17 Nov 2026; the "To prepare" card was taken out the same day): the table
// says where to bring the food (room, floor, building, office), the food with the booker's and the Pitika's notes under it, then the meeting. Today,
// past rows are faded, the next time is marked, and a red Now line sits between them. Food has no
// numbers (owner decision, 17 Nov 2026); "Confirmed" is not repeated, only "IT setting up".
// The meeting opens the booking's drawer on this page (?booking=7, owner, 17 Nov 2026), the same
// panel as Bookings; the Admin gets their actions in it.
import { ChevronLeft, ChevronRight, CircleAlert } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '../api'
import { getBooking, getFoodList } from '../api/bookings'
import { ApiError } from '../api/errors'
import type { BookingDetail, CateringOrderItem } from '../api/types'
import BaseButton from '../components/base/BaseButton.vue'
import DatePicker from '../components/base/DatePicker.vue'
import EmptyState from '../components/list/EmptyState.vue'
import TableSkeleton from '../components/list/TableSkeleton.vue'
import OfflineNote from '../components/list/OfflineNote.vue'
import RefreshButton from '../components/list/RefreshButton.vue'
import { usePanelParam } from '../composables/usePanelParam'
import { usePanelRecord } from '../composables/usePanelRecord'
import { usePhnomPenhToday } from '../composables/usePhnomPenhToday'
import { useLiveRefresh } from '../composables/useLiveRefresh'
import { useSessionStore } from '../stores/session'
import { foodDay } from '../utils/foodDay'
import BookingPanel from './bookings/BookingPanel.vue'
import { addDays, formatDay, phnomPenhClock } from '../utils/time'

const route = useRoute()
const router = useRouter()

const DAY = /^\d{4}-\d{2}-\d{2}$/
// Kept current: a list left open past midnight (with no ?date) moves to the new day.
const today = usePhnomPenhToday()
const day = computed(() => {
  const value = route.query.date
  return typeof value === 'string' && DAY.test(value) ? value : today.value
})
function go(next: string) {
  void router.push({ query: next === today.value ? {} : { date: next } })
}

// The time now in Phnom Penh ("HH:MM"), for the Now line: checked every 20 seconds.
const clock = ref(phnomPenhClock(new Date()))
let tick: ReturnType<typeof setInterval> | undefined
onMounted(() => (tick = setInterval(() => (clock.value = phnomPenhClock(new Date())), 20_000)))
onBeforeUnmount(() => clearInterval(tick))

const items = ref<CateringOrderItem[] | null>(null)
const loading = ref(false)
const error = ref('')
let latest = 0

/** `quiet` (only a real `true`): the live refresh — no spinner, a failure keeps what is shown. */
async function load(quietRefresh?: unknown) {
  const quiet = quietRefresh === true
  const request = ++latest
  if (!quiet) {
    loading.value = true
    error.value = ''
  }
  try {
    const answer = await getFoodList(api, day.value)
    if (request === latest) items.value = answer.items
  } catch (err) {
    if (request === latest && quiet) throw err // what is shown stays; the refresh button learns it failed
    if (request === latest) error.value = err instanceof ApiError ? err.message : 'Something went wrong.'
  } finally {
    if (request === latest) loading.value = false
  }
}
watch(day, () => load(), { immediate: true })
const live = useLiveRefresh(() => (loading.value ? undefined : load(true)))

const plan = computed(() => foodDay(items.value ?? [], day.value, today.value, clock.value))

// The booking's drawer: loaded before it opens (see usePanelRecord), so a reload on ?booking= works.
const session = useSessionStore()
const panel = usePanelParam('booking')
const { record: openBooking, error: openError, load: loadOpen } = usePanelRecord(panel.id, (id) => getBooking(api, id))
/** After an Admin action: the drawer shows the new booking and the list reloads. */
async function onChanged(booking: BookingDetail) {
  openBooking.value = booking
  await load(true).catch(() => undefined)
}

const packages = (order: CateringOrderItem) => order.packages.map((p) => String(p.name)).join(', ')
const hhmm = (time: string) => time.slice(0, 5)
const SKELETON_COLUMNS = ['72px', '3fr', '3fr', '2fr', '110px']
</script>

<template>
  <div class="places-page">
    <div class="page-head">
      <h1>Food list</h1>
      <span class="mono count">{{ formatDay(day) }}</span>
      <RefreshButton class="new" :live="live" />
    </div>

    <div class="filters days">
      <BaseButton variant="quiet" @click="go(addDays(day, -1))">
        <ChevronLeft aria-hidden="true" />
        Previous day
      </BaseButton>
      <BaseButton variant="quiet" :disabled="day === today" @click="go(today)">Today</BaseButton>
      <BaseButton variant="quiet" @click="go(addDays(day, 1))">
        Next day
        <ChevronRight aria-hidden="true" />
      </BaseButton>
      <div class="pick">
        <DatePicker id="food-day" label="Day" :model-value="day" @update:model-value="$event && go($event)" />
      </div>
    </div>

    <div v-if="openError" class="summary open-error" role="alert">
      <CircleAlert aria-hidden="true" />
      <div>
        <b>Booking {{ panel.id.value }}: {{ openError }}</b>
        <BaseButton variant="quiet" @click="loadOpen">Try again</BaseButton>
        <BaseButton variant="quiet" @click="panel.close">Close</BaseButton>
      </div>
    </div>

    <OfflineNote :live="live" />

    <div class="sheet">
      <div v-if="error" class="summary load-error" role="alert">
        <CircleAlert aria-hidden="true" />
        <div>
          <b>{{ error }}</b>
          <BaseButton variant="quiet" @click="load">Try again</BaseButton>
        </div>
      </div>
      <TableSkeleton v-else-if="loading && !items" :columns="SKELETON_COLUMNS" />
      <EmptyState v-else-if="items && !items.length" title="No food orders on this day." text="Orders show here once Pitika approves the booking." />
      <div v-else-if="items" class="table-scroll" :aria-busy="loading || undefined">
        <table class="list food">
          <caption class="sr-only">Food orders on {{ formatDay(day) }}</caption>
          <thead>
            <tr>
              <th scope="col" class="time-col">Time</th>
              <th scope="col">Deliver to</th>
              <th scope="col">Food</th>
              <th scope="col">Meeting</th>
              <th scope="col" class="it-col"><span class="sr-only">IT</span></th>
            </tr>
          </thead>
          <tbody>
            <template v-for="(order, i) in items" :key="`${order.booking_id}-${order.session_number}`">
              <tr v-if="plan.nowAt === i" class="now-line">
                <td colspan="5"><span class="now mono">Now {{ clock }}</span></td>
              </tr>
              <tr data-order :data-state="plan.states[i]" :class="plan.states[i]">
                <td class="time">
                  <span class="mono">{{ hhmm(order.delivery_time) }}</span>
                  <span v-if="plan.states[i] === 'next'" class="next-word">Next</span>
                </td>
                <td>
                  <span class="room">{{ order.room.name_en }}</span>
                  <span class="kh room-kh">{{ order.room.name_kh }}</span>
                  <span class="floor">{{ order.room.floor.floor_label }}</span>
                  <span class="sub">{{ order.room.building.name_en }} · {{ order.room.location.name_en }}</span>
                </td>
                <td class="food-cell">
                  <span class="packages-line">{{ packages(order) }}</span>
                  <span v-if="order.remarks" class="note booker">Booker: {{ order.remarks }}</span>
                  <span v-if="order.approver_notes" class="note pitika">Pitika: {{ order.approver_notes }}</span>
                </td>
                <td class="meeting">
                  <button type="button" class="title link" @click="panel.open(order.booking_id)">{{ order.meeting_title }}</button>
                  <span class="sub mono">{{ order.reference_code }}</span>
                  <span v-if="order.session_count > 1" class="sub session">Session {{ order.session_number }} of {{ order.session_count }}</span>
                </td>
                <td class="it">{{ order.booking_status === 'SETUP_IN_PROGRESS' ? 'IT setting up' : '' }}</td>
              </tr>
            </template>
            <tr v-if="plan.nowAt === items.length" class="now-line">
              <td colspan="5"><span class="now mono">Now {{ clock }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <BookingPanel
      v-if="openBooking"
      :key="`booking-${openBooking.id}`"
      :booking="openBooking"
      :admin-actions="session.isAdmin"
      @close="panel.close"
      @changed="onChanged"
    />
  </div>
</template>

<style scoped src="./listPage.css"></style>

<style scoped>
.days {
  align-items: center;
  gap: 4px;
}
.pick {
  margin-left: auto;
}
.pick .date-picker {
  width: 172px;
}

/* The table */
table.food td {
  vertical-align: top;
  padding-block: 12px;
}
table.food tbody tr {
  cursor: default;
}
.time-col {
  width: 84px;
}
.it-col {
  width: 120px;
}
.time .mono {
  display: block;
  font-size: 15px;
  font-weight: 500;
}
.next-word {
  display: block;
  margin-top: 3px;
  font-size: 11.5px;
  font-weight: 500;
  color: var(--color-warn);
}
.room {
  font-weight: 500;
}
.room-kh {
  margin-left: 6px;
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.kh {
  font-family: var(--font-kh);
}
.floor,
.packages-line,
.note,
.meeting .title,
.sub {
  display: block;
}
.floor {
  margin-top: 2px;
}
.note {
  margin-top: 4px;
  font-size: 13px;
  white-space: pre-line;
  overflow-wrap: anywhere;
}
.note.booker {
  color: var(--color-warn);
}
.note.pitika {
  color: var(--color-intaglio);
}
.meeting {
  font-size: 13px;
}
/* The meeting title opens the drawer: text that looks like the title, crimson on hover. */
.link {
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.link:hover {
  color: var(--color-crimson);
}
.link:focus-visible {
  outline: 2px solid var(--color-ink);
  outline-offset: 2px;
  border-radius: 4px;
}
.sub {
  font-size: 12px;
  color: var(--color-ink-off);
}
.it {
  font-size: 12.5px;
  color: var(--color-intaglio);
  white-space: nowrap;
}
/* Today: past rows faded, the next time on a soft warm wash, the red Now line between. */
table.food tr.past td,
table.food tr.past td * {
  color: var(--color-ink-off);
}
tr.next td {
  background: color-mix(in srgb, var(--color-warn) 6%, var(--color-sheet));
}
table.food tbody tr.now-line:hover {
  background: none;
}
tr.now-line td {
  position: relative;
  height: 0;
  padding: 0;
  border-bottom: 2px solid var(--color-crimson);
}
.now {
  position: absolute;
  top: -9px;
  left: 10px;
  padding: 1px 8px;
  border-radius: 999px;
  background: var(--color-crimson-fill);
  color: #fff;
  font-size: 11px;
}
</style>
