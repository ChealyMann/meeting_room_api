<script setup lang="ts">
// Find a room (Staff): bookable rooms as photo cards with a live line, 24 at a time; the next 24
// load when the end of the list comes into view (owner decision, 12 Nov 2026: infinite scroll).
// Filters are chips (owner pick, 13 Nov 2026): When (one day or day to day, and a time), People,
// Office, Equipment, and Shared / Private. All of them are asked of the server; with a time, it
// sends only rooms free then on every day. Each page's day comes in one request.
import { Building2, CalendarDays, LoaderCircle, Monitor, Search, Users, X } from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '../../api'
import { listBuildings, listEquipment, listOffices } from '../../api/references'
import { getDaySchedule, listBookableRooms } from '../../api/staff'
import type { RoomDaySchedule, RoomListItem } from '../../api/types'
import { useLiveRefresh } from '../../composables/useLiveRefresh'
import { usePhnomPenhToday } from '../../composables/usePhnomPenhToday'
import { useSessionStore } from '../../stores/session'
import { phnomPenhClock } from '../../utils/time'
import OfflineNote from '../../components/list/OfflineNote.vue'
import RefreshButton from '../../components/list/RefreshButton.vue'
import { SEARCH_FROM } from '../../components/list/SearchPicker.vue'
import RoomCard from './RoomCard.vue'
import FilterChip from './find/FilterChip.vue'
import PlaceList, { type PlaceBuilding, type PlaceOffice } from './find/PlaceList.vue'
import WhenPicker from './find/WhenPicker.vue'
import { anyTime, bookQuery, countLine, datesOf, freeQuery, hasTime, isRange, PICK_DAYS, whenLabel, whenSet, type When } from './find/when'
import { busySpans, nowLine, roomHours, toMin, toTime, daysFrom, type NowLine } from './rules'
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

// --- Filters ---------------------------------------------------------------------------
const q = ref('')
const query = ref('') // q, once typing stops
const kind = ref<'all' | 'shared' | 'private'>('all')
const pickDays = computed(() => daysFrom(today.value, PICK_DAYS))
const firstDay = computed(() => pickDays.value[0]!)
const when = ref<When>(anyTime(firstDay.value))
const people = ref(0)
const office = ref<'all' | number>('all')
const building = ref<'all' | number>('all')
const equipment = ref<number[]>([])
const hasMore = computed(() => rooms.value.length < total.value)

const filters = () => ({
  q: query.value.trim() || undefined,
  is_private: kind.value === 'all' ? undefined : kind.value === 'private',
  location_id: office.value === 'all' ? undefined : office.value,
  building_id: building.value === 'all' ? undefined : building.value,
  min_capacity: people.value || undefined,
  equipment_ids: equipment.value,
  ...freeQuery(when.value, pickDays.value),
})

// The day the live lines are about: the one day picked, or today.
const lineDay = computed(() => (isRange(when.value) ? today.value : when.value.first))

