<script setup lang="ts">
// Find a room (Staff): every bookable room as a photo card with a live line, one request for
// every room's day, and filters on the rooms already loaded (search, building, type, free now).
import { Search, X } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '../../api'
import { getDaySchedule, listBookableRooms } from '../../api/staff'
import type { RoomDaySchedule, RoomListItem } from '../../api/types'
import { usePhnomPenhToday } from '../../composables/usePhnomPenhToday'
import { formatDay, phnomPenhClock } from '../../utils/time'
import RoomCard from './RoomCard.vue'
import { busySpans, matchesWords, nowLine, roomHours, toMin, type NowLine } from './rules'
import './staff.css'

const router = useRouter()
const today = usePhnomPenhToday()
const rooms = ref<RoomListItem[]>([])
const days = ref<Record<number, RoomDaySchedule['items']>>({})
const loading = ref(true)
const failed = ref(false)

const q = ref('')
const building = ref<'all' | number>('all')
const kind = ref<'all' | 'shared' | 'private'>('all')
const freeNow = ref(false)

async function load() {
  loading.value = true
  failed.value = false
  try {
    const page = await listBookableRooms(api, { page: 1, size: 100 })
    rooms.value = page.items
    if (page.items.length) {
      const day = await getDaySchedule(api, today.value, page.items.map((r) => r.id))
      days.value = Object.fromEntries(day.items.map((row) => [row.room_id, row.items]))
    }
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}
onMounted(load)

const now = () => toMin(phnomPenhClock(new Date()))
const lineOf = (room: RoomListItem): NowLine =>
  nowLine(busySpans(days.value[room.id] ?? [], today.value), roomHours(room), today.value, today.value, now())

const buildings = computed(() => {
  const seen = new Map<number, string>()
  for (const r of rooms.value) seen.set(r.building.id, r.building.name_kh || r.building.name_en)
  return [...seen.entries()].map(([id, label]) => ({ id, label }))
})

const shown = computed(() =>
  rooms.value.filter((r) => {
    if (!matchesWords(`${r.name_en} ${r.name_kh} ${r.short_desc ?? ''} ${r.building.name_en} ${r.building.name_kh}`, q.value)) return false
    if (building.value !== 'all' && r.building.id !== building.value) return false
    if (kind.value === 'shared' && r.is_private) return false
    if (kind.value === 'private' && !r.is_private) return false
    if (freeNow.value && lineOf(r).tone !== 'ok') return false
    return true
  }),
)

function clear() {
  q.value = ''
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
  <section class="st-page find-room">
    <header class="st-head">
      <h1>Find a room</h1>
      <p>{{ formatDay(today) }} · {{ shown.length }} {{ shown.length === 1 ? 'room' : 'rooms' }}</p>
    </header>

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
        <i class="dot" aria-hidden="true" />Free now
      </button>
    </div>

    <p v-if="failed" class="st-empty" role="alert"><b>The rooms could not load</b><button type="button" class="st-chip" @click="load">Try again</button></p>
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
    <div v-else-if="!loading" class="st-empty">
      <b>No room matches</b>
      <span>Try another building or clear the filters.</span>
      <button type="button" class="st-chip clear" @click="clear"><X :size="14" aria-hidden="true" />Clear filters</button>
    </div>
  </section>
</template>

<style scoped>
.bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin: 26px 0 30px;
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-ok);
}
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 30px 24px;
}
@media (max-width: 760px) {
  .cards {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
