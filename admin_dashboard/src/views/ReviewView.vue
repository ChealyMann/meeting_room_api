<script setup lang="ts">
// The Pitika's queue (spec docs/superpowers/specs/2026-11-05-pitika-review-design.md): the
// bookings of their province waiting for them, grouped by urgency, each with the room's photo,
// what to check and the row bar ("gap is you"). Details are loaded per booking for the labels.
import { CalendarDays, Check, CircleAlert, EyeOff, Monitor, TriangleAlert, User, Users, Utensils, X } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '../api'
import { getBooking, getPitikaSummary, listPitikaBookingPage, pitikaApprove, pitikaReject } from '../api/bookings'
import { ApiError } from '../api/errors'
import { listAllRooms } from '../api/references'
import type { BookingDetail, BookingListItem, PitikaSummary, RoomListItem } from '../api/types'
import BaseButton from '../components/base/BaseButton.vue'
import DatePicker from '../components/base/DatePicker.vue'
import EmptyState from '../components/list/EmptyState.vue'
import ListSearch from '../components/list/ListSearch.vue'
import SearchPicker, { type PickerItem } from '../components/list/SearchPicker.vue'
import TableSkeleton from '../components/list/TableSkeleton.vue'
import ProcessBar from '../components/ProcessBar.vue'
import RoomPhoto from '../components/RoomPhoto.vue'
import { usePanelParam } from '../composables/usePanelParam'
import { usePhnomPenhToday } from '../composables/usePhnomPenhToday'
import { useResourceList } from '../composables/useResourceList'
import { useToast } from '../composables/useToast'
import { useSessionStore } from '../stores/session'
import { tabFrom, type Tab } from '../utils/decided'
import { checkLabels, groupByUrgency, nextStepText, rowSteps, startsIn } from '../utils/reviewQueue'
import { FILTER_WORDS } from '../utils/pickerWords'
import { formatDay } from '../utils/time'
import BookingActionDialog from './bookings/BookingActionDialog.vue'
import ReviewPanel from './bookings/ReviewPanel.vue'
import DecidedList from './review/DecidedList.vue'
import ReviewHead from './review/ReviewHead.vue'

/** Whose queue this page is: the Pitika's, or the room owner's (Task 4 uses it). */
withDefaults(defineProps<{ reviewer?: 'pitika' | 'owner' }>(), { reviewer: 'pitika' })

// Filters in the address, like the other lists: room, a day range (any session in it), search.
const { list, result, loading, error, load } = useResourceList<BookingListItem>(
  { room_id: 'int', from: 'string', to: 'string', q: 'string' },
  // Every waiting booking on one page: the queue is short, and it is grouped, not paged.
  (params) =>
    listPitikaBookingPage(api, {
      status: 'PENDING_PITIKA',
      room_id: params.room_id as number | undefined,
      from: params.from as string | undefined,
      to: params.to as string | undefined,
      q: params.q as string | undefined,
      page: 1,
      size: 100,
    }),
  { activeFilter: false },
)
const f = computed(() => list.filters.value as Record<string, string | number | undefined>)
const anyFilter = computed(() => Object.keys(list.filters.value).length > 0)
const DAY = /^\d{4}-\d{2}-\d{2}$/
const dayOf = (key: 'from' | 'to') => {
  const value = f.value[key]
  return typeof value === 'string' && DAY.test(value) ? value : null
}
const items = computed(() => result.value?.items ?? [])

// The details give the labels (food, IT, private reason); a failed one leaves its labels out.
const details = ref<Record<number, BookingDetail>>({})
watch(items, async (list) => {
  const missing = list.filter((b) => !details.value[b.id])
  const answers = await Promise.allSettled(missing.map((b) => getBooking(api, b.id)))
  const next = { ...details.value }
  answers.forEach((a, k) => {
    if (a.status === 'fulfilled') next[missing[k]!.id] = a.value
  })
  details.value = next
})

// Rooms, loaded once: their cover photos, and the room filter (only the Pitika's province).
const rooms = ref<RoomListItem[]>([])
const covers = computed(() => Object.fromEntries(rooms.value.map((r) => [r.id, r.cover_photo ?? null])))
const session = useSessionStore()
const roomItems = computed<PickerItem[]>(() => {
  const province = session.user?.province?.code
  return rooms.value
    .filter((r) => !province || r.province.code === province)
    .map((r) => ({ value: r.id, label: r.name_en, keywords: `${r.name_kh} ${r.location.name_en}` }))
})
onMounted(async () => {
  try {
    rooms.value = await listAllRooms(api)
  } catch {
    // no photos and no room filter: the rows show the plain tile
  }
})

