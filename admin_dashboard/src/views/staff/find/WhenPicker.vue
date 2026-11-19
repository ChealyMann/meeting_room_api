<script setup lang="ts">
// Inside the When chip: One day / Day to day, the next 14 days in week rows, and a time
// that is the same every day. Day to day: the first click sets the first day, the next click the
// last day; a click after that starts again. The time uses the app's own picker, never the
// browser's list (owner, 19 Nov 2026).
import { computed, ref } from 'vue'

import SearchPicker, { type PickerItem, type PickerWords } from '../../../components/list/SearchPicker.vue'

import { dateNumber, dayLabel, toTime, weekdayShort } from '../rules'
import { datesOf, isRange, startChoices, type When } from './when'

const props = defineProps<{ modelValue: When; days: string[]; today: string; now: number }>()
const emit = defineEmits<{ 'update:modelValue': [When] }>()
const when = computed(() => props.modelValue)
const set = (patch: Partial<When>) => emit('update:modelValue', { ...when.value, ...patch })

const picking = ref<'first' | 'last'>('first')

function setMode(mode: When['mode']) {
  picking.value = 'first'
  set(mode === 'one' ? { mode, last: when.value.first } : { mode })
}
function pickDay(day: string) {
  if (when.value.mode === 'one') return set({ first: day, last: day, ...keepTime(day, day) })
  if (picking.value === 'last' && day >= when.value.first) {
    picking.value = 'first'
    return set({ last: day, ...keepTime(when.value.first, day) })
  }
  picking.value = 'last'
  set({ first: day, last: day, ...keepTime(day, day) })
}
/** A start that has passed (today is now in the days) is dropped. */
function keepTime(first: string, last: string): Partial<When> {
  const start = when.value.start
  if (start === null) return {}
  return startChoices({ ...when.value, first, last }, props.today, props.now).includes(start) ? {} : { start: null, end: null }
}

// Week rows: a new row starts on each Monday.
const weeks = computed(() => {
  const rows: string[][] = []
  for (const d of props.days) {
    if (!rows.length || weekdayShort(d) === 'Mon') rows.push([])
    rows.at(-1)!.push(d)
  }
  return rows
})
const dayClass = (d: string) => ({
  on: d === when.value.first || d === when.value.last,
  mid: d > when.value.first && d < when.value.last,
})

const starts = computed(() => startChoices(when.value, props.today, props.now))
const ends = computed(() => {
  const out: number[] = []
  if (when.value.start === null) return out
  for (let m = when.value.start + 30; m <= 18 * 60; m += 30) out.push(m)
  return out
})
const asItems = (list: number[]): PickerItem[] => list.map((m) => ({ value: m, label: toTime(m) }))
const FROM_WORDS: PickerWords = { all: 'Any time', search: 'Search times', unknown: 'Any time', none: 'No time left today' }
const TO_WORDS: PickerWords = { all: '—', search: 'Search times', unknown: '—', none: 'No time' }
function setStart(value: number | string | null) {
  if (value === null || value === '') return set({ start: null, end: null })
  const start = Number(value)
  const end = when.value.end !== null && when.value.end > start ? when.value.end : Math.min(start + 60, 18 * 60)
  set({ start, end })
}
const QUICK = [
  ['Morning', 8 * 60, 12 * 60],
  ['Afternoon', 13 * 60, 17 * 60],
  ['All day', 8 * 60, 17 * 60],
] as const
const quick = computed(() => QUICK.filter((q) => starts.value.includes(q[1])))

const hint = computed(() => {
  if (when.value.mode !== 'range') return ''
  if (picking.value === 'last') return `From ${dayLabel(when.value.first)}. Now pick the last day.`
  if (isRange(when.value)) return `${datesOf(when.value, props.days).length} days. Click a day to start again.`
  return 'Pick the first day, then the last day.'
})
</script>

<template>
  <div class="when">
    <div class="st-seg" role="radiogroup" aria-label="One day or several">
      <button type="button" role="radio" data-mode="one" :aria-checked="when.mode === 'one'" :class="{ on: when.mode === 'one' }" @click="setMode('one')">One day</button>
      <button type="button" role="radio" data-mode="range" :aria-checked="when.mode === 'range'" :class="{ on: when.mode === 'range' }" @click="setMode('range')">
        Day to day
      </button>
    </div>
    <div class="weeks" role="group" :aria-label="when.mode === 'range' ? 'From day to day' : 'Day'">
      <div v-for="(row, i) in weeks" :key="i" class="row">
        <button
          v-for="d in row"
          :key="d"
          type="button"
          class="day"
          :class="dayClass(d)"
          :data-day="d"
          :aria-pressed="d === when.first || d === when.last"
          :aria-label="dayLabel(d)"
          @click="pickDay(d)"
        >
          <span>{{ d === today ? 'Today' : weekdayShort(d) }}</span><b>{{ dateNumber(d) }}</b>
        </button>
      </div>
    </div>
    <p v-if="hint" class="hint">{{ hint }}</p>

    <div class="time">
      <span class="lbl">Time{{ isRange(when) ? ' (the same every day)' : '' }}</span>
      <div class="selects">
        <label for="when-from" class="sr-only">From</label>
        <SearchPicker
          id="when-from"
          class="time-pick"
          mode="field"
          nullable
          :searchable="false"
          :items="asItems(starts)"
          :words="FROM_WORDS"
          :model-value="when.start"
          @update:model-value="setStart"
        />
        <span aria-hidden="true">to</span>
        <label for="when-to" class="sr-only">To</label>
        <SearchPicker
          id="when-to"
          class="time-pick"
          mode="field"
          :searchable="false"
          :disabled="when.start === null"
          :items="asItems(ends)"
          :words="TO_WORDS"
          :model-value="when.end"
          @update:model-value="(v) => set({ end: v === null ? null : Number(v) })"
        />
      </div>
      <div class="quick">
        <button
          v-for="q in quick"
          :key="q[0]"
          type="button"
          :class="{ on: when.start === q[1] && when.end === q[2] }"
          @click="set({ start: q[1], end: q[2] })"
        >
          {{ q[0] }}
        </button>
        <button type="button" :class="{ on: when.start === null }" @click="set({ start: null, end: null })">Any time</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.when {
  display: grid;
  gap: 12px;
}
.when > .st-seg {
  justify-self: start;
}
.weeks {
  display: grid;
  gap: 6px;
}
.row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.day {
  display: grid;
  justify-items: center;
  width: 52px;
  padding: 6px 0;
  border: 1px solid var(--color-rule);
  border-radius: 12px;
  background: var(--color-sheet);
  color: var(--color-ink);
  font: inherit;
  cursor: pointer;
}
.day span {
  font-size: 11px;
  color: var(--color-intaglio);
}
.day b {
  font-size: 16px;
  font-weight: 600;
  line-height: 1.2;
}
.day.mid {
  border-color: var(--color-field-disabled);
  background: var(--color-field-disabled);
}
.day.on {
  border-color: var(--color-ink);
  background: var(--color-ink);
  color: var(--color-sheet);
}
.day.on span {
  color: inherit;
  opacity: 0.8;
}
.hint {
  margin: 0;
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.time {
  display: grid;
  gap: 8px;
}
.lbl {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-intaglio);
}
.selects {
  display: flex;
  align-items: center;
  gap: 8px;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}
.selects .time-pick {
  width: 132px;
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
  border-color: var(--color-ink);
  background: var(--color-ink);
  color: var(--color-sheet);
}
</style>
