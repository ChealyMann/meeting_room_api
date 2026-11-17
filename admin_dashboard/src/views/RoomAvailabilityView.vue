<script setup lang="ts">
// Room availability (spec 2026-11-17-room-availability-design, owner pick 17 Nov 2026): every
// room's day on one page for the Pitika (their province) and the Admin (every room). The Food
// list's head and day buttons; one filter row led by "Free at"; one row per room with its
// bookings on a 07:00–18:00 lane, the past hatched and a red Now line today. No summary numbers
// above the table (owner, twice). The day lives in the address (?date=2026-11-04; none = today).
// Hover a booking for its title, times and booker; click it for its drawer (?booking=ID): a booking
// waiting for Pitika opens the To review panel with Approve and Reject, anything else the Bookings
// drawer, like the Food list.
import { ChevronLeft, ChevronRight, CircleAlert, Globe, Lock } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '../api'
import { getBooking } from '../api/bookings'
import { ApiError } from '../api/errors'
import { listAllRooms } from '../api/references'
import { getDaySchedule } from '../api/staff'
import type { BookingDetail, RoomDaySchedule, RoomListItem } from '../api/types'
import BaseButton from '../components/base/BaseButton.vue'
import DatePicker from '../components/base/DatePicker.vue'
import EmptyState from '../components/list/EmptyState.vue'
import ListSearch from '../components/list/ListSearch.vue'
import OfflineNote from '../components/list/OfflineNote.vue'
import RefreshButton from '../components/list/RefreshButton.vue'
import SearchPicker, { type PickerItem } from '../components/list/SearchPicker.vue'
import TableSkeleton from '../components/list/TableSkeleton.vue'
import RoomPhoto from '../components/RoomPhoto.vue'
import { useLiveRefresh } from '../composables/useLiveRefresh'
import { usePanelParam } from '../composables/usePanelParam'
import { usePanelRecord } from '../composables/usePanelRecord'
import { useToast } from '../composables/useToast'
import { usePhnomPenhToday } from '../composables/usePhnomPenhToday'
import { useSessionStore } from '../stores/session'
import { FILTER_WORDS } from '../utils/pickerWords'
import { blockKind, clockLabel, freeAtOptions, freeUntil, lanePct, toMinutes } from '../utils/roomDay'
import { addDays, formatDay, phnomPenhClock } from '../utils/time'
import BookingActionDialog from './bookings/BookingActionDialog.vue'
import BookingPanel from './bookings/BookingPanel.vue'
import ReviewPanel from './bookings/ReviewPanel.vue'
import { REVIEWERS } from './review/reviewers'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()

// --- The day (in the address) and the clock ------------------------------------------------
const DAY = /^\d{4}-\d{2}-\d{2}$/
const today = usePhnomPenhToday()
const day = computed(() => {
  const value = route.query.date
  return typeof value === 'string' && DAY.test(value) ? value : today.value
})
const isToday = computed(() => day.value === today.value)
function go(next: string) {
  void router.push({ query: next === today.value ? {} : { date: next } })
}
const clock = ref(phnomPenhClock(new Date()))
const now = computed(() => toMinutes(clock.value))
let tick: ReturnType<typeof setInterval> | undefined
onMounted(() => (tick = setInterval(() => (clock.value = phnomPenhClock(new Date())), 20_000)))
onBeforeUnmount(() => clearInterval(tick))

// --- Rooms (once) and the day's bookings ------------------------------------------------
const rooms = ref<RoomListItem[] | null>(null)
const schedule = ref<Record<number, RoomDaySchedule['items']>>({})
const loading = ref(false)
const error = ref('')
let latest = 0

/** Active rooms the reader looks after: the Pitika's province, or every room for the Admin. */
const myRooms = computed(() => {
  const province = session.user?.province?.code ?? null
  return (rooms.value ?? []).filter((r) => r.is_active && (session.isAdmin || r.province.code === province))
})

/** `quiet` (only a real `true`): the live refresh — no spinner, a failure keeps what is shown. */
async function load(quietRefresh?: unknown) {
  const quiet = quietRefresh === true
  const request = ++latest
  if (!quiet) {
    loading.value = true
    error.value = ''
  }
  try {
    if (rooms.value === null) rooms.value = await listAllRooms(api)
    const ids = myRooms.value.map((r) => r.id)
    const answer = ids.length ? await getDaySchedule(api, day.value, ids) : { items: [] }
    if (request === latest) schedule.value = Object.fromEntries(answer.items.map((d) => [d.room_id, d.items]))
  } catch (err) {
    if (request === latest && quiet) throw err
    if (request === latest) error.value = err instanceof ApiError ? err.message : 'Something went wrong.'
  } finally {
    if (request === latest) loading.value = false
  }
}
watch(day, () => load(), { immediate: true })
const live = useLiveRefresh(() => (loading.value ? undefined : load(true)))

