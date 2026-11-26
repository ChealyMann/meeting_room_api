<script setup lang="ts">
// My bookings (Staff), layout 2 "Folders on the left" (owner pick, 20 Nov 2026; no calendar: the
// owner removed it). On the left: search, then the folders Coming up (with Waiting and Confirmed
// under it) and Past & cancelled, each with its count. On the right: the To review soft rows
// (look E) grouped by day; only the rows scroll on a laptop. The row's cream footer says where the
// booking is and what happens next. A row opens its details; ?booking=<id> opens them too.
// Status always has an icon, never a dot.
import {
  Ban,
  Building2,
  Check,
  CalendarDays,
  CircleCheck,
  CircleX,
  Clock,
  MapPin,
  Monitor,
  Plus,
  Radio,
  Search,
  UserLock,
  Users,
  Utensils,
  Wrench,
} from 'lucide-vue-next'
import { computed, onMounted, ref, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '../../api'
import { listBookableRooms, listMyBookings } from '../../api/staff'
import type { BookingDetail, BookingListItem } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import EmptyState from '../../components/list/EmptyState.vue'
import OfflineNote from '../../components/list/OfflineNote.vue'
import RefreshButton from '../../components/list/RefreshButton.vue'
import SoftRow from '../../components/SoftRow.vue'
import { useLiveRefresh } from '../../composables/useLiveRefresh'
import { startsAt } from '../../utils/reviewQueue'
import { phnomPenhClock, phnomPenhDate, sentLabel } from '../../utils/time'
import BookingDetailDialog from './BookingDetailDialog.vue'
import { dateNumber, monthShort, weekdayShort } from './rules'
import './staff.css'

const route = useRoute()
const router = useRouter()

const items = ref<BookingListItem[]>([])
const covers = ref<Record<number, string | null>>({})
const loaded = ref(false)
const failed = ref(false)
const tab = ref<'soon' | 'past'>('soon')
const now = ref(new Date())

const PAST = ['REJECTED', 'CANCELLED', 'COMPLETED']
const WAITING = ['PENDING_PITIKA', 'PENDING_OWNER']
/** The session the row shows: the next one not ended, else the first. */
const sessionOf = (b: BookingListItem) => b.next_session ?? b.first_session
const startOf = (b: BookingListItem) => `${sessionOf(b).date} ${sessionOf(b).start_time}`
const today = computed(() => phnomPenhDate(now.value))
const hhmm = (t: string) => t.slice(0, 5)

const query = ref('')
const matches = (b: BookingListItem) => {
  const q = query.value.trim().toLowerCase()
  return !q || [b.meeting_title, b.room.name_en, b.room.name_kh, b.reference_code].some((text) => text.toLowerCase().includes(q))
}
const soon = computed(() => items.value.filter((b) => !PAST.includes(b.display_status) && matches(b)).sort((x, y) => (startOf(x) < startOf(y) ? -1 : 1)))
const past = computed(() => items.value.filter((b) => PAST.includes(b.display_status) && matches(b)).sort((x, y) => (startOf(x) < startOf(y) ? 1 : -1)))

type Status = 'all' | 'wait' | 'ok'
const status = ref<Status>('all')
const isWaiting = (b: BookingListItem) => WAITING.includes(b.display_status)
const shownSoon = computed(() => soon.value.filter((b) => status.value === 'all' || (status.value === 'wait') === isWaiting(b)))
const shown = computed(() => (tab.value === 'soon' ? shownSoon.value : past.value))

/** A session under way right now (only a confirmed booking meets). */
const isLive = (b: BookingListItem) => {
  const s = b.next_session
  const clock = phnomPenhClock(now.value)
  return b.display_status === 'CONFIRMED' && !!s && s.date === today.value && hhmm(s.start_time) <= clock && clock < hhmm(s.end_time)
}

const longDay = (iso: string) => `${weekdayShort(iso)} ${dateNumber(iso)} ${monthShort(iso)}`
/** The rows by the day of the session they show. */
const days = computed(() => {
  const map = new Map<string, BookingListItem[]>()
  for (const b of shown.value) {
    const d = sessionOf(b).date
    if (!map.has(d)) map.set(d, [])
    map.get(d)!.push(b)
  }
  return [...map].map(([date, list]) => ({ date, list, isToday: date === today.value && tab.value === 'soon' }))
})

/** The folders on the left: a folder picks the tab and the status filter at once. */
const folders = computed(() => {
  const waiting = soon.value.filter(isWaiting).length
  return [
    { key: 'soon-all', tab: 'soon' as const, status: 'all' as const, label: 'Coming up', icon: CalendarDays, count: soon.value.length, sub: false },
    { key: 'soon-wait', tab: 'soon' as const, status: 'wait' as const, label: 'Waiting', icon: Clock, count: waiting, sub: true },
    { key: 'soon-ok', tab: 'soon' as const, status: 'ok' as const, label: 'Confirmed', icon: CircleCheck, count: soon.value.length - waiting, sub: true },
    { key: 'past', tab: 'past' as const, status: 'all' as const, label: 'Past & cancelled', icon: Check, count: past.value.length, sub: false },
  ]
})
const isOpen = (f: { tab: 'soon' | 'past'; status: Status }) => tab.value === f.tab && (f.tab === 'past' || status.value === f.status)
function openFolder(f: { tab: 'soon' | 'past'; status: Status }) {
  tab.value = f.tab
  status.value = f.status
}

/** The footer's left side: the status with its icon, and what happens next. */
interface State {
  tone: 'ok' | 'wait' | 'off' | 'bad'
  icon: Component
  word: string
  next: string
}
function stateOf(b: BookingListItem): State {
  if (isLive(b)) return { tone: 'ok', icon: Radio, word: 'Happening now', next: `Until ${hhmm(b.next_session!.end_time)} · your door pass works until then` }
  switch (b.display_status) {
    case 'CONFIRMED':
      return { tone: 'ok', icon: CircleCheck, word: 'Confirmed', next: b.has_it ? 'Door pass ready · IT sets up the room' : 'Door pass ready' }
    case 'SETUP_IN_PROGRESS':
      return { tone: 'wait', icon: Wrench, word: 'IT setup', next: 'IT is getting the room ready' }
    case 'PENDING_PITIKA':
      return { tone: 'wait', icon: Clock, word: 'Waiting for Pitika', next: b.room.is_private ? 'Pitika checks it next, then the room owner' : 'Pitika checks it next' }
    case 'PENDING_OWNER':
      return { tone: 'wait', icon: Clock, word: 'Waiting for the room owner', next: 'Private room · the owner decides' }
    case 'REJECTED':
      return { tone: 'bad', icon: CircleX, word: 'Rejected', next: 'Open it to see the reason' }
    case 'CANCELLED':
      return { tone: 'off', icon: Ban, word: 'Cancelled', next: 'This booking was cancelled' }
    default:
      return { tone: 'off', icon: Check, word: 'Completed', next: 'This meeting is over' }
  }
}
const soonText = (b: BookingListItem) => {
  if (tab.value !== 'soon' || isLive(b) || sessionOf(b).date !== today.value) return ''
  const text = startsAt(sessionOf(b).date, sessionOf(b).start_time, now.value)
  return text === 'Started' ? '' : text
}
const moreText = (b: BookingListItem) => (b.session_count > 1 ? `${b.session_count} days` : null)
const place = (b: BookingListItem) => [b.room.floor?.floor_label, b.room.building?.short_name || b.room.building?.name_en].filter(Boolean).join(' · ')

/** `quiet`: the live refresh — what is shown stays when it fails. */
async function loadList(quiet = false) {
  try {
    items.value = (await listMyBookings(api, { page: 1, size: 100 })).items
    now.value = new Date()
    failed.value = false
  } catch (err) {
    if (quiet) throw err
    failed.value = true
  } finally {
    loaded.value = true
  }
}
const live = useLiveRefresh(() => loadList(true))

onMounted(async () => {
  await loadList()
  // Photos are a nice extra: without them the rows still work.
  listBookableRooms(api, { size: 100 })
    .then((page) => (covers.value = Object.fromEntries(page.items.map((r) => [r.id, r.cover_photo?.url ?? null]))))
    .catch(() => undefined)
})

const openId = computed(() => {
  const id = Number(route.query.booking)
  return Number.isInteger(id) && id > 0 ? id : null
})
const openBooking = (id: number) => router.replace({ query: { ...route.query, booking: String(id) } })
const closeBooking = () => {
  const { booking: _drop, ...rest } = route.query
  void _drop
  router.replace({ query: rest })
}
function changed(detail: BookingDetail) {
  items.value = items.value.map((b) =>
    b.id === detail.id ? { ...b, status: detail.status, display_status: detail.display_status, version: detail.version } : b,
  )
}
const coverOf = (roomId: number) => covers.value[roomId] ?? null
</script>

<template>
  <section class="st-page my-page">
    <header class="head">
      <h1>My bookings</h1>
      <div class="actions">
        <RefreshButton :live="live" />
        <BaseButton variant="primary" @click="router.push({ name: 'find-room' })"><Plus aria-hidden="true" />Book a room</BaseButton>
      </div>
    </header>
    <OfflineNote :live="live" class="offline" />

    <div class="frame">
      <nav class="folders" aria-label="My bookings">
        <label class="search">
          <Search aria-hidden="true" />
          <input v-model="query" type="search" placeholder="Title, room or reference" aria-label="Search my bookings by title, room or reference" />
        </label>
        <div class="folder-list">
          <template v-for="f in folders" :key="f.key">
            <span v-if="f.key === 'past'" class="sep" aria-hidden="true" />
            <button type="button" class="folder" :class="[f.key, { sub: f.sub }]" :aria-current="isOpen(f) ? 'page' : undefined" @click="openFolder(f)">
              <component :is="f.icon" aria-hidden="true" />
              <span class="label">{{ f.label }}</span>
              <span class="n mono">{{ f.count }}</span>
            </button>
          </template>
        </div>
      </nav>

      <div class="main">
        <p v-if="failed" class="st-empty" role="alert"><b>Your bookings could not load</b></p>
        <EmptyState v-else-if="loaded && query.trim() && !shown.length" title="Nothing found" :text="`No bookings match “${query.trim()}”.`">
          <BaseButton @click="query = ''">Clear search</BaseButton>
        </EmptyState>
        <EmptyState v-else-if="loaded && tab === 'soon' && !soon.length" title="Nothing coming up" text="Book a room and it shows here.">
          <BaseButton variant="primary" @click="router.push({ name: 'find-room' })">Book a room</BaseButton>
        </EmptyState>
        <EmptyState v-else-if="loaded && tab === 'soon' && !shownSoon.length" title="Nothing here" :text="status === 'wait' ? 'No booking is waiting for approval.' : 'No confirmed booking coming up.'">
          <BaseButton @click="status = 'all'">Show all</BaseButton>
        </EmptyState>
        <EmptyState v-else-if="loaded && tab === 'past' && !past.length" title="Nothing here yet" text="Past, cancelled and not approved bookings show here." />
        <template v-else-if="loaded">
          <section v-for="d in days" :key="d.date" class="day">
            <h2 class="day-head" :class="{ today: d.isToday }">
              {{ d.isToday ? `Today · ${longDay(d.date)}` : longDay(d.date) }}
              <span class="n mono">{{ String(d.list.length).padStart(2, '0') }}</span>
            </h2>
            <ul class="rows">
              <SoftRow
                v-for="b in d.list"
                :key="b.id"
                :class="{ 'is-live': isLive(b), 'is-past': tab === 'past' }"
                :start="hhmm(sessionOf(b).start_time)"
                :end="hhmm(sessionOf(b).end_time)"
                :day="d.isToday ? 'Today' : `${weekdayShort(d.date)} ${dateNumber(d.date)}`"
                :more="moreText(b)"
                :photo="coverOf(b.room.id)"
                :photo-alt="b.room.name_en"
                :reference="b.reference_code"
                :title="b.meeting_title"
                :soon="d.isToday"
                :sent="sentLabel(b.created_at, now)"
                @open="openBooking(b.id)"
              >
                <template #line>
                  <span class="bit"><MapPin aria-hidden="true" /><span class="kh">{{ b.room.name_kh }}</span></span>
                  <span class="bit">{{ b.room.name_en }}</span>
                  <span v-if="place(b)" class="bit"><Building2 aria-hidden="true" />{{ place(b) }}</span>
                  <span class="bit"><Users aria-hidden="true" /><span class="mono">{{ b.attendees }}</span></span>
                </template>
                <template v-if="b.room.is_private || b.has_catering || b.has_it" #tags>
                  <span v-if="b.room.is_private" class="soft-tag warn"><UserLock aria-hidden="true" />Private</span>
                  <span v-if="b.has_catering" class="soft-tag"><Utensils aria-hidden="true" />Food</span>
                  <span v-if="b.has_it" class="soft-tag"><Monitor aria-hidden="true" />IT help</span>
                </template>
                <template #lead>
                  <span class="stt" :class="stateOf(b).tone"><component :is="stateOf(b).icon" aria-hidden="true" />{{ stateOf(b).word }}</span>
                  <span class="nx">{{ stateOf(b).next }}</span>
                </template>
                <template v-if="soonText(b)" #status>
                  <span class="soon-pill"><Clock aria-hidden="true" />{{ soonText(b) }}</span>
                </template>
              </SoftRow>
            </ul>
          </section>
        </template>
      </div>
    </div>

    <BookingDetailDialog v-if="openId" :booking-id="openId" :cover="coverOf(items.find((b) => b.id === openId)?.room.id ?? 0)" @close="closeBooking" @changed="changed" />
  </section>
</template>

<style scoped>
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.head h1 {
  margin: 0;
  font-size: 30px;
  font-weight: 600;
  letter-spacing: -0.025em;
  line-height: 1.15;
}
.actions {
  display: flex;
  gap: 8px;
}
.offline {
  margin: 16px 0 0;
}
/* Folders on the left, the rows on the right (layout 2, owner pick 20 Nov 2026) */
.frame {
  display: grid;
  grid-template-columns: 248px minmax(0, 1fr);
  gap: 28px;
  align-items: start;
  margin-top: 22px;
}
.folders {
  display: grid;
  gap: 14px;
}
.search {
  position: relative;
}
.search svg {
  position: absolute;
  top: 50%;
  left: 12px;
  width: 15px;
  height: 15px;
  color: var(--color-ink-off);
  transform: translateY(-50%);
  pointer-events: none;
}
.search input {
  box-sizing: border-box;
  width: 100%;
  height: 38px;
  padding: 0 12px 0 36px;
  border: 1px solid var(--color-rule-strong);
  border-radius: 11px;
  outline: none;
  background: var(--color-sheet);
  color: var(--color-ink);
  font: inherit;
  font-size: 13px;
}
.search input:focus {
  border-color: var(--color-crimson);
  box-shadow: 0 0 0 3px rgba(153, 27, 27, 0.12);
}
.folder-list {
  display: grid;
  gap: 2px;
}
.folder {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  height: 40px;
  padding: 0 12px;
  border: 0;
  border-radius: 10px;
  background: none;
  color: var(--color-intaglio);
  font: inherit;
  font-size: 14px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition:
    background-color 140ms ease,
    color 140ms ease;
}
.folder svg {
  width: 16px;
  height: 16px;
}
.folder.sub {
  grid-template-columns: 16px minmax(0, 1fr) auto;
  height: 36px;
  padding-left: 30px;
  font-size: 13.5px;
  font-weight: 400;
}
.folder.sub svg {
  width: 14px;
  height: 14px;
}
.folder.soon-wait svg {
  color: var(--color-warn);
}
.folder.soon-ok svg {
  color: var(--color-ok);
}
.folder .label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.folder .n {
  color: var(--color-ink-off);
  font-size: 12px;
}
.folder[aria-current='page'] {
  background: var(--color-sheet);
  box-shadow:
    0 1px 3px rgba(42, 28, 19, 0.08),
    inset 0 0 0 1px var(--color-rule);
  color: var(--color-ink);
}
.folder[aria-current='page'] .n {
  color: var(--color-crimson);
}
.folder:focus-visible {
  outline: 2px solid var(--color-crimson);
  outline-offset: 2px;
}
.sep {
  height: 1px;
  margin: 8px 12px;
  background: var(--color-rule);
}
.main {
  min-width: 0;
}
.n {
  font-weight: 500;
}
/* Day groups (same head as To review) */
.day + .day {
  margin-top: 18px;
}
.day-head {
  position: sticky;
  top: 0;
  z-index: 3;
  /* Its own layer: Safari paints a row's photo tag (backdrop blur) above a plain sticky head. */
  transform: translateZ(0);
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin: 0 0 12px;
  padding: 10px 2px 8px;
  border-bottom: 1px solid var(--color-rule-strong);
  background: var(--color-paper);
  color: var(--color-intaglio);
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
/* While stuck, the space under the head's line is covered too (fading out), so a row sliding
   under it never shows a cut edge in that gap (owner, 20 Nov 2026). */
.day-head::after {
  content: '';
  position: absolute;
  top: 100%;
  right: 0;
  left: 0;
  height: 14px;
  margin-top: 1px;
  background: linear-gradient(var(--color-paper) 55%, transparent);
  pointer-events: none;
}
.day-head.today::after {
  margin-top: 2px;
}
.day:first-child .day-head {
  padding-top: 0;
}
.day-head .n {
  letter-spacing: 0;
}
.day-head.today {
  border-bottom: 2px solid var(--color-crimson);
  color: var(--color-crimson);
}
.day-head.today .n {
  color: var(--color-crimson);
}
/* The rows stack under the day head (z-index 3), even where Safari puts a row on its own layer. */
.rows {
  position: relative;
  z-index: 0;
  margin: 0;
  padding: 0;
}
/* The row's footer: status + what happens next on the left */
.stt {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 13.5px;
  font-weight: 600;
  white-space: nowrap;
}
.stt svg {
  width: 15px;
  height: 15px;
}
.stt.ok {
  color: var(--color-ok);
}
.stt.wait {
  color: var(--color-warn);
}
.stt.off {
  color: var(--color-ink-off);
}
.stt.bad {
  color: var(--color-crimson);
}
.nx {
  min-width: 0;
  overflow: hidden;
  padding-left: 12px;
  border-left: 1px solid var(--color-rule-strong);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.soon-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 26px;
  padding: 0 10px;
  border: 1px solid var(--color-danger-line);
  border-radius: 999px;
  background: var(--color-sheet);
  color: var(--color-crimson);
  font-size: 12.5px;
  font-weight: 500;
  white-space: nowrap;
}
.soon-pill svg {
  width: 13px;
  height: 13px;
}
.rows :deep(.soft-row.is-live) {
  border-color: color-mix(in srgb, var(--color-ok) 45%, transparent);
}
.rows :deep(.soft-row.is-live .time) {
  background: color-mix(in srgb, var(--color-ok) 14%, transparent);
  color: var(--color-ok);
}
.rows :deep(.soft-row.is-past .photo img) {
  filter: saturate(0.55);
}
@media (hover: hover) and (pointer: fine) {
  .folder:not([aria-current='page']):hover {
    background: var(--color-field-disabled);
    color: var(--color-ink);
  }
}
/* Laptop and wider: the page stays still and only the rows scroll (owner, 20 Nov 2026). */
@media (min-width: 861px) {
  .my-page {
    overflow: hidden;
    padding-bottom: 0;
  }
  .frame {
    flex: 1;
    min-height: 0;
    align-items: stretch;
  }
  .folders {
    align-self: start;
  }
  .main {
    min-height: 0;
    /* The scrollbar sits in the page's right padding, so the rows end under the Book a room button. */
    margin-right: -14px;
    padding: 0 1px 32px 0;
    overflow-y: auto;
    scrollbar-gutter: stable;
  }
}
/* iPad and smaller (owner, 20 Nov 2026): a folder column would squeeze each row into its narrow
   look, so the folders become one line over the list, search at its right, and the rows get the
   full width. Above 860px only the rows still scroll. */
@media (max-width: 1280px) {
  .frame {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto minmax(0, 1fr);
    gap: 16px;
    margin-top: 18px;
  }
  .folders {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px 16px;
  }
  .search {
    order: 2;
    flex: 1 1 190px;
    max-width: 300px;
    margin-left: auto;
  }
  .folder-list {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .folder,
  .folder.sub {
    grid-template-columns: auto auto auto;
    gap: 8px;
    height: 38px;
    padding: 0 14px;
    font-size: 13.5px;
  }
  .sep {
    display: none;
  }
}
/* Touch screens: 44px targets for a finger. */
@media (pointer: coarse) {
  .search input,
  .folder,
  .folder.sub {
    height: 44px;
  }
}
/* iPad portrait and phone: search across the full width, the folders under it. */
@media (max-width: 860px) {
  .search {
    order: 0;
    flex-basis: 100%;
    max-width: none;
    margin-left: 0;
  }
}
@media (max-width: 640px) {
  .head h1 {
    font-size: 22px;
    white-space: nowrap;
  }
  .nx {
    flex-basis: 100%;
    padding-left: 0;
    border-left: 0;
    white-space: normal;
  }
}
</style>
