<script setup lang="ts">
// A room (Staff), look A "Split" (owner pick, 20 Nov 2026): the big photo with small photos under
// it, then the status, the names and the facts, the description, what is in the room and good to
// know; the "Book a time" card stays on the right while the page scrolls. Nothing is written on
// the photo. Continue opens the booking with that time already picked.
import { ArrowRight, Building2, Check, Clock, Layers, MapPin, Ruler, Tag, User, UserLock, Users } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api, apiBaseUrl } from '../../api'
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
const shown = ref(0)

const now = () => toMin(phnomPenhClock(new Date()))
const hours = computed(() => (room.value ? roomHours(room.value) : { open: 480, close: 1080 }))
/** The next seven days, weekends too; today is left out when less than 30 minutes stay open. */
const days = computed(() =>
  daysFrom(today.value, 8)
    .filter((d) => d !== today.value || now() < hours.value.close - 30)
    .slice(0, 7),
)
const line = computed(() => nowLine(busySpans(busy.value, today.value), hours.value, today.value, today.value, now()))
const about = computed(() => room.value?.description || room.value?.short_desc || '')
const openText = computed(() => `${toTime(hours.value.open)}–${toTime(hours.value.close)}`)

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
    <div v-else-if="room" class="room">
      <div class="info">
        <div class="photos">
          <div class="main">
            <PhotoGallery v-model:shown="shown" :photos="room.photos" :name="room.name_en" :dots="false" />
            <span v-if="room.photos.length > 1" class="count">{{ shown + 1 }} / {{ room.photos.length }}</span>
          </div>
          <div v-if="room.photos.length > 1" class="thumbs">
            <button
              v-for="(p, n) in room.photos"
              :key="p.id"
              type="button"
              :aria-label="`Photo ${n + 1}`"
              :aria-current="n === shown"
              @click="shown = n"
            >
              <img :src="`${apiBaseUrl}${p.url}`" alt="" loading="lazy" />
            </button>
          </div>
        </div>

        <div class="names">
          <p class="tags">
            <span class="st-now now" :class="line.tone"><Clock :size="14" aria-hidden="true" />{{ line.text }}</span>
            <span v-if="room.is_private" class="lock"><UserLock :size="13" aria-hidden="true" />Private</span>
          </p>
          <p class="kh">{{ room.name_kh }}</p>
          <h1>{{ room.name_en }}</h1>
          <p class="facts">
            <span><Users :size="14" aria-hidden="true" /><b class="num">{{ room.capacity }}</b> seats</span>
            <span v-if="room.size_sqm"><Ruler :size="14" aria-hidden="true" /><b class="num">{{ room.size_sqm }}</b> m²</span>
            <span><Layers :size="14" aria-hidden="true" />{{ room.floor.floor_label }}</span>
          </p>
        </div>

        <p v-if="about" class="about">{{ about }}</p>

        <div class="two">
          <section v-if="room.equipment.length" aria-labelledby="in-room">
            <h2 id="in-room" class="h-sec">In the room</h2>
            <ul class="equip">
              <li v-for="e in room.equipment" :key="e.id">
                <span class="ico"><component :is="iconFor(e.icon) ?? Check" :size="16" aria-hidden="true" /></span>{{ e.name }}
              </li>
            </ul>
          </section>
          <section aria-labelledby="good-to-know">
            <h2 id="good-to-know" class="h-sec">Good to know</h2>
            <dl class="know">
              <div><Clock :size="14" aria-hidden="true" /><dt>Open</dt><dd><span class="num">{{ openText }}</span> every day</dd></div>
              <div><Tag :size="14" aria-hidden="true" /><dt>Room type</dt><dd>{{ room.category.name_en }}</dd></div>
              <div><Building2 :size="14" aria-hidden="true" /><dt>Building</dt><dd>{{ room.building.name_en }}</dd></div>
              <div><MapPin :size="14" aria-hidden="true" /><dt>Office</dt><dd>{{ room.location.name_en }}</dd></div>
              <div v-if="room.owner"><User :size="14" aria-hidden="true" /><dt>Owner</dt><dd>{{ room.owner.name_en }}</dd></div>
            </dl>
          </section>
        </div>
      </div>

      <aside class="card" aria-label="Book a time">
        <h2>Book a time</h2>
        <p v-if="room.is_private" class="private"><UserLock :size="13" aria-hidden="true" />Pitika and the room owner both check it</p>
        <TimePick :days="days" :today="today" :now="now()" :hours="hours" :busy="busy" :holidays="holidays" cta="Continue" @pick="pick" />
        <button type="button" class="more" @click="router.push({ name: 'book', params: { roomId } })">
          Several days? Pick on the calendar<ArrowRight :size="14" aria-hidden="true" />
        </button>
      </aside>
    </div>
  </section>