// --- Filters, with the app's dropdown (SearchPicker): Free at first (Now today, Any time on other
// days; null = Any time), then the search, the kind and the building (null = all).
const freeAt = ref<string | null>(null)
const q = ref('')
const kind = ref<string | null>(null)
const buildingName = ref<string | null>(null)
watch(isToday, (yes) => (freeAt.value = yes ? 'now' : null), { immediate: true })
const defaultFreeAt = computed(() => (isToday.value ? 'now' : null))
const filtered = computed(() => !!q.value || !!kind.value || !!buildingName.value || freeAt.value !== defaultFreeAt.value)
function clearFilters() {
  q.value = ''
  kind.value = null
  buildingName.value = null
  freeAt.value = defaultFreeAt.value
}
/** Now, then every half hour; Any time is the picker's empty choice. */
const freeAtItems = computed<PickerItem[]>(() =>
  freeAtOptions()
    .filter((o) => o.value !== '')
    .map((o) => ({ value: o.value, label: o.label, keywords: o.value === 'now' ? clock.value : undefined })),
)
const KIND_ITEMS: PickerItem[] = [
  { value: 'shared', label: 'Shared rooms' },
  { value: 'private', label: 'Private rooms' },
]
const buildingItems = computed<PickerItem[]>(() =>
  [...new Set(myRooms.value.map((r) => r.building.name_en))].sort().map((name) => ({ value: name, label: name })),
)
/** The Free at time in minutes, or null for Any time. */
const at = computed(() => (freeAt.value === null ? null : freeAt.value === 'now' ? now.value : Number(freeAt.value)))

const rows = computed(() => {
  const words = q.value.trim().toLowerCase()
  const list = myRooms.value
    .filter((r) => !words || `${r.name_en} ${r.name_kh} ${r.floor.floor_label} ${r.building.name_en}`.toLowerCase().includes(words))
    .filter((r) => !kind.value || (kind.value === 'private') === r.is_private)
    .filter((r) => !buildingName.value || r.building.name_en === buildingName.value)
    .map((room) => {
      const items = schedule.value[room.id] ?? []
      return { room, items, until: at.value === null ? null : freeUntil(room, items, at.value) }
    })
    .sort((a, b) => a.room.building.name_en.localeCompare(b.room.building.name_en) || a.room.name_en.localeCompare(b.room.name_en))
  if (at.value !== null) list.sort((a, b) => Number(a.until === null) - Number(b.until === null) || (b.until ?? 0) - (a.until ?? 0))
  return list
})
const result = computed(() => {
  if (at.value === null) return ''
  const free = rows.value.filter((r) => r.until !== null).length
  const when = freeAt.value === 'now' ? `${clock.value}, now` : clockLabel(at.value)
  return `${free} of ${rows.value.length} rooms free at ${when}`
})
/** "Free for the rest of the day" when it stays free until the room closes. */
const fitsFor = (row: { room: RoomListItem; until: number | null }) =>
  row.until === null ? '' : row.until >= toMinutes(row.room.end_time) ? 'Free for the rest of the day' : `Free until ${clockLabel(row.until)}`

const HOURS = Array.from({ length: 11 }, (_, i) => clockLabel((7 + i) * 60))
const hhmm = (time: string) => time.slice(0, 5)
const span = (item: { start_time: string; end_time: string }) => {
  const left = lanePct(toMinutes(item.start_time))
  return { left: `calc(${left}% + 1px)`, width: `calc(${lanePct(toMinutes(item.end_time)) - left}% - 2px)` }
}
const SKELETON_COLUMNS = ['260px', '88px', '6fr']

// --- Hover: the booking's title, times and booker ------------------------------------------
type Item = RoomDaySchedule['items'][number]
const WAITING_FOR: Record<string, string> = { PENDING_PITIKA: 'Waiting for Pitika', PENDING_OWNER: 'Waiting for room owner' }
const tip = ref<{ item: Item; left: number; top: number; below: boolean } | null>(null)
function showTip(item: Item, event: Event) {
  const box = (event.currentTarget as HTMLElement).getBoundingClientRect()
  const below = box.top < 90
  tip.value = { item, left: Math.max(8, Math.min(box.left, window.innerWidth - 268)), top: below ? box.bottom + 8 : box.top - 8, below }
}
const hideTip = () => (tip.value = null)

