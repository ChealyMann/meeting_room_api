<script setup lang="ts">
// A room (Staff): the photo fills the page with the name, facts and equipment on it, and a
// floating "Book a time" card. Continue opens the booking with that time already picked.
import { ArrowRight, Clock, Lock } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '../../api'
import { getRoomSchedule } from '../../api/bookings'
import { getRoom } from '../../api/rooms'
import { listHolidays } from '../../api/staff'
import type { PublicHolidayOut, RoomDetail, ScheduleItem } from '../../api/types'
import { useLiveRefresh } from '../../composables/useLiveRefresh'
import { usePhnomPenhToday } from '../../composables/usePhnomPenhToday'
import { iconFor } from '../../utils/equipmentIcons'
import { phnomPenhClock } from '../../utils/time'
import PhotoGallery from './PhotoGallery.vue'
import { busySpans, nowLine, roomHours, toMin, toTime, daysFrom } from './rules'
import TimePick from './TimePick.vue'
import './staff.css'

const route = useRoute()
const router = useRouter()
const today = usePhnomPenhToday()
const roomId = Number(route.params.roomId)
const room = ref<RoomDetail | null>(null)
const busy = ref<ScheduleItem[]>([])
const holidays = ref<PublicHolidayOut[]>([])
const failed = ref(false)

const now = () => toMin(phnomPenhClock(new Date()))
const hours = computed(() => (room.value ? roomHours(room.value) : { open: 480, close: 1080 }))
/** The next seven days, weekends too; today is left out when less than 30 minutes stay open. */
const days = computed(() =>
  daysFrom(today.value, 8)
    .filter((d) => d !== today.value || now() < hours.value.close - 30)
    .slice(0, 7),
)
const line = computed(() => nowLine(busySpans(busy.value, today.value), hours.value, today.value, today.value, now()))

onMounted(async () => {
  try {
    room.value = await getRoom(api, roomId)
    const first = days.value[0]!
    const last = days.value[days.value.length - 1]!
    const [schedule, offDays] = await Promise.all([getRoomSchedule(api, roomId, first, last), listHolidays(api, first, last)])
    busy.value = schedule.items
    holidays.value = offDays
  } catch {
    failed.value = true
  }
})

// Quiet refresh: the free times and the status line follow new bookings with no click.
useLiveRefresh(async () => {
  if (!room.value) return
  busy.value = (await getRoomSchedule(api, roomId, days.value[0]!, days.value[days.value.length - 1]!)).items
})

function pick(p: { date: string; a: number; b: number }) {
  router.push({ name: 'book', params: { roomId }, query: { date: p.date, start: toTime(p.a), end: toTime(p.b) } })
}
</script>

