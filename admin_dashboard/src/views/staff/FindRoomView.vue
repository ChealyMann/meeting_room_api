<script setup lang="ts">
// Find a room (Staff): bookable rooms as photo cards with a live line, 24 at a time; the next 24
// load when the end of the list comes into view (owner decision, 12 Nov 2026: infinite scroll).
// Search, building and type are asked of the server; "Free now" filters the rooms loaded, since
// the API cannot (more load as you scroll). Each page's day comes in one request.
import { Clock, LoaderCircle, Search, X } from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '../../api'
import { listBuildings } from '../../api/references'
import { getDaySchedule, listBookableRooms } from '../../api/staff'
import type { RoomDaySchedule, RoomListItem } from '../../api/types'
import { useLiveRefresh } from '../../composables/useLiveRefresh'
import { usePhnomPenhToday } from '../../composables/usePhnomPenhToday'
import { formatDay, phnomPenhClock } from '../../utils/time'
import OfflineNote from '../../components/list/OfflineNote.vue'
import RefreshButton from '../../components/list/RefreshButton.vue'
import RoomCard from './RoomCard.vue'
import { busySpans, nowLine, roomHours, toMin, type NowLine } from './rules'
import './staff.css'

const PAGE_SIZE = 24 // four rows of a wide screen
const DAY_CHUNK = 200 // the day endpoint's room limit (MAX_DAY_ROOMS)
const SEARCH_WAIT_MS = 250

const router = useRouter()
const today = usePhnomPenhToday()
const rooms = ref<RoomListItem[]>([])
const total = ref(0)
const days = ref<Record<number, RoomDaySchedule['items']>>({})
const loading = ref(true) // the first page of a search
const loadingMore = ref(false)
const failed = ref(false)
let pageNo = 0
let request = 0 // the newest search; older answers are dropped

const q = ref('')
const query = ref('') // q, once typing stops
const building = ref<'all' | number>('all')
const kind = ref<'all' | 'shared' | 'private'>('all')
const freeNow = ref(false)
const hasMore = computed(() => rooms.value.length < total.value)

const filters = () => ({
  q: query.value.trim() || undefined,
  is_private: kind.value === 'all' ? undefined : kind.value === 'private',
  building_id: building.value === 'all' ? undefined : building.value,
})

async function loadDays(ids: number[]) {
  for (let i = 0; i < ids.length; i += DAY_CHUNK) {
    const day = await getDaySchedule(api, today.value, ids.slice(i, i + DAY_CHUNK))
    days.value = { ...days.value, ...Object.fromEntries(day.items.map((row) => [row.room_id, row.items])) }
  }
}

/** A new search: the first page, from the top. */
async function load() {
  const mine = ++request
  loading.value = true
  failed.value = false
  try {
    const page = await listBookableRooms(api, { ...filters(), page: 1, size: PAGE_SIZE })
    if (mine !== request) return
    rooms.value = page.items
    total.value = page.total
    pageNo = 1
    if (page.items.length) await loadDays(page.items.map((r) => r.id))
  } catch {
    if (mine === request) failed.value = true
  } finally {
    if (mine === request) loading.value = false
  }
  if (mine === request) void fillIfEndNear()
}

/** The next 24, when the end of the list comes into view (or Show more is pressed). */
async function loadMore() {
  if (loading.value || loadingMore.value || !hasMore.value) return
  const mine = request
  loadingMore.value = true
  try {
    const page = await listBookableRooms(api, { ...filters(), page: pageNo + 1, size: PAGE_SIZE })
    if (mine !== request) return
    const known = new Set(rooms.value.map((r) => r.id))
    const fresh = page.items.filter((r) => !known.has(r.id)) // a room added meanwhile shifts the pages
    rooms.value = [...rooms.value, ...fresh]
    total.value = page.total
    pageNo += 1
    if (fresh.length) await loadDays(fresh.map((r) => r.id))
  } catch {
    // Show more stays; the next scroll or click tries again.
  } finally {
    loadingMore.value = false
  }
  void fillIfEndNear()
}

onMounted(() => load())
let typing: ReturnType<typeof setTimeout> | undefined
watch(q, (text) => {
  clearTimeout(typing)
  typing = setTimeout(() => (query.value = text), SEARCH_WAIT_MS)
})
watch([query, building, kind], () => load())
// Quiet refresh: the live lines of every loaded room follow new bookings with no click.
const live = useLiveRefresh(() => (loading.value || !rooms.value.length ? undefined : loadDays(rooms.value.map((r) => r.id))))

// The end of the list: a line under the cards; when it comes near the view, the next page loads.
const page = ref<HTMLElement | null>(null)
const end = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null
onMounted(() => {
  if (typeof IntersectionObserver === 'undefined') return // Show more still works
  observer = new IntersectionObserver((entries) => entries.some((e) => e.isIntersecting) && void loadMore(), {
    root: page.value,
    rootMargin: '0px 0px 600px 0px',
  })
})
watch(end, (el, old) => {
  if (old) observer?.unobserve(old)
  if (el) observer?.observe(el)
})
// The browser tells us only when the end comes INTO view. If it is still in view after a load (a
// tall screen, or "Free now" hid the new rooms), it says nothing more: so after every load, and
// when Free now changes, look again and load on while the end is near.
async function fillIfEndNear() {
  await nextTick()
  if (!end.value || !page.value || !page.value.clientHeight || !hasMore.value) return
  const view = page.value.getBoundingClientRect()
  if (end.value.getBoundingClientRect().top < view.bottom + 600) void loadMore()
}
watch(freeNow, fillIfEndNear)
onBeforeUnmount(() => {
  observer?.disconnect()
  clearTimeout(typing)
})

