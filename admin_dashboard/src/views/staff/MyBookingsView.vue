<script setup lang="ts">
// My bookings (Staff): "Coming up" and "Past & cancelled", each card with a date block, the room
// photo, title, time, room and status (no door pass button: owner pick, 13 Nov 2026). A card opens its details;
// ?booking=<id> opens them too. Finding one (owner pick, 16 Nov 2026, look A): a search box (title,
// room or reference), status chips on Coming up (All · Waiting · Confirmed), and Coming up grouped
// by Today, Tomorrow, Later this week and Later. A card shows its next session, not its first,
// and "Happening now" while one is under way.
import { Plus, Search } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '../../api'
import { listBookableRooms, listMyBookings } from '../../api/staff'
import type { BookingDetail, BookingListItem } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import EmptyState from '../../components/list/EmptyState.vue'
import OfflineNote from '../../components/list/OfflineNote.vue'
import RefreshButton from '../../components/list/RefreshButton.vue'
import RoomPhoto from '../../components/RoomPhoto.vue'
import { useLiveRefresh } from '../../composables/useLiveRefresh'
import { statusLabel } from '../../utils/bookingLabels'
import { addDays, phnomPenhClock, phnomPenhDate } from '../../utils/time'
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
const WAITING = ['PENDING_PITIKA', 'PENDING_OWNER', 'SETUP_IN_PROGRESS']
/** The session the card shows: the next one not ended, else the first. */
const sessionOf = (b: BookingListItem) => b.next_session ?? b.first_session
const startOf = (b: BookingListItem) => `${sessionOf(b).date} ${sessionOf(b).start_time}`

const query = ref('')
const matches = (b: BookingListItem) => {
  const q = query.value.trim().toLowerCase()
  return !q || [b.meeting_title, b.room.name_en, b.reference_code].some((text) => text.toLowerCase().includes(q))
}
const soon = computed(() => items.value.filter((b) => !PAST.includes(b.display_status) && matches(b)).sort((x, y) => (startOf(x) < startOf(y) ? -1 : 1)))
const past = computed(() => items.value.filter((b) => PAST.includes(b.display_status) && matches(b)).sort((x, y) => (startOf(x) < startOf(y) ? 1 : -1)))

type Status = 'all' | 'wait' | 'ok'
const status = ref<Status>('all')
const isWaiting = (b: BookingListItem) => WAITING.includes(b.display_status)
const chips = computed(() => [
  { id: 'all' as const, label: 'All', count: soon.value.length },
  { id: 'wait' as const, label: 'Waiting', count: soon.value.filter(isWaiting).length },
  { id: 'ok' as const, label: 'Confirmed', count: soon.value.filter((b) => !isWaiting(b)).length },
])
const shownSoon = computed(() => soon.value.filter((b) => status.value === 'all' || (status.value === 'wait') === isWaiting(b)))

/** Coming up by day of the next session: Today, Tomorrow, Later this week (to 6 days), Later. */
const groups = computed(() => {
  const today = phnomPenhDate(now.value)
  const tomorrow = addDays(today, 1)
  const week = addDays(today, 6)
  const day = (b: BookingListItem) => sessionOf(b).date
  return [
    { title: 'Today', list: shownSoon.value.filter((b) => day(b) <= today) },
    { title: 'Tomorrow', list: shownSoon.value.filter((b) => day(b) === tomorrow) },
    { title: 'Later this week', list: shownSoon.value.filter((b) => day(b) > tomorrow && day(b) <= week) },
    { title: 'Later', list: shownSoon.value.filter((b) => day(b) > week) },
  ].filter((g) => g.list.length)
})
/** A session under way right now (only a confirmed booking meets). */
const isLive = (b: BookingListItem) => {
  const s = b.next_session
  const clock = phnomPenhClock(now.value)
  return b.display_status === 'CONFIRMED' && !!s && s.date === phnomPenhDate(now.value) && s.start_time.slice(0, 5) <= clock && clock < s.end_time.slice(0, 5)
}

/** `quiet`: the live refresh — what is shown stays when it fails. */
async function loadList(quiet = false) {
  try {
    items.value = (await listMyBookings(api, { page: 1, size: 100 })).items
    now.value = new Date()
    failed.value = false
  } catch (err) {
    // Quiet: what is shown stays; the button learns why (the server's own error, so a
    // "too many requests" is seen as one).
    if (quiet) throw err
    failed.value = true
  } finally {
    loaded.value = true
  }
}
const live = useLiveRefresh(() => loadList(true))

