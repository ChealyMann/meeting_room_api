<script setup lang="ts">
// The week table: half-hour rows in the room's hours, one column per working day. Click a free
// cell for 1 hour, or press and drag down for any length; click a picked block to remove it.
// Busy (masked private ones too) shows "Busy", past is striped, a holiday is marked softly.
import { X } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, reactive } from 'vue'

import type { PublicHolidayOut, ScheduleItem } from '../../../api/types'
import { busySpans, dateNumber, toTime, weekdayShort, monthShort, type Hours, type PickedSession, type Span } from '../rules'

const props = defineProps<{
  days: string[]
  hours: Hours
  busy: ScheduleItem[]
  holidays: PublicHolidayOut[]
  sessions: PickedSession[]
  today: string
  now: number
}>()
const emit = defineEmits<{ add: [PickedSession]; remove: [PickedSession] }>()

const SLOT = 30
const rows = computed(() => Math.max(0, Math.floor((props.hours.close - props.hours.open) / SLOT)))
const startOf = (i: number) => props.hours.open + i * SLOT

const spans = computed<Record<string, Span[]>>(() => Object.fromEntries(props.days.map((d) => [d, busySpans(props.busy, d)])))
const holidayOf = (d: string) => props.holidays.find((h) => h.holiday_date === d)
const mineAt = (d: string, i: number) => props.sessions.find((s) => s.date === d && s.a <= startOf(i) && startOf(i) < s.b) ?? null
function stateOf(d: string, i: number): 'past' | 'busy' | 'free' {
  const a = startOf(i)
  if (d < props.today || (d === props.today && a < props.now)) return 'past'
  if ((spans.value[d] ?? []).some((s) => a < s.b && s.a < a + SLOT)) return 'busy'
  return 'free'
}
const isFree = (d: string, i: number) => stateOf(d, i) === 'free' && !mineAt(d, i)
const freeHours = (d: string) => (Array.from({ length: rows.value }, (_, i) => i).filter((i) => stateOf(d, i) === 'free').length * SLOT) / 60

// Drag: from the pressed cell, down (or up) over free cells next to each other.
const drag = reactive<{ day: string | null; from: number; to: number; moved: boolean }>({ day: null, from: 0, to: 0, moved: false })
let skipClick = false
function down(d: string, i: number, e: PointerEvent) {
  skipClick = false
  if (e.pointerType === 'mouse' && e.button !== 0) return
  if (!isFree(d, i)) return
  Object.assign(drag, { day: d, from: i, to: i, moved: false })
}
function enter(d: string, i: number) {
  if (drag.day !== d) return
  const step = i > drag.to ? 1 : -1
  let j = drag.to
  while (j !== i && isFree(d, j + step)) j += step
  if (j !== drag.to) Object.assign(drag, { to: j, moved: true })
}
function up() {
  if (drag.day === null) return
  const d = drag.day
  const lo = Math.min(drag.from, drag.to)
  let hi = Math.max(drag.from, drag.to)
  if (!drag.moved && hi + 1 < rows.value && isFree(d, hi + 1)) hi += 1 // a click gives 1 hour
  drag.day = null
  skipClick = true // the click that follows this press must not remove the new block
  emit('add', { date: d, a: startOf(lo), b: startOf(hi + 1) })
}
function clickCell(d: string, i: number) {
  if (skipClick) {
    skipClick = false
    return
  }
  const mine = mineAt(d, i)
  if (mine) emit('remove', mine)
}
function key(d: string, i: number, e: KeyboardEvent) {
  if (e.key !== 'Enter' && e.key !== ' ') return
  e.preventDefault()
  const mine = mineAt(d, i)
  if (mine) emit('remove', mine)
  else if (isFree(d, i)) emit('add', { date: d, a: startOf(i), b: startOf(Math.min(rows.value, isFree(d, i + 1) ? i + 2 : i + 1)) })
}
const pending = (d: string, i: number) => drag.day === d && i >= Math.min(drag.from, drag.to) && i <= Math.max(drag.from, drag.to)
const busyStart = (d: string, i: number) => stateOf(d, i) === 'busy' && (i === 0 || stateOf(d, i - 1) !== 'busy')

onMounted(() => window.addEventListener('pointerup', up))
onBeforeUnmount(() => window.removeEventListener('pointerup', up))
const label = (d: string) => (d === props.today ? 'Today' : `${weekdayShort(d)} ${monthShort(d)}`)
</script>

