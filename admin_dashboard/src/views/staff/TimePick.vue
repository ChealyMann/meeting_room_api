<script setup lang="ts">
// "Book a time": a day, how long, then only the start times that are free (busy and past times
// are never offered). A public holiday is marked softly and stays bookable (owner, 12 Nov 2026).
import { computed, ref, watch } from 'vue'

import type { PublicHolidayOut, ScheduleItem } from '../../api/types'
import { busySpans, dateNumber, dayLabel, freeStarts, monthShort, toTime, weekdayShort, type Hours } from './rules'

const props = defineProps<{
  days: string[]
  today: string
  now: number
  hours: Hours
  busy: ScheduleItem[]
  holidays: PublicHolidayOut[]
  cta: string
}>()
const emit = defineEmits<{ pick: [{ date: string; a: number; b: number }] }>()

const LENGTHS = [30, 60, 90, 120, 180]
const lengthText = (m: number) => (m < 60 ? `${m} min` : m % 60 ? `${Math.floor(m / 60)} h ${m % 60}` : `${m / 60} h`)

const day = ref(props.days[0] ?? props.today)
const len = ref(60)
const start = ref<number | null>(null)
watch(
  () => props.days,
  (list) => {
    if (!list.includes(day.value)) day.value = list[0] ?? props.today
  },
)

const startsOn = (d: string) => freeStarts(busySpans(props.busy, d), props.hours, d, props.today, props.now, len.value)
const times = computed(() => startsOn(day.value))
watch([day, len], () => {
  if (start.value !== null && !times.value.includes(start.value)) start.value = null
})
const holidayOf = (d: string) => props.holidays.find((h) => h.holiday_date === d)
const label = (d: string) => (d === props.today ? 'Today' : weekdayShort(d))

function go() {
  if (start.value !== null) emit('pick', { date: day.value, a: start.value, b: start.value + len.value })
}
</script>

<template>
  <div class="tp">
    <div class="tp-row"><span class="tp-h">Day</span><span class="tp-sub">{{ monthShort(day) }} {{ day.slice(0, 4) }}</span></div>
    <div class="tp-days" role="radiogroup" aria-label="Day">
      <button
        v-for="d in days"
        :key="d"
        type="button"
        role="radio"
        :data-day="d"
        :aria-checked="d === day"
        :title="holidayOf(d)?.name_en || holidayOf(d)?.name_km"
        :class="{ on: d === day, full: !startsOn(d).length, holiday: holidayOf(d) }"
        @click="day = d"
      >
        <small>{{ label(d) }}</small><b>{{ dateNumber(d) }}</b><em v-if="holidayOf(d)">Holiday</em>
      </button>
    </div>
    <div class="tp-row"><span class="tp-h">How long</span></div>
    <div class="st-seg tp-len" role="radiogroup" aria-label="How long">
      <button v-for="m in LENGTHS" :key="m" type="button" role="radio" :aria-checked="len === m" :class="{ on: len === m }" @click="len = m">
        {{ lengthText(m) }}
      </button>
    </div>
    <div class="tp-row"><span class="tp-h">Start time</span><span class="tp-sub">{{ times.length ? `${times.length} free` : '' }}</span></div>
    <div class="tp-times" role="radiogroup" aria-label="Start time">
      <button
        v-for="a in times"
        :key="a"
        type="button"
        role="radio"
        class="mono"
        :aria-checked="start === a"
        :class="{ on: start === a }"
        @click="start = start === a ? null : a"
      >
        {{ toTime(a) }}
      </button>
      <p v-if="!times.length" class="tp-empty">No free {{ lengthText(len) }} on this day. Try a shorter time or another day.</p>
    </div>
    <button type="button" class="tp-go" :disabled="start === null" @click="go">
      <template v-if="start !== null">{{ cta }} · {{ toTime(start) }}–{{ toTime(start + len) }}, {{ dayLabel(day) }}</template>
      <template v-else>Pick a start time</template>
    </button>
  </div>
</template>

<style scoped>
.tp {
  display: grid;
  gap: 10px;
}
.tp-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-top: 8px;
}
.tp-row:first-child {
  margin-top: 0;
}
.tp-h {
  font-size: 13px;
  font-weight: 600;
}
.tp-sub {
  color: var(--color-ink-off);
  font-size: 12.5px;
}
.tp-days {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 4px;
}
.tp-days button {
  position: relative;
  display: grid;
  justify-items: center;
  gap: 2px;
  padding: 8px 0 9px;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: var(--color-ink);
  font: inherit;
  cursor: pointer;
  transition: background-color 150ms ease, color 150ms ease, opacity 150ms ease, transform 160ms var(--ease-out-quint);
}
.tp-days button:active {
  transform: scale(0.95);
}
.tp-days small {
  color: var(--color-ink-off);
  font-size: 11.5px;
}
.tp-days b {
  font-size: 17px;
  font-weight: 600;
  line-height: 1.2;
}
.tp-days em {
  color: var(--color-warn);
  font-size: 9.5px;
  font-style: normal;
  font-weight: 500;
}
.tp-days button.full {
  opacity: 0.38;
}
.tp-days button.on {
  background: var(--color-crimson-fill);
  color: #fff;
  opacity: 1;
}
.tp-days button.on small,
.tp-days button.on em {
  color: rgba(255, 255, 255, 0.85);
}
.tp-len {
  display: flex;
}
.tp-len button {
  flex: 1;
  height: 32px;
  padding: 0 4px;
}
.tp-times {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
  max-height: 182px;
  overflow: auto;
  margin: -2px;
  padding: 2px;
}
.tp-times button {
  height: 40px;
  border: 1px solid var(--color-rule-strong);
  border-radius: 11px;
  background: var(--color-sheet);
  color: var(--color-ink);
  font-size: 13.5px;
  cursor: pointer;
  transition: background-color 150ms ease, border-color 150ms ease, color 150ms ease, transform 160ms var(--ease-out-quint);
}
.tp-times button:active {
  transform: scale(0.95);
}
.tp-times button.on {
  border-color: var(--color-crimson-fill);
  background: var(--color-crimson-fill);
  color: #fff;
}
.tp-empty {
  grid-column: 1 / -1;
  margin: 0;
  padding: 14px;
  border-radius: 12px;
  background: var(--color-field-disabled);
  color: var(--color-intaglio);
  font-size: 13px;
  text-align: center;
}
.tp-go {
  width: 100%;
  height: 50px;
  margin-top: 8px;
  border: 0;
  border-radius: 14px;
  background: var(--color-crimson-fill);
  color: #fff;
  font: inherit;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 150ms ease, transform 160ms var(--ease-out-quint);
}
.tp-go:active:not(:disabled) {
  transform: scale(0.97);
}
.tp-go:disabled {
  background: var(--color-field-disabled);
  color: var(--color-ink-off);
  cursor: not-allowed;
}
@media (hover: hover) and (pointer: fine) {
  .tp-days button:not(.on):hover {
    background: var(--color-field-disabled);
  }
  .tp-times button:not(.on):hover {
    border-color: var(--color-ink);
  }
  .tp-go:not(:disabled):hover {
    background: var(--color-crimson-deep);
  }
}
@media (prefers-reduced-motion: reduce) {
  .tp-days button,
  .tp-times button,
  .tp-go {
    transition-duration: 1ms;
  }
}
</style>