onMounted(async () => {
  await loadList()
  // Photos are a nice extra: without them the cards still work.
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
/** What the list shows: Coming up by day, or Past as one list. */
const sections = computed(() => (tab.value === 'soon' ? groups.value : [{ title: '', list: past.value }]))
const coverOf = (roomId: number) => covers.value[roomId] ?? null
const time = (b: BookingListItem) => `${sessionOf(b).start_time.slice(0, 5)}–${sessionOf(b).end_time.slice(0, 5)}`
const tone = (status: string) =>
  status === 'CONFIRMED' || status === 'COMPLETED' ? 'ok' : status === 'REJECTED' || status === 'CANCELLED' ? 'off' : 'wait'
</script>

<template>
  <section class="st-page my-page">
    <header class="st-head head">
      <h1>My bookings</h1>
      <div class="head-actions">
        <RefreshButton :live="live" />
        <BaseButton variant="primary" @click="router.push({ name: 'find-room' })"><Plus aria-hidden="true" />Book a room</BaseButton>
      </div>
    </header>

    <OfflineNote :live="live" class="offline" />
    <div class="bar">
      <div class="st-seg tabs" role="tablist" aria-label="Bookings">
        <button type="button" role="tab" :aria-selected="tab === 'soon'" :class="{ on: tab === 'soon' }" @click="tab = 'soon'">
          Coming up <span class="n">{{ soon.length }}</span>
        </button>
        <button type="button" role="tab" :aria-selected="tab === 'past'" :class="{ on: tab === 'past' }" @click="tab = 'past'">
          Past &amp; cancelled <span class="n">{{ past.length }}</span>
        </button>
      </div>
      <div v-if="tab === 'soon'" class="chips" role="group" aria-label="Status">
        <button v-for="c in chips" :key="c.id" type="button" class="chip" :class="c.id" :aria-pressed="status === c.id" @click="status = c.id">
          <i v-if="c.id !== 'all'" aria-hidden="true" />{{ c.label }} <span class="n">{{ c.count }}</span>
        </button>
      </div>
      <label class="search">
        <Search aria-hidden="true" />
        <input v-model="query" type="search" placeholder="Search title, room or reference" aria-label="Search my bookings" />
      </label>
    </div>

    <p v-if="failed" class="st-empty" role="alert"><b>Your bookings could not load</b></p>
    <EmptyState v-else-if="loaded && query.trim() && !(tab === 'soon' ? shownSoon : past).length" title="Nothing found" :text="`No bookings match “${query.trim()}”.`">
      <BaseButton @click="query = ''">Clear search</BaseButton>
    </EmptyState>
    <EmptyState v-else-if="loaded && tab === 'soon' && !soon.length" title="Nothing coming up" text="Book a room and it shows here.">
      <BaseButton variant="primary" @click="router.push({ name: 'find-room' })">Book a room</BaseButton>
    </EmptyState>
    <EmptyState v-else-if="loaded && tab === 'soon' && !shownSoon.length" title="Nothing here" :text="status === 'wait' ? 'No booking is waiting for approval.' : 'No confirmed booking coming up.'">
      <BaseButton @click="status = 'all'">Show all</BaseButton>
    </EmptyState>
    <EmptyState v-else-if="loaded && tab === 'past' && !past.length" title="Nothing here yet" text="Past, cancelled and not approved bookings show here." />
    <template v-else>
      <section v-for="g in sections" :key="g.title" class="group">
        <h2 v-if="g.title">{{ g.title }}</h2>
        <ul class="list">
          <li v-for="b in g.list" :key="b.id">
            <article class="bk-card" :class="{ 'is-live': isLive(b) }" tabindex="0" :aria-label="`${b.meeting_title}, details`" @click="openBooking(b.id)" @keydown.enter="openBooking(b.id)">
              <span class="date" :class="{ dim: tab === 'past' }">
                <small>{{ weekdayShort(sessionOf(b).date).toUpperCase() }}</small><b>{{ dateNumber(sessionOf(b).date) }}</b
                ><small>{{ monthShort(sessionOf(b).date).toUpperCase() }}</small>
              </span>
              <span class="ph"><RoomPhoto :path="coverOf(b.room.id)" :alt="b.room.name_en" /></span>
              <span class="txt">
                <h3>{{ b.meeting_title }}</h3>
                <span class="meta">
                  <span class="mono">{{ time(b) }}</span><span v-if="b.session_count > 1"> +{{ b.session_count - 1 }} more</span> · {{ b.room.name_en }}
                </span>
                <span v-if="isLive(b)" class="now-line"><i aria-hidden="true" />Now · until {{ b.next_session!.end_time.slice(0, 5) }}</span>
              </span>
              <span class="pill" :class="tone(b.display_status)">{{ statusLabel(b.display_status) }}</span>
            </article>
          </li>
        </ul>
      </section>
    </template>

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
.head-actions {
  display: flex;
  gap: 8px;
}
.offline {
  margin: 18px 0 0;
}
/* The filter row (look A): when, status chips, search. */
.bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin: 22px 0 6px;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 12px;
  border: 1px solid var(--color-rule);
  border-radius: 999px;
  background: var(--color-sheet);
  color: var(--color-intaglio);
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}
.chip i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}
.chip.wait i {
  background: var(--color-warn);
}
.chip.ok i {
  background: var(--color-ok);
}
.chip[aria-pressed='true'] {
  border-color: var(--color-ink);
  background: var(--color-paper);
  color: var(--color-ink);
}
.chip:focus-visible {
  outline: 2px solid var(--color-ink);
  outline-offset: 2px;
}
.search {
  position: relative;
  flex: 1;
  min-width: 200px;
  max-width: 320px;
  margin-left: auto;
}
.search :deep(svg.lucide) {
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
  height: 36px;
  padding: 0 12px 0 34px;
  border: 1px solid var(--color-rule);
  border-radius: 10px;
  outline: none;
  background: var(--color-sheet);
  color: var(--color-ink);
  font: inherit;
  font-size: 13px;
}
.search input:focus {
  border-color: var(--color-ink);
}
.n {
  margin-left: 2px;
  color: var(--color-ink-off);
  font-size: 12px;
}
/* Coming up by day: a small heading over each group. */
.group {
  margin-top: 18px;
}
.group h2 {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-ink-off);
}
.list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.bk-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px 12px 12px;
  border-radius: 18px;
  background: var(--color-sheet);
  box-shadow: 0 1px 3px rgba(30, 22, 17, 0.06);
  cursor: pointer;
  transition: box-shadow 160ms ease, transform 160ms var(--ease-out-quint);
}
.bk-card:active {
  transform: scale(0.995);
}
.bk-card:focus-visible {
  outline: 2px solid var(--color-ink);
  outline-offset: 2px;
}
.date {
  display: grid;
  flex: none;
  align-content: center;
  justify-items: center;
  width: 64px;
  height: 68px;
  border-radius: 12px;
  background: var(--color-paper);
}
.date small {
  color: var(--color-crimson);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.06em;
}
.date small:last-child,
.date.dim small {
  color: var(--color-intaglio);
}
.date b {
  font-size: 22px;
  font-weight: 600;
  line-height: 1.1;
}
.ph {
  flex: none;
  width: 100px;
  height: 68px;
  overflow: hidden;
  border-radius: 12px;
}
.ph :deep(.room-photo),
.ph :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.txt {
  display: grid;
  flex: 1;
  gap: 2px;
  min-width: 0;
}
.txt h3 {
  overflow: hidden;
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.meta {
  color: var(--color-intaglio);
  font-size: 13px;
}
.pill {
  flex: none;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
}
.pill.ok {
  background: color-mix(in srgb, var(--color-ok) 14%, transparent);
  color: var(--color-ok);
}
.pill.wait {
  background: var(--color-saved-tint);
  color: var(--color-warn);
}
.pill.off {
  background: var(--color-field-disabled);
  color: var(--color-intaglio);
}
/* A meeting under way (owner pick, 16 Nov 2026, look C): a green bar on the left, and
   "Now · until 18:00" under the room; the status pill stays as it is. */
.bk-card.is-live {
  position: relative;
  overflow: hidden;
}
.bk-card.is-live::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: var(--color-ok);
}
.now-line {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-ok);
  font-size: 12.5px;
  font-weight: 500;
}
.now-line i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-ok);
  animation: live-pulse 1.6s ease-in-out infinite;
}
@keyframes live-pulse {
  50% {
    opacity: 0.35;
  }
}
@media (hover: hover) and (pointer: fine) {
  .bk-card:hover {
    box-shadow: 0 6px 20px rgba(30, 22, 17, 0.08);
  }
}
@media (max-width: 640px) {
  .search {
    flex-basis: 100%;
    max-width: none;
    margin-left: 0;
  }
  .ph,
  .pill {
    display: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .now-line i {
    animation: none;
  }
  .bk-card {
    transition: none;
  }
}
</style>