</template>

<style scoped>
/* The page padding is the shared .st-page one, the same as Find a room (owner, 20 Nov 2026). */
.room {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 404px;
  gap: 36px;
  align-items: start;
}
.info {
  display: grid;
  gap: 26px;
  min-width: 0;
}
/* Photos: the big one, then the small ones in a row. */
.photos {
  display: grid;
  gap: 8px;
}
/* The photo takes the screen height that is left, so the name and facts show without scrolling
   (owner, 20 Nov 2026). */
.main {
  position: relative;
  overflow: hidden;
  height: clamp(240px, calc(100vh - 430px), 500px);
  border-radius: 18px;
  background: var(--color-field-disabled);
}
.count {
  position: absolute;
  right: 12px;
  bottom: 12px;
  z-index: 2;
  padding: 3px 9px;
  border-radius: 999px;
  background: rgba(20, 10, 8, 0.62);
  color: #fff;
  font-family: var(--font-mono);
  font-size: 12px;
}
.thumbs {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
}
.thumbs button {
  flex: 0 0 auto;
  width: 96px;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  padding: 0;
  border: 2px solid transparent;
  border-radius: 12px;
  background: var(--color-field-disabled);
  opacity: 0.72;
  cursor: pointer;
  transition: opacity 160ms ease, border-color 160ms ease;
}
.thumbs button[aria-current='true'] {
  border-color: var(--color-ink);
  opacity: 1;
}
.thumbs img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
@media (hover: hover) and (pointer: fine) {
  .thumbs button:hover {
    opacity: 1;
  }
}
/* Status, names and facts. */
.names {
  display: grid;
  gap: 8px;
}
.tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
  margin: 0;
}
.lock {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-warn);
  font-size: 12.5px;
  font-weight: 500;
}
/* Khmer over English (owner, 20 Nov 2026; DESIGN.md "Two Names Rule"). */
.kh {
  margin: 0;
  color: var(--color-ink);
  font-family: var(--font-kh);
  font-size: 28px;
  font-weight: 600;
  line-height: 1.4;
}
h1 {
  margin: -6px 0 0;
  color: var(--color-intaglio);
  font-size: 16px;
  font-weight: 500;
}
.facts {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 18px;
  margin: 4px 0 0;
  color: var(--color-intaglio);
  font-size: 13.5px;
}
.facts > span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  white-space: nowrap;
}
.num {
  font-family: var(--font-mono);
  font-weight: 400;
  font-variant-numeric: tabular-nums;
}
.about {
  max-width: 64ch;
  margin: 0;
  color: var(--color-ink-off);
}
/* In the room | Good to know */
.two {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr);
  gap: 32px;
  padding-top: 22px;
  border-top: 1px solid var(--color-rule);
}
.h-sec {
  margin: 0 0 12px;
  font-size: 13.5px;
  font-weight: 600;
}
.equip {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 10px 16px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.equip li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13.5px;
}
.ico {
  display: grid;
  flex: none;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: var(--color-field-disabled);
  color: var(--color-intaglio);
}
.know {
  display: grid;
  margin: 0;
}
.know > div {
  display: grid;
  grid-template-columns: 22px 100px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  padding: 10px 0;
  border-top: 1px solid var(--color-rule);
  font-size: 13.5px;
}
.know > div:first-child {
  padding-top: 0;
  border-top: 0;
}
.know svg {
  color: var(--color-intaglio);
}
.know dt {
  color: var(--color-intaglio);
}
.know dd {
  min-width: 0;
  margin: 0;
}
/* The card stays on the right while the page scrolls. */
.card {
  position: sticky;
  top: 0; /* the page's own top padding already keeps it off the edge */
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
/* Narrow: one column; the card comes right after the names and facts. */
@media (max-width: 1000px) {
  .room {
    grid-template-columns: minmax(0, 1fr);
    gap: 26px;
  }
  .main {
    height: auto;
    aspect-ratio: 16 / 10;
  }
  .info {
    display: contents;
  }
  .card {
    position: static;
    order: 1;
  }
  .about,
  .two {
    order: 2;
  }
}
@media (max-width: 640px) {
  .main {
    aspect-ratio: 4 / 3;
  }
  .thumbs button {
    width: 76px;
  }
  .names > .kh {
    font-size: 24px;
  }
  .two {
    grid-template-columns: minmax(0, 1fr);
    gap: 24px;
  }
  .know > div {
    grid-template-columns: 22px 92px minmax(0, 1fr);
  }
}
</style>