async function loadDays(ids: number[]) {
  const day = lineDay.value
  for (let i = 0; i < ids.length; i += DAY_CHUNK) {
    const answer = await getDaySchedule(api, day, ids.slice(i, i + DAY_CHUNK))
    days.value = { ...days.value, ...Object.fromEntries(answer.items.map((row) => [row.room_id, row.items])) }
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
    days.value = {}
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
// Any filter change is a new search; the same filters again (a chip set back) are not.
watch(() => JSON.stringify(filters()), () => load())
// Another day with no time: the same rooms, that day's bookings for their lines.
watch(lineDay, () => {
  if (loading.value || !rooms.value.length) return
  days.value = {}
  void loadDays(rooms.value.map((r) => r.id))
})
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
// tall screen), it says nothing more: so after every load, look again and load on while it is near.
async function fillIfEndNear() {
  await nextTick()
  if (!end.value || !page.value || !page.value.clientHeight || !hasMore.value) return
  const view = page.value.getBoundingClientRect()
  if (end.value.getBoundingClientRect().top < view.bottom + 600) void loadMore()
}
onBeforeUnmount(() => {
  observer?.disconnect()
  clearTimeout(typing)
})

// Offices, buildings and equipment for the chips. Each list is read once; a failure hides its chip.
const offices = ref<PlaceOffice[]>([])
const buildings = ref<PlaceBuilding[]>([])
const equipmentList = ref<{ id: number; name: string }[]>([])
onMounted(async () => {
  const [o, b, e] = await Promise.allSettled([listOffices(api), listBuildings(api), listEquipment(api)])
  if (o.status === 'fulfilled')
    offices.value = o.value
      .filter((x) => x.is_active)
      .map((x) => ({ id: x.id, en: x.name_en, kh: x.name_kh ?? '', province: x.province ?? null }))
  if (b.status === 'fulfilled')
    buildings.value = b.value
      .filter((x) => x.is_active)
      .map((x) => ({ id: x.id, office: x.location_id, en: x.name_en, kh: x.name_kh ?? '' }))
  if (e.status === 'fulfilled') equipmentList.value = e.value.filter((x) => x.is_active).map((x) => ({ id: x.id, name: x.name }))
})
const showPlace = computed(() => offices.value.length > 1 || buildings.value.length > 1)
/** The offices in the user's province come first in the list. */
const myProvince = computed(() => useSessionStore().user?.province ?? null)
function pickOffice(id: 'all' | number) {
  office.value = id
  building.value = 'all'
}
/** One click picks; a building picks its office too. */
function pickPlace(o: 'all' | number, b: 'all' | number) {
  office.value = o
  building.value = b
}
const placeLabel = computed(() => {
  const o = offices.value.find((x) => x.id === office.value)
  const b = buildings.value.find((x) => x.id === building.value)
  if (b) return o ? `${o.en.replace(/ Branch$/, '')} · ${b.en}` : b.en
  if (o) return o.en
  return offices.value.length > 1 ? 'Office' : 'Building'
})
const equipmentLabel = computed(() =>
  equipment.value.length ? equipmentList.value.filter((e) => equipment.value.includes(e.id)).map((e) => e.name).join(', ') || 'Equipment' : 'Equipment',
)
// Equipment: a search box for a long list, and what is picked as tags with × (owner, 20 Nov 2026).
const equipmentQuery = ref('')
const shownEquipment = computed(() => {
  const q = equipmentQuery.value.trim().toLowerCase()
  return q ? equipmentList.value.filter((e) => e.name.toLowerCase().includes(q)) : equipmentList.value
})
const pickedEquipment = computed(() => equipmentList.value.filter((e) => equipment.value.includes(e.id)))
function toggleEquipment(id: number, on: boolean) {
  equipment.value = on ? [...equipment.value, id] : equipment.value.filter((x) => x !== id)
}
const PEOPLE = [2, 4, 8, 12, 20, 50, 100]

// --- Lines and counts ------------------------------------------------------------------
const now = () => toMin(phnomPenhClock(new Date()))
function lineOf(room: RoomListItem): NowLine {
  const w = when.value
  const n = datesOf(w, pickDays.value).length
  // With a time the server sent only rooms free then on every day.
  if (hasTime(w)) return { tone: 'ok', text: isRange(w) ? `Free all ${n} days` : `Free ${toTime(w.start!)}–${toTime(w.end!)}` }
  if (isRange(w)) return { tone: 'off', text: 'Pick a time' }
  const busy = busySpans(days.value[room.id] ?? [], w.first)
  const hours = roomHours(room)
  if (w.first === today.value) return nowLine(busy, hours, today.value, today.value, now())
  if (!busy.length) return { tone: 'ok', text: 'Free all day' }
  const booked = busy.reduce((sum, s) => sum + s.b - s.a, 0)
  if (booked >= hours.close - hours.open) return { tone: 'alert', text: 'Full' }
  return { tone: 'off', text: `${busy.length} ${busy.length === 1 ? 'booking' : 'bookings'} that day` }
}
const count = computed(() => countLine(when.value, pickDays.value, today.value, total.value))
const anySet = computed(
  () =>
    !!query.value.trim() ||
    kind.value !== 'all' ||
    whenSet(when.value, firstDay.value) ||
    !!people.value ||
    office.value !== 'all' ||
    building.value !== 'all' ||
    equipment.value.length > 0,
)

function clear() {
  clearTimeout(typing)
  q.value = ''
  query.value = ''
  kind.value = 'all'
  when.value = anyTime(firstDay.value)
  people.value = 0
  office.value = 'all'
  building.value = 'all'
  equipment.value = []
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
        <p class="count-line"><b :class="{ free: count.free }">{{ count.count }}</b>{{ count.rest }}</p>
      </div>
      <RefreshButton :live="live" />
    </header>
    <OfflineNote :live="live" class="offline" />

    <div class="bar" role="search">
      <label class="st-search">
        <Search :size="16" aria-hidden="true" />
        <input v-model="q" type="search" placeholder="Search a room" aria-label="Search rooms" />
      </label>

      <FilterChip
        class="chip-when"
        :label="whenLabel(when, pickDays, today)"
        :set="whenSet(when, firstDay)"
        wide
        @clear="when = anyTime(firstDay)"
      >
        <template #icon><CalendarDays :size="16" aria-hidden="true" /></template>
        <WhenPicker v-model="when" :days="pickDays" :today="today" :now="now()" />
      </FilterChip>

      <FilterChip class="chip-people" :label="people ? `${people}+ people` : 'People'" :set="!!people" @clear="people = 0">
        <template #icon><Users :size="16" aria-hidden="true" /></template>
        <span class="box-lbl">How many people?</span>
        <div class="stepper">
          <button type="button" aria-label="Fewer people" :disabled="!people" @click="people = Math.max(0, people - 1)">−</button>
          <output aria-live="polite">{{ people || 'Any' }}</output>
          <button type="button" aria-label="More people" @click="people += 1">+</button>
        </div>
        <div class="quick">
          <button v-for="n in PEOPLE" :key="n" type="button" :data-people="n" :class="{ on: people === n }" @click="people = n">{{ n }}+</button>
        </div>
      </FilterChip>

      <FilterChip
        v-if="showPlace"
        class="chip-place"
        :label="placeLabel"
        :set="office !== 'all' || building !== 'all'"
        @clear="pickOffice('all')"
      >
        <template #icon><Building2 :size="16" aria-hidden="true" /></template>
        <PlaceList :offices="offices" :buildings="buildings" :office="office" :building="building" :mine="myProvince" @pick="pickPlace" />
      </FilterChip>

      <FilterChip v-if="equipmentList.length" class="chip-equipment" :label="equipmentLabel" :set="equipment.length > 0" @clear="equipment = []">
        <template #icon><Monitor :size="16" aria-hidden="true" /></template>
        <span class="box-lbl">The room must have</span>
        <label v-if="equipmentList.length >= SEARCH_FROM" class="pl-search">
          <Search :size="16" aria-hidden="true" />
          <input v-model="equipmentQuery" type="search" placeholder="Search equipment" aria-label="Search equipment" />
        </label>
        <p v-if="pickedEquipment.length" class="eq-tags">
          <span v-for="e in pickedEquipment" :key="e.id" class="eq-tag">
            {{ e.name }}<button type="button" :aria-label="`Remove ${e.name}`" @click="toggleEquipment(e.id, false)"><X :size="13" aria-hidden="true" /></button>
          </span>
          <button type="button" class="eq-clear" @click="equipment = []">Clear</button>
        </p>
        <p v-if="!shownEquipment.length" class="eq-none">No equipment matches "{{ equipmentQuery.trim() }}"</p>
        <div class="checks">
          <label v-for="e in shownEquipment" :key="e.id">
            <input type="checkbox" :data-equipment="e.id" :checked="equipment.includes(e.id)" @change="toggleEquipment(e.id, ($event.target as HTMLInputElement).checked)" />
            {{ e.name }}
          </label>
        </div>
      </FilterChip>

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
      <button v-if="anySet" type="button" class="clear-all" @click="clear">Clear filters</button>
    </div>

    <p v-if="failed" class="st-empty" role="alert"><b>The rooms could not load</b><button type="button" class="st-chip" @click="load()">Try again</button></p>
    <div v-else-if="rooms.length" class="cards">
      <RoomCard
        v-for="room in rooms"
        :key="room.id"
        :room="room"
        :now="lineOf(room)"
        @details="router.push({ name: 'staff-room', params: { roomId: room.id } })"
        @book="router.push({ name: 'book', params: { roomId: room.id }, query: bookQuery(when, pickDays) })"
      />
    </div>
    <div v-else-if="!loading && !hasMore" class="st-empty">
      <b>{{ hasTime(when) ? (isRange(when) ? 'No room is free on all these days' : 'No room is free then') : 'No room matches' }}</b>
      <span>{{ hasTime(when) ? 'Try another time, fewer days, or fewer filters.' : 'Try other filters, or clear them.' }}</span>
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
.count-line b {
  color: var(--color-ink);
  font-weight: 500;
}
.count-line b.free {
  color: var(--color-ok);
}.offline {
  margin: 18px 0 0;
}
.bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin: 26px 0 30px;
}
.box-lbl {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-intaglio);
}
.stepper {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.stepper button {
  width: 36px;
  height: 36px;
  border: 1px solid var(--color-rule-strong);
  border-radius: 10px;
  background: var(--color-sheet);
  color: var(--color-ink);
  font: inherit;
  font-size: 16px;
  cursor: pointer;
  user-select: none;
}
.stepper button:disabled {
  opacity: 0.45;
  cursor: default;
}
.stepper output {
  min-width: 48px;
  font-size: 16px;
  font-weight: 600;
  text-align: center;
}
.quick {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.quick button {
  padding: 5px 12px;
  border: 1px solid var(--color-rule-strong);
  border-radius: 999px;
  background: var(--color-sheet);
  color: var(--color-ink);
  font: inherit;
  font-size: 12.5px;
  cursor: pointer;
}
.quick button.on {
  border-color: var(--color-crimson-fill);
  background: var(--color-crimson-fill);
  color: #fff;
}
.checks {
  display: grid;
  gap: 2px;
  max-height: 260px;
  overflow: auto;
}
.pl-search {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 38px;
  padding: 0 12px;
  border: 1px solid var(--color-rule-strong);
  border-radius: 10px;
  background: var(--color-sheet);
  color: var(--color-ink-off);
}
.pl-search:focus-within {
  border-color: var(--color-crimson);
  box-shadow: 0 0 0 3px rgba(153, 27, 27, 0.12);
}
.pl-search input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  background: none;
  color: var(--color-ink);
  font: inherit;
  font-size: 13.5px;
}
.eq-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin: 0;
}
.eq-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 6px 3px 10px;
  border-radius: 999px;
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
  font-size: 12px;
  font-weight: 500;
}
.eq-tag button {
  display: grid;
  place-items: center;
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  cursor: pointer;
}
.eq-clear {
  margin-left: auto;
  padding: 2px 4px;
  border: 0;
  background: none;
  color: var(--color-crimson);
  font: inherit;
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
}
.eq-none {
  margin: 0;
  color: var(--color-ink-off);
  font-size: 13px;
}
.checks label {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 4px;
  border-radius: 8px;
  font-size: 13.5px;
  cursor: pointer;
}
.checks input {
  width: 16px;
  height: 16px;
  accent-color: var(--color-crimson-fill);
}
.clear-all {
  padding: 4px;
  border: 0;
  background: none;
  color: var(--color-intaglio);
  font: inherit;
  font-size: 13px;
  text-decoration: underline;
  text-underline-offset: 3px;
  cursor: pointer;
}
@media (hover: hover) and (pointer: fine) {
  .checks label:hover {
    background: var(--color-field-disabled);
  }
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