const today = usePhnomPenhToday()
// "Starts in …" counts down; it is worked out again every minute.
const now = ref(new Date())
let tick: ReturnType<typeof setInterval> | undefined
onMounted(() => (tick = setInterval(() => (now.value = new Date()), 60_000)))
onBeforeUnmount(() => clearInterval(tick))

const groups = computed(() => groupByUrgency(items.value, today.value))

// --- Today's summary and the tabs (spec 2026-11-05-pitika-decided-design) -----------------
const summary = ref<PitikaSummary | null>(null)
async function loadSummary() {
  try {
    summary.value = await getPitikaSummary(api)
  } catch {
    // no ring and no numbers: the lists still work
  }
}
onMounted(loadSummary)
watch(today, loadSummary)

const route = useRoute()
const router = useRouter()
const tab = computed<Tab>(() => tabFrom(route.query.tab))
/** Another tab: the filters stay; the page and the open booking do not. */
function selectTab(next: Tab) {
  const query = { ...route.query }
  for (const key of ['tab', 'page', 'id']) delete query[key]
  if (next !== 'waiting') query.tab = next
  void router.replace({ query })
}

const hhmm = (time: string) => time.slice(0, 5)
const whenText = (b: BookingListItem) => (b.first_session.date === today.value ? `Today, ${formatDay(b.first_session.date)}` : formatDay(b.first_session.date))

// --- The panel (the open booking lives in the address, ?id=12) ------------------------------
const panel = usePanelParam()
const openItem = computed(() => items.value.find((b) => b.id === panel.id.value) ?? null)
const openDetail = computed(() => (panel.id.value !== null ? (details.value[panel.id.value] ?? null) : null))
watch(
  () => panel.id.value,
  async (id) => {
    if (id === null || tab.value !== 'waiting' || details.value[id]) return
    try {
      details.value = { ...details.value, [id]: await getBooking(api, id) }
    } catch {
      panel.close() // gone, or not this Pitika's: nothing to show
    }
  },
  { immediate: true },
)

// --- Approve and reject (the Ledger pop-up) ------------------------------------------------
type Decision = 'approve' | 'reject'
const asking = ref<{ action: Decision; booking: BookingListItem } | null>(null)
const askText = ref('')
const askBusy = ref(false)
const askError = ref('')
const askFieldError = ref('')
const toast = useToast()

function ask(action: Decision, booking: BookingListItem) {
  asking.value = { action, booking }
  askText.value = ''
  askError.value = ''
  askFieldError.value = ''
}
const askDetail = computed(() => (asking.value ? (details.value[asking.value.booking.id] ?? null) : null))
const askEffect = computed(() => {
  if (!asking.value) return ''
  if (asking.value.action === 'reject') return 'The booking stops and the room is free again. The booker sees your reason.'
  return askDetail.value ? nextStepText(askDetail.value) : ''
})
const askTimes = computed(() => {
  const b = asking.value?.booking
  if (!b) return ''
  const more = b.session_count - 1
  return `${hhmm(b.first_session.start_time)}–${hhmm(b.first_session.end_time)}${more > 0 ? ` +${more} more` : ''}`
})

async function decide() {
  if (!asking.value) return
  const { action, booking } = asking.value
  const text = askText.value.trim()
  askBusy.value = true
  askError.value = ''
  askFieldError.value = ''
  try {
    if (action === 'approve') await pitikaApprove(api, booking.id, { notes: text || null, version: booking.version })
    else await pitikaReject(api, booking.id, { reason: text, version: booking.version })
    toast.show(`${booking.reference_code} ${action === 'approve' ? 'approved' : 'rejected'}`, booking.meeting_title)
    asking.value = null
    if (panel.id.value === booking.id) panel.close()
    await Promise.all([load(), loadSummary()])
  } catch (err) {
    if (err instanceof ApiError) {
      askFieldError.value = err.fields.reason ?? err.fields.notes ?? ''
      askError.value = askFieldError.value ? '' : err.message
      // Decided by someone else, started, or changed: show the queue as it is now.
      if (err.status === 409 || err.status === 403 || err.status === 404) await Promise.all([load(), loadSummary()])
    } else {
      askError.value = 'Something went wrong.'
    }
  } finally {
    askBusy.value = false
  }
}
</script>