// --- The drawer (?booking=ID) -------------------------------------------------------------
const panel = usePanelParam('booking')
const { record: openBooking, load: loadOpen } = usePanelRecord(panel.id, (id) => getBooking(api, id))
function open(item: Item) {
  hideTip()
  if (item.booking_id !== null && !item.is_masked) panel.open(item.booking_id)
}
/** A Pitika decides a booking waiting for Pitika right here; anything else is read in the drawer. */
const canDecide = computed(() => openBooking.value?.display_status === 'PENDING_PITIKA' && session.roleCodes.includes('PITIKA'))
const coverOf = (roomId: number) => rooms.value?.find((r) => r.id === roomId)?.cover_photo?.url ?? null
async function onChanged(booking: BookingDetail) {
  openBooking.value = booking
  await load(true).catch(() => undefined)
}

// --- Approve and reject: the same pop-up as To review ---------------------------------------
type Decision = 'approve' | 'reject'
const asking = ref<Decision | null>(null)
const askText = ref('')
const askBusy = ref(false)
const askError = ref('')
const askFieldError = ref('')
const toast = useToast()
function ask(action: Decision) {
  asking.value = action
  askText.value = ''
  askError.value = ''
  askFieldError.value = ''
}
const askEffect = computed(() => {
  if (asking.value === 'reject') return 'The booking stops and the room is free again. The booker sees your reason.'
  return openBooking.value ? REVIEWERS.pitika.nextStepText(openBooking.value) : ''
})
const askTimes = computed(() => {
  const b = openBooking.value
  if (!b) return ''
  const more = b.session_count - 1
  return `${hhmm(b.first_session.start_time)}–${hhmm(b.first_session.end_time)}${more > 0 ? ` +${more} more` : ''}`
})
async function decide() {
  const booking = openBooking.value
  const action = asking.value
  if (!action || !booking) return
  const text = askText.value.trim()
  askBusy.value = true
  askError.value = ''
  askFieldError.value = ''
  try {
    if (action === 'approve') await REVIEWERS.pitika.approve(booking.id, { notes: text || null, version: booking.version })
    else await REVIEWERS.pitika.reject(booking.id, { reason: text, version: booking.version })
    toast.show(`${booking.reference_code} ${action === 'approve' ? 'approved' : 'rejected'}`, booking.meeting_title)
    asking.value = null
    panel.close()
    await load(true).catch(() => undefined)
  } catch (err) {
    if (err instanceof ApiError) {
      askFieldError.value = err.fields.reason ?? err.fields.notes ?? ''
      askError.value = askFieldError.value ? '' : err.message
      // Decided by someone else, started, or changed: show the day and the booking as they are now.
      if ([403, 404, 409].includes(err.status)) await Promise.all([load(true).catch(() => undefined), loadOpen()])
    } else {
      askError.value = 'Something went wrong.'
    }
  } finally {
    askBusy.value = false
  }
}
</script>