<template>
  <div class="tbl-scroll">
    <div class="tbl" :style="{ gridTemplateColumns: `52px repeat(${days.length}, minmax(0, 1fr))` }">
      <div class="tbl-corner" />
      <div
        v-for="d in days"
        :key="d"
        class="tbl-day"
        :data-day="d"
        :class="{ today: d === today, holiday: holidayOf(d) }"
        :title="holidayOf(d)?.name_en || holidayOf(d)?.name_km"
      >
        <small>{{ label(d) }}</small><b>{{ dateNumber(d) }}</b>
        <em v-if="holidayOf(d)" class="hol">Holiday</em>
        <em v-else :class="{ none: !freeHours(d) }">{{ freeHours(d) ? `${freeHours(d)} h free` : d === today ? 'No time left' : 'Full' }}</em>
      </div>
      <div class="tbl-times" :style="{ gridTemplateRows: `repeat(${rows}, 22px)` }">
        <span v-for="i in rows" :key="i" class="mono">{{ (i - 1) % 2 === 0 ? toTime(startOf(i - 1)) : '' }}</span>
      </div>
      <div v-for="d in days" :key="`${d}-c`" class="tbl-col" :data-day="d" :style="{ gridTemplateRows: `repeat(${rows}, 22px)` }">
        <button
          v-for="i in rows"
          :key="i"
          type="button"
          class="cell"
          :class="[
            mineAt(d, i - 1) ? 'mine' : stateOf(d, i - 1),
            { pending: pending(d, i - 1), hour: (i - 1) % 2 === 0, first: mineAt(d, i - 1)?.a === startOf(i - 1) },
          ]"
          :disabled="!mineAt(d, i - 1) && stateOf(d, i - 1) !== 'free'"
          :aria-label="`${label(d)} ${dateNumber(d)} ${toTime(startOf(i - 1))} ${mineAt(d, i - 1) ? 'picked, press to remove' : stateOf(d, i - 1)}`"
          @pointerdown="down(d, i - 1, $event)"
          @pointerenter="enter(d, i - 1)"
          @click="clickCell(d, i - 1)"
          @keydown="key(d, i - 1, $event)"
        >
          <span v-if="mineAt(d, i - 1)?.a === startOf(i - 1)" class="cell-label mono"
            >{{ toTime(mineAt(d, i - 1)!.a) }}–{{ toTime(mineAt(d, i - 1)!.b) }}<X :size="12" aria-hidden="true"
          /></span>
          <span v-else-if="busyStart(d, i - 1)" class="cell-busy">Busy</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tbl-scroll {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
.tbl {
  display: grid;
  column-gap: 6px;
  user-select: none;
  -webkit-user-select: none;
}
.tbl-corner,
.tbl-day {
  position: sticky;
  top: 0;
  z-index: 2;
  background: var(--color-sheet);
}
.tbl-day {
  display: grid;
  justify-items: center;
  padding: 0 0 8px;
}
.tbl-day small {
  color: var(--color-ink-off);
  font-size: 11.5px;
}
.tbl-day b {
  font-size: 17px;
  font-weight: 600;
  line-height: 1.25;
}
.tbl-day em {
  color: var(--color-ok);
  font-size: 11px;
  font-style: normal;
}
.tbl-day em.none {
  color: var(--color-ink-off);
}
.tbl-day em.hol {
  padding: 0 7px;
  border-radius: 999px;
  background: var(--color-saved-tint);
  color: var(--color-warn);
  font-weight: 500;
}
.tbl-day.today b,
.tbl-day.today small {
  color: var(--color-crimson);
}
.tbl-times {
  display: grid;
}
.tbl-times span {
  padding-right: 8px;
  color: var(--color-ink-off);
  font-size: 11px;
  text-align: right;
  transform: translateY(-7px);
}
.tbl-times span:first-child {
  transform: none;
}
.tbl-col {
  display: grid;
  overflow: hidden;
  border-radius: 12px;
  background: var(--color-sheet);
  box-shadow: inset 0 0 0 1px var(--color-rule);
}
.cell {
  position: relative;
  display: block;
  width: 100%;
  height: 22px;
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
  transition: background-color 120ms ease;
}
.cell.hour:not(:first-child) {
  box-shadow: inset 0 1px 0 var(--color-rule);
}
.cell.busy {
  background: var(--color-field-disabled);
  cursor: not-allowed;
  box-shadow: none;
}
.cell.past {
  background: repeating-linear-gradient(135deg, var(--color-field-disabled) 0 5px, transparent 5px 10px);
  cursor: not-allowed;
}
.cell.mine {
  background: var(--color-crimson-fill);
  box-shadow: none;
}
.cell.pending {
  background: var(--color-crimson-wash);
  box-shadow: inset 2px 0 0 var(--color-crimson), inset -2px 0 0 var(--color-crimson);
}
.cell-label {
  position: absolute;
  top: 3px;
  right: 5px;
  left: 7px;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #fff;
  font-size: 11.5px;
  font-weight: 600;
  pointer-events: none;
}
.cell-busy {
  position: absolute;
  top: 3px;
  left: 7px;
  color: var(--color-ink-off);
  font-size: 11px;
  pointer-events: none;
}
@media (hover: hover) and (pointer: fine) {
  .cell.free:hover {
    background: var(--color-crimson-wash);
  }
  .cell.mine:hover {
    background: var(--color-crimson-deep);
  }
}
@media (max-width: 1000px) {
  .tbl {
    min-width: 560px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .cell {
    transition: none;
  }
}
</style>
