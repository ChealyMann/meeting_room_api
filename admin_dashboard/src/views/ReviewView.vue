<script setup lang="ts">
// The Pitika's queue (spec docs/superpowers/specs/2026-11-05-pitika-review-design.md): the
// bookings of their province waiting for them, grouped by urgency, each with the room's photo,
// what to check and the row bar ("gap is you"). Details are loaded per booking for the labels.
import { CalendarDays, CircleAlert, Monitor, TriangleAlert, User, Users, Utensils, EyeOff } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { api } from '../api'
import { getBooking, listPitikaBookingPage } from '../api/bookings'
import { listAllRooms } from '../api/references'
import type { BookingDetail, BookingListItem } from '../api/types'
import BaseButton from '../components/base/BaseButton.vue'
import EmptyState from '../components/list/EmptyState.vue'
import ListSearch from '../components/list/ListSearch.vue'
import TableSkeleton from '../components/list/TableSkeleton.vue'
import ProcessBar from '../components/ProcessBar.vue'
import RoomPhoto from '../components/RoomPhoto.vue'
import { usePhnomPenhToday } from '../composables/usePhnomPenhToday'
import { useResourceList } from '../composables/useResourceList'
import { checkLabels, groupByUrgency, rowSteps, startsIn } from '../utils/reviewQueue'
import { formatDay } from '../utils/time'

const { list, result, loading, error, load } = useResourceList<BookingListItem>(
  { q: 'string' },
  // Every waiting booking on one page: the queue is short, and it is grouped, not paged.
  (params) => listPitikaBookingPage(api, { status: 'PENDING_PITIKA', q: params.q as string | undefined, page: 1, size: 100 }),
  { activeFilter: false },
)
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

// Room cover photos, by room id (rooms are loaded once).
const covers = ref<Record<number, { url: string; thumbnail_url: string } | null>>({})
onMounted(async () => {
  try {
    const rooms = await listAllRooms(api)
    covers.value = Object.fromEntries(rooms.map((r) => [r.id, r.cover_photo ?? null]))
  } catch {
    // no photos: the rows show the plain tile
  }
})

const today = usePhnomPenhToday()
// "Starts in …" counts down; it is worked out again every minute.
const now = ref(new Date())
let tick: ReturnType<typeof setInterval> | undefined
onMounted(() => (tick = setInterval(() => (now.value = new Date()), 60_000)))
onBeforeUnmount(() => clearInterval(tick))

const groups = computed(() => groupByUrgency(items.value, today.value))
const count = computed(() => `${String(items.value.length).padStart(3, '0')} waiting`)

const hhmm = (time: string) => time.slice(0, 5)
const whenText = (b: BookingListItem) => (b.first_session.date === today.value ? `Today, ${formatDay(b.first_session.date)}` : formatDay(b.first_session.date))
</script>

<template>
  <div class="places-page review">
    <div class="page-head">
      <h1>To review</h1>
      <span v-if="result" class="mono count">{{ count }}</span>
    </div>
    <p class="sub">
      Bookings of rooms in your province waiting for your decision, the most urgent first. Approving also approves the food
      and IT.
    </p>

    <div class="filters" role="search">
      <ListSearch
        :value="(list.filters.value.q as string | undefined) ?? ''"
        label="Search bookings"
        placeholder="Search title, reference or booker"
        @search="list.set({ q: $event })"
      />
    </div>

    <div class="queue">
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
        :filtered="!!list.filters.value.q"
        :title="list.filters.value.q ? 'No bookings match' : 'Nothing to review'"
        :text="list.filters.value.q ? `Nothing waiting matches “${list.filters.value.q}”.` : 'New bookings in your province show here.'"
      >
        <BaseButton v-if="list.filters.value.q" @click="list.reset()">Clear search</BaseButton>
      </EmptyState>
      <template v-else-if="result">
        <section v-for="group in groups" :key="group.key" :aria-labelledby="`group-${group.key}`">
          <div class="group-head" :class="group.key">
            <h2 :id="`group-${group.key}`">{{ group.label }}</h2>
            <span class="n mono">{{ group.items.length }}</span>
            <p v-if="group.hint">{{ group.hint }}</p>
          </div>
          <ul class="rows">
            <li v-for="b in group.items" :key="b.id" class="row" :data-booking="b.id">
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
              </div>
            </li>
          </ul>
        </section>
      </template>
    </div>
  </div>
</template>

<style scoped src="./listPage.css"></style>

<style scoped>
.sub {
  margin: 4px 0 0;
  max-width: 75ch;
  font-size: 13px;
  color: var(--color-intaglio);
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
.row:hover {
  background: var(--color-row-hover);
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