// Buildings for the filter: every building (the rooms come page by page). Failing hides it.
const buildings = ref<{ id: number; label: string }[]>([])
onMounted(async () => {
  try {
    buildings.value = (await listBuildings(api)).map((b) => ({ id: b.id, label: b.name_kh || b.name_en }))
  } catch {
    buildings.value = []
  }
})

const now = () => toMin(phnomPenhClock(new Date()))
const lineOf = (room: RoomListItem): NowLine =>
  nowLine(busySpans(days.value[room.id] ?? [], today.value), roomHours(room), today.value, today.value, now())

const shown = computed(() => (freeNow.value ? rooms.value.filter((r) => lineOf(r).tone === 'ok') : rooms.value))
const countText = computed(() =>
  freeNow.value
    ? `${shown.value.length} free now${hasMore.value ? ' so far' : ''}`
    : `${total.value} ${total.value === 1 ? 'room' : 'rooms'}`,
)

function clear() {
  clearTimeout(typing)
  q.value = ''
  query.value = ''
  building.value = 'all'
  kind.value = 'all'
  freeNow.value = false
}
const KINDS = [
  ['all', 'All'],
  ['shared', 'Shared'],
  ['private', 'Private'],
] as const
</script>

<template>
  <section ref="page" class="st-page find-room">
    <header class="st-head head">
      <div>
        <h1>Find a room</h1>
        <p>{{ formatDay(today) }} · {{ countText }}</p>
      </div>
      <RefreshButton :live="live" />
    </header>
    <OfflineNote :live="live" class="offline" />

    <div class="bar" role="search">
      <label class="st-search">
        <Search :size="16" aria-hidden="true" />
        <input v-model="q" type="search" placeholder="Search a room" aria-label="Search rooms" />
      </label>
      <div v-if="buildings.length > 1" class="st-seg" role="radiogroup" aria-label="Building">
        <button type="button" role="radio" data-building="all" :aria-checked="building === 'all'" :class="{ on: building === 'all' }" @click="building = 'all'">All buildings</button>
        <button
          v-for="b in buildings"
          :key="b.id"
          type="button"
          role="radio"
          class="kh"
          :data-building="b.id"
          :aria-checked="building === b.id"
          :class="{ on: building === b.id }"
          @click="building = b.id"
        >
          {{ b.label }}
        </button>
      </div>
      <div class="st-seg" role="radiogroup" aria-label="Room type">
        <button
          v-for="k in KINDS"
          :key="k[0]"
          type="button"
          role="radio"
          :data-kind="k[0]"
          :aria-checked="kind === k[0]"
          :class="{ on: kind === k[0] }"
          @click="kind = k[0]"
        >
          {{ k[1] }}
        </button>
      </div>
      <button type="button" class="st-chip free-now" :class="{ on: freeNow }" :aria-pressed="freeNow" @click="freeNow = !freeNow">
        <Clock :size="15" aria-hidden="true" />Free now
      </button>
    </div>

    <p v-if="failed" class="st-empty" role="alert"><b>The rooms could not load</b><button type="button" class="st-chip" @click="load()">Try again</button></p>
    <div v-else-if="shown.length" class="cards">
      <RoomCard
        v-for="room in shown"
        :key="room.id"
        :room="room"
        :now="lineOf(room)"
        @details="router.push({ name: 'staff-room', params: { roomId: room.id } })"
        @book="router.push({ name: 'book', params: { roomId: room.id } })"
      />
    </div>
    <div v-else-if="!loading && !hasMore" class="st-empty">
      <b>No room matches</b>
      <span>Try another building or clear the filters.</span>
      <button type="button" class="st-chip clear" @click="clear"><X :size="14" aria-hidden="true" />Clear filters</button>
    </div>

    <!-- The end of the list: it loads the next rooms as it nears the view; the button is for the keyboard. -->
    <div v-if="!failed && !loading && hasMore" ref="end" class="more-row">
      <span v-if="loadingMore" class="loading-more"><LoaderCircle :size="16" class="spin" aria-hidden="true" />Loading more rooms</span>
      <button v-else type="button" class="st-chip more" @click="loadMore">Show more rooms</button>
    </div>
  </section>
</template>

<style scoped>
.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.offline {
  margin: 18px 0 0;
}
.bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin: 26px 0 30px;
}
.free-now svg {
  color: var(--color-ok);
}
.free-now.on svg {
  color: var(--color-crimson);
}
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 30px 24px;
}
.more-row {
  display: flex;
  justify-content: center;
  min-height: 40px;
  margin-top: 28px;
}
.loading-more {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--color-ink-off);
  font-size: 13.5px;
}
.spin {
  animation: spin 800ms linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@media (max-width: 760px) {
  .cards {
    grid-template-columns: minmax(0, 1fr);
  }
}
@media (prefers-reduced-motion: reduce) {
  .spin {
    animation-duration: 2s;
  }
}
</style>