<template>
  <div class="places-page review">
    <ReviewHead :summary="summary" :tab="tab" @select="selectTab" />

    <div class="filters" role="search">
      <ListSearch
        :value="(f.q as string | undefined) ?? ''"
        label="Search bookings"
        placeholder="Search title, reference or booker"
        @search="list.set({ q: $event })"
      />
      <SearchPicker
        id="filter-room"
        searchable
        class="narrow"
        :items="roomItems"
        :words="FILTER_WORDS.room"
        :model-value="(f.room_id as number | undefined) ?? null"
        @update:model-value="list.set({ room_id: $event })"
      />
      <div class="day">
        <span class="label" aria-hidden="true">From</span>
        <DatePicker
          id="filter-from"
          label="From"
          placeholder="Any day"
          clearable
          :max="dayOf('to')"
          :model-value="dayOf('from')"
          @update:model-value="list.set({ from: $event })"
        />
      </div>
      <div class="day">
        <span class="label" aria-hidden="true">To</span>
        <DatePicker
          id="filter-to"
          label="To"
          placeholder="Any day"
          clearable
          :min="dayOf('from')"
          :model-value="dayOf('to')"
          @update:model-value="list.set({ to: $event })"
        />
      </div>
      <BaseButton v-if="anyFilter" variant="quiet" class="clear-filters" @click="list.reset()">
        <X aria-hidden="true" />
        Clear filters
      </BaseButton>
    </div>

    <div v-if="tab === 'waiting'" class="queue">
      <div v-if="error" class="summary load-error" role="alert">
        <CircleAlert aria-hidden="true" />
        <div>
          <b>{{ error }}</b>
          <BaseButton variant="quiet" @click="load">Try again</BaseButton>
        </div>
      </div>
      <TableSkeleton v-else-if="loading && !result" :columns="['168px', '2fr', '220px']" />
      <EmptyState
        v-else-if="result && !items.length"
        :filtered="anyFilter"
        :title="anyFilter ? 'No bookings match' : 'Nothing to review'"
        :text="anyFilter ? 'Nothing waiting matches these filters.' : 'New bookings in your province show here.'"
      >
        <BaseButton v-if="anyFilter" @click="list.reset()">Clear filters</BaseButton>
      </EmptyState>
      <template v-else-if="result">
        <section v-for="group in groups" :key="group.key" :aria-labelledby="`group-${group.key}`">
          <div class="group-head" :class="group.key">
            <h2 :id="`group-${group.key}`">{{ group.label }}</h2>
            <span class="n mono">{{ group.items.length }}</span>
            <p v-if="group.hint">{{ group.hint }}</p>
          </div>
          <ul class="rows">
            <li
              v-for="b in group.items"
              :key="b.id"
              class="row"
              :class="{ current: panel.id.value === b.id }"
              :data-booking="b.id"
              tabindex="0"
              @click="panel.open(b.id)"
              @keydown.enter.self="panel.open(b.id)"
            >
              <RoomPhoto class="thumb" :path="covers[b.room.id]?.thumbnail_url ?? null" :alt="b.room.name_en" />
              <div class="info">
                <span class="ref mono"><span class="prefix">{{ b.reference_code.slice(0, 3) }}</span>{{ b.reference_code.slice(3) }}</span>
                <h3>{{ b.meeting_title }}</h3>
                <div class="room"><span class="kh">{{ b.room.name_kh }}</span> · {{ b.room.name_en }}</div>
                <div class="facts">
                  <span>
                    <CalendarDays aria-hidden="true" />{{ whenText(b) }} ·
                    <span class="mono">{{ hhmm(b.first_session.start_time) }}–{{ hhmm(b.first_session.end_time) }}</span>
                    <template v-if="b.session_count > 1"> +{{ b.session_count - 1 }} more</template>
                  </span>
                  <span><User aria-hidden="true" />{{ b.requester.name_en }}</span>
                  <span><Users aria-hidden="true" />{{ b.attendees }} people</span>
                </div>
                <div v-if="details[b.id] && checkLabels(details[b.id]!).length" class="checks">
                  <span v-for="c in checkLabels(details[b.id]!)" :key="c.kind" class="chk" :class="c.kind">
                    <EyeOff v-if="c.kind === 'private'" aria-hidden="true" />
                    <Utensils v-else-if="c.kind === 'food'" aria-hidden="true" />
                    <Monitor v-else-if="c.kind === 'it'" aria-hidden="true" />
                    <TriangleAlert v-else aria-hidden="true" />
                    <b>{{ c.text }}</b>
                    <span v-if="c.count" class="mono">×{{ c.count }}</span>
                  </span>
                </div>
              </div>
              <div class="side">
                <span v-if="group.key === 'today'" class="soon"><TriangleAlert aria-hidden="true" />{{ startsIn(b, now) }}</span>
                <ProcessBar :steps="rowSteps(b)" />
                <div class="acts">
                  <BaseButton variant="danger" @click.stop="ask('reject', b)">Reject</BaseButton>
                  <BaseButton variant="primary" @click.stop="ask('approve', b)"><Check aria-hidden="true" />Approve</BaseButton>
                </div>
              </div>
            </li>
          </ul>
        </section>
      </template>
    </div>
    <DecidedList v-else :key="tab" :decision="tab === 'approved' ? 'APPROVED' : 'REJECTED'" :covers="covers" />

    <ReviewPanel
      v-if="tab === 'waiting' && openItem && openDetail"
      :key="`review-${openItem.id}`"
      :booking="openDetail"
      :photo-path="covers[openItem.room.id]?.url ?? null"
      :starts-in="openItem.first_session.date <= today ? startsIn(openItem, now) : null"
      @close="panel.close"
      @approve="ask('approve', openItem)"
      @reject="ask('reject', openItem)"
    />

    <BookingActionDialog
      v-if="asking"
      v-model="askText"
      :action="asking.action"
      :title="asking.action === 'approve' ? 'Approve this booking?' : 'Reject this booking?'"
      :confirm-label="asking.action === 'approve' ? 'Approve' : 'Reject'"
      :field-label="asking.action === 'approve' ? 'Notes (optional)' : 'Reason'"
      :max="1000"
      :min-length="asking.action === 'reject' ? 5 : 0"
      :meeting="asking.booking.meeting_title"
      :reference="asking.booking.reference_code"
      :day="formatDay(asking.booking.first_session.date)"
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
.filters > .narrow {
  width: 184px;
}
.day {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  color: var(--color-ink-off);
}
.day .date-picker {
  width: 164px;
}
.clear-filters {
  color: var(--color-crimson);
}
.queue {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  border-top: 1px solid var(--color-rule-strong);
}
.group-head {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 14px 12px 8px;
  border-bottom: 1px solid var(--color-rule-strong);
  background: var(--color-paper);
}
.group-head h2 {
  margin: 0;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-intaglio);
}
.group-head .n {
  font-size: 11px;
  color: var(--color-intaglio);
}
.group-head p {
  margin: 0 0 0 auto;
  font-size: 12px;
}
.group-head.today {
  border-bottom-color: transparent;
  box-shadow: inset 0 -2px 0 var(--color-crimson);
}
.group-head.today h2,
.group-head.today .n,
.group-head.today p {
  color: var(--color-crimson);
}
.group-head.today p {
  font-weight: 500;
}
.rows {
  margin: 0;
  padding: 0;
  list-style: none;
}
.row {
  display: grid;
  grid-template-columns: 168px minmax(0, 1fr) 232px;
  gap: 20px;
  align-items: center;
  padding: 16px 12px;
  border-bottom: 1px solid var(--color-rule);
  transition: background-color 150ms ease;
}
.row {
  cursor: pointer;
}
.row:hover {
  background: var(--color-row-hover);
}
.row.current {
  background: var(--color-crimson-wash);
}
.row:focus-visible {
  outline: 2px solid var(--color-crimson);
  outline-offset: -2px;
}
.acts {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}
.acts :deep(.btn) {
  height: 32px;
  padding: 0 12px;
  font-size: 13px;
}
.thumb {
  width: 168px;
  aspect-ratio: 16 / 10;
  border-radius: 8px;
}
.info {
  min-width: 0;
}
.ref {
  font-size: 11.5px;
  color: var(--color-intaglio);
}
.prefix {
  color: var(--color-crimson);
}
.info h3 {
  margin: 2px 0;
  font-size: 15px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.room {
  font-size: 13px;
  color: var(--color-intaglio);
}
.room .kh {
  font-family: var(--font-kh);
  font-weight: 500;
  color: var(--color-ink);
}
.facts {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  margin-top: 8px;
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.facts > span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.facts .mono {
  font-size: 12px;
  color: var(--color-ink);
}
.facts :deep(svg.lucide),
.chk :deep(svg.lucide) {
  width: 14px;
  height: 14px;
  flex: none;
}
.checks {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}
.chk {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 24px;
  padding: 2px 8px;
  border: 1px solid var(--color-rule);
  border-radius: 6px;
  background: var(--color-paper);
  font-size: 12px;
}
.chk :deep(svg.lucide) {
  color: var(--color-intaglio);
}
.chk b {
  font-weight: 500;
}
.chk .mono {
  font-size: 11.5px;
  color: var(--color-intaglio);
}
.chk.private {
  border-color: var(--color-danger-line);
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
}
.chk.private :deep(svg.lucide) {
  color: var(--color-crimson);
}
.side {
  display: grid;
  gap: 10px;
  align-content: center;
}
.soon {
  justify-self: end;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
  font-size: 12px;
  font-weight: 500;
}
.soon :deep(svg.lucide) {
  width: 13px;
  height: 13px;
}

@media (max-width: 1100px) {
  .row {
    grid-template-columns: 132px minmax(0, 1fr);
  }
  .thumb {
    width: 132px;
  }
  .side {
    grid-column: 1 / -1;
  }
  .soon {
    justify-self: start;
  }
  .acts {
    justify-content: flex-start;
  }
}
@media (max-width: 560px) {
  .row {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  .thumb {
    width: 100%;
  }
}
</style>
