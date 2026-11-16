<script setup lang="ts">
// The booking's side card: the room photo, the picked sessions (× removes one), holiday notes,
// a short message slot, the total, and the step buttons. It fills the height; only the list scrolls.
import { X } from 'lucide-vue-next'
import { computed } from 'vue'

import RoomPhoto from '../../../components/RoomPhoto.vue'
import type { PublicHolidayOut, RoomDetail } from '../../../api/types'
import { dayLabel, lenText, toTime, type PickedSession } from '../rules'

const props = defineProps<{
  room: RoomDetail
  sessions: PickedSession[]
  holidays: PublicHolidayOut[]
  today: string
  tomorrow: string
  message?: string
}>()
const emit = defineEmits<{ remove: [PickedSession] }>()

const sorted = computed(() => [...props.sessions].sort((x, y) => (x.date === y.date ? x.a - y.a : x.date < y.date ? -1 : 1)))
const total = computed(() => props.sessions.reduce((sum, s) => sum + s.b - s.a, 0))
const dayName = (d: string) => (d === props.today ? 'Today' : d === props.tomorrow ? 'Tomorrow' : dayLabel(d))
const holidayNotes = computed(() => {
  const days = [...new Set(sorted.value.map((s) => s.date))]
  return days
    .map((d) => ({ d, h: props.holidays.find((h) => h.holiday_date === d) }))
    .filter((x) => x.h)
    .map((x) => `${dayLabel(x.d)} is ${x.h!.name_en || x.h!.name_km}`)
})
const cover = computed(() => props.room.photos[0]?.url ?? null)
</script>

<template>
  <aside class="bf-side" aria-label="Your booking">
    <div class="ph"><RoomPhoto :path="cover" :alt="room.name_en" /></div>
    <div class="body">
      <h2 class="head">Your sessions</h2>
      <ul v-if="sorted.length" class="bf-sess">
        <li v-for="s in sorted" :key="`${s.date}-${s.a}`">
          <span class="when"
            ><b class="day">{{ dayName(s.date) }}</b> <span class="time"
              ><span class="mono">{{ toTime(s.a) }}–{{ toTime(s.b) }}</span
              ><span class="len">{{ ` · ${lenText(s.b - s.a)}` }}</span></span
            ></span
          >
          <button type="button" class="rm" :aria-label="`Remove ${dayLabel(s.date)} ${toTime(s.a)}`" @click="emit('remove', s)">
            <X :size="14" aria-hidden="true" />
          </button>
        </li>
      </ul>
      <p v-else class="none">Click a free time, or press and drag down.</p>
      <p v-for="n in holidayNotes" :key="n" class="hol">{{ n }}</p>
      <p v-if="message" class="msg" role="alert">{{ message }}</p>
      <slot />
    </div>
    <div class="foot">
      <p v-if="sorted.length" class="total">
        <span>Total</span><span>{{ sorted.length }} {{ sorted.length === 1 ? 'session' : 'sessions' }} · {{ lenText(total) }}</span>
      </p>
      <div class="actions"><slot name="actions" /></div>
    </div>
  </aside>
</template>

<style scoped>
.bf-side {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  border-radius: 20px;
  background: var(--color-sheet);
  box-shadow: 0 10px 36px rgba(30, 22, 17, 0.08), 0 1px 4px rgba(30, 22, 17, 0.05);
}
.ph {
  flex: none;
  height: 132px;
  overflow: hidden;
}
.ph :deep(img),
.ph :deep(.room-photo) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.body {
  flex: 1;
  min-height: 0;
  padding: 0 20px 12px;
  overflow: auto;
  scrollbar-width: thin;
}
.head {
  position: sticky;
  top: 0;
  z-index: 1;
  margin: 0;
  padding: 16px 0 8px;
  background: var(--color-sheet);
  font-size: 14px;
  font-weight: 600;
}
.bf-sess {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
/* Day on top, time and length under it; × on the right. Nothing breaks inside a line. */
.bf-sess li {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 6px 8px 12px;
  border-radius: 12px;
  background: var(--color-paper);
}
.when {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}
.day {
  font-size: 13.5px;
  font-weight: 600;
  line-height: 1.35;
}
.time {
  font-size: 12.5px;
  line-height: 1.4;
  white-space: nowrap;
}
.len {
  color: var(--color-intaglio);
}
.rm {
  flex: none;
}
.rm {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--color-ink-off);
  cursor: pointer;
  transition: background-color 160ms ease, color 160ms ease, transform 160ms var(--ease-out-quint);
}
.rm:active {
  transform: scale(0.97);
}
.none {
  margin: 4px 0 0;
  color: var(--color-ink-off);
  font-size: 13px;
}
.hol {
  margin: 10px 0 0;
  padding: 8px 12px;
  border-radius: 10px;
  background: var(--color-saved-tint);
  color: var(--color-warn);
  font-size: 12.5px;
}
.msg {
  margin: 10px 0 0;
  color: var(--color-crimson);
  font-size: 13px;
}
.foot {
  flex: none;
  padding: 12px 20px 18px;
  border-top: 1px solid var(--color-rule);
}
.total {
  display: flex;
  justify-content: space-between;
  margin: 0 0 12px;
  font-size: 13.5px;
}
.total span:first-child {
  color: var(--color-intaglio);
}
.total span:last-child {
  font-weight: 600;
}
.actions {
  display: flex;
  gap: 8px;
}
@media (hover: hover) and (pointer: fine) {
  .rm:hover {
    background: var(--color-field-disabled);
    color: var(--color-ink);
  }
}
@media (prefers-reduced-motion: reduce) {
  .rm {
    transition: none;
  }
}
</style>
