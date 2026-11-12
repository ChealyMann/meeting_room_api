<script setup lang="ts">
// My bookings (Staff): "Coming up" and "Past & cancelled", each card with a date block, the room
// photo, title, time, room and status; "Door pass" on a confirmed one. A card opens its details;
// ?booking=<id> opens them too.
import { KeyRound, Plus } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '../../api'
import { listBookableRooms, listMyBookings } from '../../api/staff'
import type { BookingDetail, BookingListItem } from '../../api/types'
import RoomPhoto from '../../components/RoomPhoto.vue'
import { statusLabel } from '../../utils/bookingLabels'
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

const PAST = ['REJECTED', 'CANCELLED', 'COMPLETED']
const startOf = (b: BookingListItem) => `${b.first_session.date} ${b.first_session.start_time}`
const soon = computed(() => items.value.filter((b) => !PAST.includes(b.display_status)).sort((x, y) => (startOf(x) < startOf(y) ? -1 : 1)))
const past = computed(() => items.value.filter((b) => PAST.includes(b.display_status)).sort((x, y) => (startOf(x) < startOf(y) ? 1 : -1)))
const shown = computed(() => (tab.value === 'soon' ? soon.value : past.value))

onMounted(async () => {
  try {
    items.value = (await listMyBookings(api, { page: 1, size: 100 })).items
  } catch {
    failed.value = true
  } finally {
    loaded.value = true
  }
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
const coverOf = (roomId: number) => covers.value[roomId] ?? null
const time = (b: BookingListItem) => `${b.first_session.start_time.slice(0, 5)}–${b.first_session.end_time.slice(0, 5)}`
const tone = (status: string) =>
  status === 'CONFIRMED' || status === 'COMPLETED' ? 'ok' : status === 'REJECTED' || status === 'CANCELLED' ? 'off' : 'wait'
</script>

<template>
  <section class="st-page my-page">
    <header class="st-head head">
      <h1>My bookings</h1>
      <button type="button" class="book" @click="router.push({ name: 'find-room' })"><Plus :size="16" aria-hidden="true" />Book a room</button>
    </header>

    <div class="st-seg tabs" role="tablist" aria-label="Bookings">
      <button type="button" role="tab" :aria-selected="tab === 'soon'" :class="{ on: tab === 'soon' }" @click="tab = 'soon'">
        Coming up <span class="n">{{ soon.length }}</span>
      </button>
      <button type="button" role="tab" :aria-selected="tab === 'past'" :class="{ on: tab === 'past' }" @click="tab = 'past'">
        Past &amp; cancelled <span class="n">{{ past.length }}</span>
      </button>
    </div>

    <p v-if="failed" class="st-empty" role="alert"><b>Your bookings could not load</b></p>
    <div v-else-if="loaded && !shown.length" class="st-empty">
      <b>{{ tab === 'soon' ? 'Nothing coming up' : 'Nothing here yet' }}</b>
      <button v-if="tab === 'soon'" type="button" class="book" @click="router.push({ name: 'find-room' })">Book a room</button>
    </div>
    <ul v-else class="list">
      <li v-for="b in shown" :key="b.id">
        <article class="bk-card" tabindex="0" :aria-label="`${b.meeting_title}, details`" @click="openBooking(b.id)" @keydown.enter="openBooking(b.id)">
          <span class="date" :class="{ dim: tab === 'past' }">
            <small>{{ weekdayShort(b.first_session.date).toUpperCase() }}</small><b>{{ dateNumber(b.first_session.date) }}</b
            ><small>{{ monthShort(b.first_session.date).toUpperCase() }}</small>
          </span>
          <span class="ph"><RoomPhoto :path="coverOf(b.room.id)" :alt="b.room.name_en" /></span>
          <span class="txt">
            <h2>{{ b.meeting_title }}</h2>
            <span class="meta">
              <span class="mono">{{ time(b) }}</span><span v-if="b.session_count > 1"> +{{ b.session_count - 1 }} more</span> · {{ b.room.name_en }}
            </span>
          </span>
          <span class="pill" :class="tone(b.display_status)">{{ statusLabel(b.display_status) }}</span>
          <button v-if="b.display_status === 'CONFIRMED'" type="button" class="pass" @click.stop="openBooking(b.id)">
            <KeyRound :size="14" aria-hidden="true" />Door pass
          </button>
        </article>
      </li>
    </ul>

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
.book {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 40px;
  padding: 0 16px;
  border: 0;
  border-radius: 12px;
  background: var(--color-crimson-fill);
  color: #fff;
  font: inherit;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 160ms ease, transform 160ms var(--ease-out-quint);
}
.book:active,
.pass:active {
  transform: scale(0.97);
}
.tabs {
  align-self: flex-start;
  margin: 22px 0 16px;
}
.tabs .n {
  margin-left: 4px;
  color: var(--color-ink-off);
  font-size: 12px;
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
.txt h2 {
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
.pass {
  display: inline-flex;
  flex: none;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding: 0 12px;
  border: 0;
  border-radius: 10px;
  background: var(--color-field-disabled);
  color: var(--color-ink);
  font: inherit;
  font-size: 13px;
  cursor: pointer;
  transition: background-color 160ms ease, transform 160ms var(--ease-out-quint);
}
@media (hover: hover) and (pointer: fine) {
  .bk-card:hover {
    box-shadow: 0 6px 20px rgba(30, 22, 17, 0.08);
  }
  .book:hover {
    background: var(--color-crimson-deep);
  }
  .pass:hover {
    background: var(--color-rule);
  }
}
@media (max-width: 640px) {
  .ph,
  .pill {
    display: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .bk-card,
  .book,
  .pass {
    transition: none;
  }
}
</style>