<template>
  <section class="st-page room-page">
    <p v-if="failed" class="st-empty" role="alert"><b>This room could not load</b></p>
    <div v-else-if="room" class="stage">
      <div class="hero">
        <PhotoGallery :photos="room.photos" :name="room.name_en" />
        <div class="shade" aria-hidden="true" />
        <div class="title">
          <span class="st-now now on-photo" :class="line.tone"><Clock :size="14" aria-hidden="true" />{{ line.text }}</span>
          <h1>{{ room.name_en }}</h1>
          <p class="kh">{{ room.name_kh }}</p>
          <p class="facts">
            <span>{{ room.capacity }} seats</span><span>{{ room.floor.floor_label }}</span><span class="kh">{{ room.building.name_kh }}</span>
            <span v-if="room.size_sqm">{{ room.size_sqm }} sq m</span>
            <span v-if="room.is_private"><Lock :size="13" aria-hidden="true" />Private</span>
          </p>
          <p v-if="room.equipment.length" class="equip">
            <span v-for="e in room.equipment" :key="e.id"><component :is="iconFor(e.icon)" v-if="iconFor(e.icon)" :size="14" aria-hidden="true" />{{ e.name }}</span>
          </p>
        </div>
      </div>
      <aside class="card" aria-label="Book a time">
        <h2>Book a time</h2>
        <p v-if="room.is_private" class="private"><Lock :size="13" aria-hidden="true" />Pitika and the room owner both check it</p>
        <TimePick :days="days" :today="today" :now="now()" :hours="hours" :busy="busy" :holidays="holidays" cta="Continue" @pick="pick" />
        <button type="button" class="more" @click="router.push({ name: 'book', params: { roomId } })">
          Several days? Pick on the calendar<ArrowRight :size="14" aria-hidden="true" />
        </button>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.room-page {
  padding: 20px 24px 24px;
}
.stage {
  position: relative;
  flex: 1;
  min-height: 600px;
}
.hero {
  position: absolute;
  inset: 0;
  overflow: hidden;
  border-radius: 26px;
}
.hero :deep(.gal-arrow.next) {
  right: 456px;
}
.shade {
  position: absolute;
  inset: 0;
  z-index: 1;
  background: linear-gradient(to top, rgba(15, 8, 6, 0.84) 0%, rgba(15, 8, 6, 0.28) 42%, rgba(15, 8, 6, 0) 64%);
  pointer-events: none;
}
.title {
  position: absolute;
  right: 460px;
  bottom: 36px;
  left: 40px;
  z-index: 2;
  color: #fff;
}
.on-photo {
  padding: 5px 12px 5px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.94);
}
.on-photo.ok {
  color: #2f6b3f;
}
.on-photo.alert {
  color: #991b1b;
}
.on-photo.off {
  color: #6b5243;
}
h1 {
  margin: 14px 0 0;
  font-size: 40px;
  font-weight: 600;
  letter-spacing: -0.03em;
  line-height: 1.1;
}
.kh {
  font-family: var(--font-kh);
}
.title > .kh {
  margin: 4px 0 0;
  color: rgba(255, 255, 255, 0.8);
  font-size: 16px;
}
.facts {
  display: flex;
  flex-wrap: wrap;
  margin: 14px 0 0;
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
}
.facts > span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.facts > span + span::before {
  content: '·';
  margin: 0 10px;
  opacity: 0.45;
}
.equip {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 18px;
  margin: 16px 0 0;
  color: rgba(255, 255, 255, 0.82);
  font-size: 12.5px;
}
.equip span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.card {
  position: absolute;
  top: 24px;
  right: 24px;
  z-index: 3;
  width: 404px;
  max-height: calc(100% - 48px);
  overflow: auto;
  padding: 24px;
  border-radius: 22px;
  background: var(--color-sheet);
  box-shadow: 0 14px 44px rgba(30, 22, 17, 0.12), 0 2px 6px rgba(30, 22, 17, 0.05);
}
.card h2 {
  margin: 0 0 4px;
  font-size: 19px;
  font-weight: 600;
  letter-spacing: -0.015em;
}
.private {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 14px;
  color: var(--color-warn);
  font-size: 12.5px;
}
.card :deep(.tp) {
  margin-top: 14px;
}
.more {
  display: flex;
  align-items: center;
  gap: 4px;
  margin: 12px auto 0;
  padding: 0;
  border: 0;
  background: none;
  color: var(--color-crimson);
  font: inherit;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}
@media (hover: hover) and (pointer: fine) {
  .more:hover {
    text-decoration: underline;
  }
}
@media (max-width: 1000px) {
  .stage {
    min-height: 0;
  }
  .hero {
    position: relative;
    inset: auto;
    height: 440px;
  }
  .hero :deep(.gal-arrow.next) {
    right: 16px;
  }
  .title {
    right: 24px;
    bottom: 24px;
    left: 24px;
  }
  .card {
    position: static;
    width: auto;
    max-height: none;
    margin-top: 16px;
  }
}
@media (max-width: 640px) {
  h1 {
    font-size: 28px;
  }
  .equip {
    display: none;
  }
}
</style>