<template>
  <div class="places-page">
    <div class="page-head">
      <h1>Room availability</h1>
      <span class="mono count">{{ formatDay(day) }}</span>
      <RefreshButton class="new" :live="live" />
    </div>

    <div class="filters days">
      <BaseButton variant="quiet" @click="go(addDays(day, -1))"><ChevronLeft aria-hidden="true" />Previous day</BaseButton>
      <BaseButton variant="quiet" :disabled="isToday" @click="go(today)">Today</BaseButton>
      <BaseButton variant="quiet" @click="go(addDays(day, 1))">Next day<ChevronRight aria-hidden="true" /></BaseButton>
      <div class="pick">
        <DatePicker id="rooms-day" label="Day" :model-value="day" @update:model-value="$event && go($event)" />
      </div>
    </div>

    <div class="filters row-filters">
      <div class="free-at">
        <span id="free-at-label" class="free-at-label">Free at</span>
        <SearchPicker
          id="free-at"
          v-model="freeAt"
          searchable
          :items="freeAtItems"
          :words="FILTER_WORDS.freeAt"
          described-by="free-at-label"
        />
      </div>
      <ListSearch :value="q" label="Search rooms" placeholder="Search room or floor" @search="q = $event" />
      <SearchPicker id="room-kind" v-model="kind" class="narrow" :items="KIND_ITEMS" :words="FILTER_WORDS.roomKind" />
      <SearchPicker id="room-building" v-model="buildingName" class="narrow" :items="buildingItems" :words="FILTER_WORDS.building" />
      <BaseButton v-if="filtered" variant="quiet" class="clear-filters" @click="clearFilters">Clear filters</BaseButton>
    </div>
    <p v-if="result" class="result" aria-live="polite">{{ result }}</p>

    <OfflineNote :live="live" />
    <div class="sheet">
      <div v-if="error" class="summary load-error" role="alert">
        <CircleAlert aria-hidden="true" />
        <div>
          <b>{{ error }}</b>
          <BaseButton variant="quiet" @click="load">Try again</BaseButton>
        </div>
      </div>
      <TableSkeleton v-else-if="loading && rooms === null" :columns="SKELETON_COLUMNS" />
      <EmptyState v-else-if="rooms && !myRooms.length" title="No rooms to show." text="Rooms of your province show here." />
      <EmptyState v-else-if="rooms && !rows.length" title="No room matches these filters." text="Try another search or building.">
        <BaseButton @click="clearFilters">Clear filters</BaseButton>
      </EmptyState>
      <div v-else-if="rooms" class="table-scroll" :aria-busy="loading || undefined">
        <div class="timeline" role="table" :aria-label="`Rooms on ${formatDay(day)}`">
          <div class="trow head" role="row">
            <div role="columnheader">Room</div>
            <div role="columnheader">Kind</div>
            <div class="hcell" role="columnheader">
              <div class="hours">
                <span v-for="h in HOURS" :key="h">{{ h }}</span>
                <span v-if="isToday" class="tag now-tag mono" :style="{ left: `${lanePct(now)}%` }">Now {{ clock }}</span>
                <span v-if="at !== null && freeAt !== 'now'" class="tag at-tag mono" :style="{ left: `${lanePct(at)}%` }">{{ clockLabel(at) }}</span>
              </div>
            </div>
          </div>
          <div
            v-for="row in rows"
            :key="row.room.id"
            class="trow"
            :class="{ 'not-free': at !== null && row.until === null }"
            role="row"
            :data-room="row.room.id"
            :data-free="at === null ? undefined : String(row.until !== null)"
          >
            <div class="room" role="cell">
              <RoomPhoto class="thumb" :path="row.room.cover_photo?.thumbnail_url ?? null" :alt="row.room.name_en" />
              <div class="names">
                <strong>{{ row.room.name_en }}<span class="kh">{{ row.room.name_kh }}</span></strong>
                <span class="sub">{{ row.room.floor.floor_label }} · {{ row.room.building.name_en }} · {{ row.room.capacity }} seats</span>
                <span v-if="at !== null && row.until !== null" class="fits">{{ fitsFor(row) }}</span>
              </div>
            </div>
            <div class="kind" role="cell">
              <template v-if="row.room.is_private"><Lock aria-hidden="true" />Private</template>
              <template v-else><Globe aria-hidden="true" />Shared</template>
            </div>
            <div class="lane" role="cell">
              <span v-if="isToday" class="past" :style="{ width: `${lanePct(now)}%` }" />
              <span v-if="!row.items.length" class="free-all">Free all day</span>
              <button
                v-for="(it, i) in row.items"
                :key="`${it.booking_id ?? 'm'}-${i}`"
                type="button"
                class="block"
                :class="blockKind(it)"
                :style="span(it)"
                :data-booking="it.booking_id ?? undefined"
                :aria-disabled="it.is_masked || undefined"
                :aria-describedby="tip && tip.item === it ? 'room-tip' : undefined"
                @mouseenter="showTip(it, $event)"
                @mouseleave="hideTip"
                @focus="showTip(it, $event)"
                @blur="hideTip"
                @click="open(it)"
              >
                <b>{{ it.is_masked ? 'Private booking' : it.title }}</b>
                <span class="mono">{{ hhmm(it.start_time) }}–{{ hhmm(it.end_time) }}</span>
              </button>
              <span v-if="isToday" class="now-line" :style="{ left: `${lanePct(now)}%` }" />
              <span v-if="at !== null && freeAt !== 'now'" class="at-line" :style="{ left: `${lanePct(at)}%` }" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="rooms && rows.length" class="legend">
      <span><i class="f" />Free</span>
      <span><i class="b" />Booked</span>
      <span><i class="w" />Waiting for approval</span>
      <span v-if="isToday"><i class="x" />Past</span>
    </div>

    <Teleport to="body">
      <div
        v-if="tip"
        id="room-tip"
        class="room-tip"
        role="tooltip"
        :class="{ below: tip.below }"
        :style="{ left: `${tip.left}px`, top: `${tip.top}px` }"
      >
        <b>{{ tip.item.is_masked ? 'Private booking' : tip.item.title }}</b>
        <span class="mono">{{ hhmm(tip.item.start_time) }}–{{ hhmm(tip.item.end_time) }}</span>
        <span v-if="!tip.item.is_masked && tip.item.requester_name"> · {{ tip.item.requester_name }}</span>
        <span v-if="!tip.item.is_masked && WAITING_FOR[tip.item.status]" class="waits">{{ WAITING_FOR[tip.item.status] }}</span>
      </div>
    </Teleport>

    <ReviewPanel
      v-if="openBooking && canDecide"
      :key="`review-${openBooking.id}`"
      :booking="openBooking"
      :photo-path="coverOf(openBooking.room.id)"
      :starts-in="null"
      :waiting-label="REVIEWERS.pitika.waitingLabel"
      :lead-card="REVIEWERS.pitika.leadCard"
      :note="REVIEWERS.pitika.panelNote(openBooking)"
      @close="panel.close"
      @approve="ask('approve')"
      @reject="ask('reject')"
    />
    <BookingPanel
      v-else-if="openBooking"
      :key="`booking-${openBooking.id}`"
      :booking="openBooking"
      :admin-actions="session.isAdmin"
      @close="panel.close"
      @changed="onChanged"
    />

    <BookingActionDialog
      v-if="asking && openBooking"
      v-model="askText"
      :action="asking"
      :title="asking === 'approve' ? 'Approve this booking?' : 'Reject this booking?'"
      :confirm-label="asking === 'approve' ? 'Approve' : 'Reject'"
      :field-label="asking === 'approve' ? 'Notes (optional)' : 'Reason'"
      :max="1000"
      :min-length="asking === 'reject' ? 5 : 0"
      :meeting="openBooking.meeting_title"
      :reference="openBooking.reference_code"
      :day="formatDay(openBooking.first_session.date)"
      :times="askTimes"
      :effect="askEffect"
      :busy="askBusy"
      :allowed="true"
      :error="askError"
      :field-error="askFieldError"
      @back="asking = null"
      @confirm="decide"
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

