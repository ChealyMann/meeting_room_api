<script setup lang="ts">
// The week table: half-hour rows in the room's hours, one column per day (weekends too). Click a free
// cell for 1 hour, or press and drag down for any length; click a picked block to remove it.
// Busy (masked private ones too) shows "Busy", past is striped, a holiday is marked softly.
// A picked session is one pill over its cells (look B, owner pick 20 Nov 2026): set in from the
// column edges, the start bold and the end lighter on one line, a × in a white circle, and the
// length at the bottom of a long one. The pill only shows: a click on the cells under it removes it.
import { X } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, reactive } from 'vue'

import type { PublicHolidayOut, ScheduleItem } from '../../../api/types'
import { isTouchDevice } from '../../../utils/touch'
import { busySpans, dateNumber, lenText, toTime, weekdayShort, monthShort, type Hours, type PickedSession, type Span } from '../rules'

const touch = isTouchDevice()

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
const ROW = 22
const sessionsOn = (d: string) => props.sessions.filter((s) => s.date === d)
/** Where the pill sits: 2px in from the top and bottom of its cells. */
const pillStyle = (s: PickedSession) => ({
  top: `${((s.a - props.hours.open) / SLOT) * ROW + 2}px`,
  height: `${((s.b - s.a) / SLOT) * ROW - 4}px`,
})
const label = (d: string) => (d === props.today ? 'Today' : `${weekdayShort(d)} ${monthShort(d)}`)
</script>

<template>
  <div class="tbl-scroll" :class="{ mouse: !touch }">
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
        <em v-else :class="{ none: !freeHours(d) }">{{ freeHours(d) ? `${freeHours(d)} h free` : 'Full' }}</em>
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
          <span v-if="busyStart(d, i - 1) && !mineAt(d, i - 1)" class="cell-busy">Busy</span>
        </button>
        <span
          v-for="s in sessionsOn(d)"
          :key="s.a"
          class="pill"
          :class="{ half: s.b - s.a <= SLOT, long: s.b - s.a >= 90 }"
          :style="pillStyle(s)"
          aria-hidden="true"
        >
          <span class="pill-time mono"><b>{{ toTime(s.a) }}</b><span class="pill-end">–{{ toTime(s.b) }}</span></span>
          <span class="pill-x"><X :size="10" :stroke-width="2.8" /></span>
          <span v-if="s.b - s.a >= 90" class="pill-len">{{ lenText(s.b - s.a) }}</span>
        </span>
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
  position: relative;
  container-type: inline-size;
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
  background: transparent;
  box-shadow: none;
}
.cell.pending {
  background: var(--color-crimson-wash);
  box-shadow: inset 2px 0 0 var(--color-crimson), inset -2px 0 0 var(--color-crimson);
}
/* The picked pill (look B) */
.pill {
  position: absolute;
  right: 2px;
  left: 2px;
  z-index: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 5px 23px 5px 6px;
  border-radius: 10px;
  /* The solid fill token (like the primary button): --color-crimson is the light text crimson in the
     night theme and looked pale under white text (owner, 20 Nov 2026). */
  background: var(--color-crimson-fill);
  box-shadow: 0 2px 6px rgba(127, 29, 29, 0.28);
  color: #fff;
  pointer-events: none;
  transition: background-color 140ms ease;
}
.pill-time {
  overflow: hidden;
  font-size: 10.5px;
  font-weight: 400;
  line-height: 1.3;
  white-space: nowrap;
  opacity: 0.92;
}
.pill-time b {
  font-weight: 500;
  opacity: 1;
}
.pill-x {
  position: absolute;
  top: 5px;
  right: 4px;
  display: grid;
  place-items: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.95);
  color: var(--color-crimson-fill);
  transition: opacity 140ms ease;
}
.pill-len {
  font-size: 11px;
  font-weight: 500;
  opacity: 0.85;
}
/* A half hour is one row: one tight line, the × centred on it. */
.pill.half {
  justify-content: center;
  padding-top: 0;
  padding-bottom: 0;
}
.pill.half .pill-time {
  font-size: 10.5px;
  line-height: 1;
}
.pill.half .pill-x {
  top: 50%;
  width: 14px;
  height: 14px;
  transform: translateY(-50%);
}
/* Only a mouse device (owner pick, 20 Nov 2026): the × shows on hover, so the time has the whole
   pill. A touch device (an iPad, even with a trackpad) always shows the × (owner, 20 Nov 2026). */
.tbl-scroll.mouse .pill {
  padding-right: 3px;
}
.tbl-scroll.mouse .pill-x {
  opacity: 0;
}
.tbl-scroll.mouse .tbl-col:has(.cell.mine:hover) .pill-x {
  opacity: 1;
}
/* A very narrow column (a phone) still keeps the time whole: the end drops under the start, no ×. */
@container (max-width: 80px) {
  .pill {
    padding-right: 4px;
  }
  .pill-x {
    display: none;
  }
  .pill-time {
    display: grid;
  }
  .pill.half .pill-end,
  .pill-len {
    display: none;
  }
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
  /* Hovering a picked cell darkens its pill (the cells stay clear). */
  .tbl-col:has(.cell.mine:hover) .pill {
    background: var(--color-crimson-deep);
  }
}
@media (prefers-reduced-motion: reduce) {
  .cell {
    transition: none;
  }
}
</style>