/* One filter row, led by Free at: the app's dropdown on a soft green box. */
.row-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.row-filters > .narrow {
  width: 184px;
}
.free-at {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 3px 3px 3px 12px;
  border: 1px solid color-mix(in srgb, var(--color-ok) 35%, var(--color-rule));
  border-radius: 12px;
  background: color-mix(in srgb, var(--color-ok) 10%, var(--color-sheet));
}
.free-at-label {
  color: var(--color-ok);
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
}
.free-at :deep(.picker) {
  width: 150px;
}
.clear-filters {
  color: var(--color-crimson);
}
.result {
  margin: 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-ok);
}

/* The timeline: Room · Kind · the 07:00–18:00 lane. */
.timeline {
  min-width: 980px;
}
.trow {
  display: grid;
  grid-template-columns: 270px 88px minmax(0, 1fr);
  align-items: center;
  border-bottom: 1px solid var(--color-rule);
  transition: opacity 160ms ease;
}
.trow:last-child {
  border-bottom: 0;
}
.trow.head {
  position: sticky;
  top: 0;
  z-index: 3;
  background: var(--color-paper);
  border-bottom-color: var(--color-rule-strong);
}
.trow.head > div {
  padding: 10px 12px;
  color: var(--color-intaglio);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.trow.head > .hcell {
  padding: 10px 12px 10px 0;
}
.trow:not(.head):hover {
  background: var(--color-row-hover);
}
.trow.not-free {
  opacity: 0.5;
}
.trow.not-free:hover {
  opacity: 0.85;
}
.hours {
  position: relative;
  display: grid;
  grid-template-columns: repeat(11, 1fr);
}
.hours > span:not(.tag) {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0;
  color: var(--color-ink-off);
}
.tag {
  position: absolute;
  top: -2px;
  z-index: 4;
  padding: 1px 7px;
  border-radius: 999px;
  color: #fff;
  font-size: 10.5px;
  letter-spacing: 0;
  white-space: nowrap;
  transform: translateX(-50%);
}
.now-tag {
  background: var(--color-crimson-fill);
}
.at-tag {
  top: 16px;
  background: var(--color-ok);
}
.room {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  min-width: 0;
}
.thumb {
  width: 56px;
  height: 38px;
  border-radius: 8px;
}
.names {
  min-width: 0;
}
.names strong {
  display: block;
  overflow: hidden;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.names .kh {
  margin-left: 4px;
  font-family: var(--font-kh);
  font-size: 12px;
  font-weight: 400;
  color: var(--color-intaglio);
}
.names .sub {
  display: block;
  overflow: hidden;
  color: var(--color-ink-off);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fits {
  display: block;
  color: var(--color-ok);
  font-size: 12px;
  font-weight: 500;
}
.kind {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 12px;
  color: var(--color-intaglio);
  font-size: 12.5px;
}
.kind svg {
  width: 14px;
  height: 14px;
}
.lane {
  position: relative;
  height: 46px;
  margin: 8px 12px 8px 0;
  border-radius: 10px;
  background-color: color-mix(in srgb, var(--color-ok) 7%, var(--color-sheet));
  background-image: repeating-linear-gradient(
    to right,
    transparent 0,
    transparent calc(100% / 11 - 1px),
    var(--color-rule) calc(100% / 11 - 1px),
    var(--color-rule) calc(100% / 11)
  );
}
.past {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  border-radius: 10px 0 0 10px;
  background: repeating-linear-gradient(135deg, color-mix(in srgb, var(--color-ink) 5%, transparent) 0 4px, transparent 4px 8px);
  pointer-events: none;
}
.free-all {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--color-ok);
  font-size: 12.5px;
  font-weight: 500;
  pointer-events: none;
}
.block {
  position: absolute;
  top: 5px;
  bottom: 5px;
  z-index: 1;
  display: grid;
  align-content: center;
  min-width: 0;
  overflow: hidden;
  padding: 4px 8px;
  border: 0;
  border-radius: 8px;
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition:
    transform 160ms var(--ease-out-quint),
    box-shadow 160ms ease;
}
.block:not(.masked):hover,
.block:focus-visible {
  z-index: 3;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(42, 28, 19, 0.12);
}
.block:focus-visible {
  outline: 2px solid var(--color-ink);
  outline-offset: 1px;
}
.block b {
  overflow: hidden;
  font-size: 12px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.block span {
  overflow: hidden;
  font-size: 10.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.block.booked {
  background: color-mix(in srgb, var(--color-crimson) 14%, var(--color-sheet));
  color: var(--color-crimson);
}
.block.waiting {
  border: 1px dashed color-mix(in srgb, var(--color-warn) 60%, transparent);
  background: color-mix(in srgb, var(--color-warn) 16%, var(--color-sheet));
  color: var(--color-warn);
}
.block.masked {
  background: var(--color-field-disabled);
  color: var(--color-ink-off);
  cursor: default;
}
.now-line,
.at-line {
  position: absolute;
  top: -4px;
  bottom: -4px;
  z-index: 2;
  width: 2px;
  pointer-events: none;
}
.now-line {
  background: var(--color-crimson);
}
.at-line {
  background: var(--color-ok);
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  margin-top: 12px;
  color: var(--color-intaglio);
  font-size: 12.5px;
}
.legend span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}
.legend i {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 4px;
}
.legend .f {
  background: color-mix(in srgb, var(--color-ok) 18%, var(--color-sheet));
}
.legend .b {
  background: color-mix(in srgb, var(--color-crimson) 22%, var(--color-sheet));
}
.legend .w {
  border: 1px dashed var(--color-warn);
  background: color-mix(in srgb, var(--color-warn) 22%, var(--color-sheet));
}
.legend .x {
  border: 1px solid var(--color-rule);
  background: repeating-linear-gradient(135deg, color-mix(in srgb, var(--color-ink) 14%, transparent) 0 3px, transparent 3px 6px);
}
/* Hover: a small dark card above the block (below it near the top of the window). */
.room-tip {
  position: fixed;
  z-index: 40;
  display: grid;
  max-width: 260px;
  padding: 8px 10px;
  border-radius: 10px;
  background: var(--color-ink);
  box-shadow: var(--shadow-toast);
  color: var(--color-sheet);
  font-size: 12.5px;
  line-height: 1.45;
  pointer-events: none;
  transform: translateY(-100%);
}
.room-tip.below {
  transform: none;
}
.room-tip b {
  font-weight: 600;
}
.room-tip span {
  opacity: 0.85;
}
.room-tip .waits {
  opacity: 1;
}
@media (prefers-reduced-motion: reduce) {
  .trow,
  .block {
    transition: none;
  }
}
</style>
