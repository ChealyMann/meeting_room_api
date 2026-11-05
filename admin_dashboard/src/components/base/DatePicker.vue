<script setup lang="ts">
// A date field in the dashboard's own look, instead of the browser's date box (owner decision,
// 5 Nov 2026), built like the TimePicker. The value stays "YYYY-MM-DD" (a Phnom Penh day, as the
// API takes it), or null when empty. The pop-up shows one month, Monday first: today has a ring,
// the chosen day is filled. Arrow keys move a day or a week, Page Up/Down a month, Home/End the
// start or end of the week, Enter picks, Escape closes. Placed like the other pickers: fixed to
// the window, above the field when there is no room below, from the bottom on a phone.
import { CalendarDays, ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'

import { usePhnomPenhToday } from '../../composables/usePhnomPenhToday'
import { addDays, formatDay } from '../../utils/time'

const props = withDefaults(
  defineProps<{
    id: string
    /** The field's name, for the pop-up's accessible name ("From"). */
    label: string
    /** Shown greyed when there is no date ("Any day"). */
    placeholder?: string
    /** Offer "Clear" (an optional date, like a filter). */
    clearable?: boolean
    /** The first and last days that can be picked, "YYYY-MM-DD". */
    min?: string | null
    max?: string | null
    invalid?: boolean
    describedBy?: string
    disabled?: boolean
  }>(),
  {
    placeholder: 'Choose a day',
    clearable: false,
    min: null,
    max: null,
    invalid: false,
    describedBy: undefined,
    disabled: false,
  },
)

const model = defineModel<string | null>({ required: true })

const DAY = /^\d{4}-\d{2}-\d{2}$/
const WEEKDAYS = [
  ['Mo', 'Monday'],
  ['Tu', 'Tuesday'],
  ['We', 'Wednesday'],
  ['Th', 'Thursday'],
  ['Fr', 'Friday'],
  ['Sa', 'Saturday'],
  ['Su', 'Sunday'],
] as const
const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
] // prettier-ignore

const today = usePhnomPenhToday()
const value = computed(() => (model.value && DAY.test(model.value) ? model.value : null))

/** "YYYY-MM" of a day, and the first day of that month. */
const monthOf = (day: string) => day.slice(0, 7)
const firstOf = (month: string) => `${month}-01`
function shiftMonth(month: string, by: number): string {
  const [y, m] = month.split('-').map(Number) as [number, number]
  const index = y * 12 + (m - 1) + by
  return `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, '0')}`
}
/** Keep a day in the same place of another month (31 Jan + 1 month = 28 Feb). */
function sameDayIn(month: string, day: string): string {
  const wanted = Number(day.slice(8, 10))
  const last = Number(addDays(firstOf(shiftMonth(month, 1)), -1).slice(8, 10))
  return `${month}-${String(Math.min(wanted, last)).padStart(2, '0')}`
}
/** Monday = 0 … Sunday = 6. */
const weekday = (day: string) => (new Date(`${day}T00:00:00Z`).getUTCDay() + 6) % 7

const outOfRange = (day: string) => (!!props.min && day < props.min) || (!!props.max && day > props.max)
function clamp(day: string): string {
  if (props.min && day < props.min) return props.min
  if (props.max && day > props.max) return props.max
  return day
}

const uid = useId()
const open = ref(false)
/** The day the keyboard is on; the shown month follows it. */
const active = ref(today.value)
const shown = computed(() => monthOf(active.value))
const title = computed(() => {
  const [y, m] = shown.value.split('-')
  return `${MONTHS[Number(m) - 1]} ${y}`
})
/** Six weeks from the Monday on or before the 1st, so every month has the same height. */
const weeks = computed(() => {
  const first = firstOf(shown.value)
  const start = addDays(first, -weekday(first))
  return Array.from({ length: 6 }, (_, w) => Array.from({ length: 7 }, (_, d) => addDays(start, w * 7 + d)))
})

const fullDate = (day: string) => {
  const [y, m, d] = day.split('-').map(Number) as [number, number, number]
  return `${WEEKDAYS[weekday(day)]![1]} ${d} ${MONTHS[m - 1]} ${y}`
}

const root = ref<HTMLElement | null>(null)
const button = ref<HTMLButtonElement | null>(null)
const grid = ref<HTMLElement | null>(null)

// Where the pop-up sits: under the field, or above it when there is no room below.
const POP_WIDTH = 292
const place = ref({ left: 0, top: 'auto', bottom: 'auto', up: false })
function position() {
  const rect = button.value?.getBoundingClientRect()
  if (!rect) return
  const below = window.innerHeight - rect.bottom - 12
  const above = rect.top - 12
  const up = below < 360 && above > below
  place.value = {
    left: Math.max(16, Math.min(rect.left, window.innerWidth - POP_WIDTH - 16)),
    top: up ? 'auto' : `${rect.bottom + 6}px`,
    bottom: up ? `${window.innerHeight - rect.top + 6}px` : 'auto',
    up,
  }
}
const popStyle = computed(() => ({
  '--pop-left': `${place.value.left}px`,
  '--pop-top': place.value.top,
  '--pop-bottom': place.value.bottom,
  '--pop-width': `${POP_WIDTH}px`,
}))

function onOutside(event: Event) {
  if (root.value && !root.value.contains(event.target as Node)) close(false)
}
watch(open, (isOpen) => {
  const method = isOpen ? 'addEventListener' : 'removeEventListener'
  document[method]('pointerdown', onOutside)
  window[method]('resize', position)
  window[method]('scroll', position, true)
})
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onOutside)
  window.removeEventListener('resize', position)
  window.removeEventListener('scroll', position, true)
})

async function focusActive() {
  await nextTick()
  grid.value?.querySelector<HTMLElement>('[data-active]')?.focus()
}

function show() {
  if (props.disabled) return
  position()
  active.value = clamp(value.value ?? today.value)
  open.value = true
  void focusActive()
}
function close(focusButton = true) {
  open.value = false
  if (focusButton) void nextTick(() => button.value?.focus())
}
function toggle() {
  if (open.value) close()
  else show()
}

function pick(day: string) {
  if (outOfRange(day)) return
  model.value = day
  close()
}
function clear() {
  model.value = null
  close()
}
function moveMonth(by: number) {
  active.value = clamp(sameDayIn(shiftMonth(shown.value, by), active.value))
  void focusActive()
}

function onKey(event: KeyboardEvent) {
  const moves: Record<string, () => string> = {
    ArrowLeft: () => addDays(active.value, -1),
    ArrowRight: () => addDays(active.value, 1),
    ArrowUp: () => addDays(active.value, -7),
    ArrowDown: () => addDays(active.value, 7),
    Home: () => addDays(active.value, -weekday(active.value)),
    End: () => addDays(active.value, 6 - weekday(active.value)),
    PageUp: () => sameDayIn(shiftMonth(shown.value, -1), active.value),
    PageDown: () => sameDayIn(shiftMonth(shown.value, 1), active.value),
  }
  if (event.key in moves) {
    event.preventDefault()
    active.value = clamp(moves[event.key]!())
    void focusActive()
  } else if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    pick(active.value)
  } else if (event.key === 'Escape') {
    // Only the pop-up closes: a side panel behind it ignores an Escape already used.
    event.preventDefault()
    close()
  }
}
function onPopKey(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    event.preventDefault()
    close()
  } else if (event.key === 'Tab') {
    // Keep Tab inside the pop-up: month buttons, the grid's day, Today and Clear.
    const stops = [...(event.currentTarget as HTMLElement).querySelectorAll<HTMLElement>('button:not([disabled]):not([tabindex="-1"])')]
    const first = stops[0]
    const last = stops[stops.length - 1]
    if (!first || !last) return
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }
}
</script>

<template>
  <div ref="root" class="date-picker">
    <button
      :id="id"
      ref="button"
      type="button"
      class="input trigger"
      aria-haspopup="dialog"
      :aria-expanded="open"
      :aria-invalid="invalid || undefined"
      :aria-describedby="describedBy"
      :aria-label="`${label}: ${value ? fullDate(value) : placeholder}`"
      :disabled="disabled"
      @click="toggle"
    >
      <span :class="{ empty: !value }">{{ value ? formatDay(value) : placeholder }}</span>
      <CalendarDays class="icon" aria-hidden="true" />
    </button>

    <div v-if="open" class="scrim" aria-hidden="true" @pointerdown="close(false)" />
    <Transition name="pop" appear>
      <div
        v-if="open"
        class="pop"
        :class="{ up: place.up }"
        :style="popStyle"
        role="dialog"
        :aria-label="`${label} date`"
        @keydown="onPopKey"
      >
        <div class="head">
          <span :id="`${uid}-title`" class="title" aria-live="polite">{{ title }}</span>
          <button type="button" class="icon-btn" aria-label="Previous month" @click="moveMonth(-1)">
            <ChevronLeft aria-hidden="true" />
          </button>
          <button type="button" class="icon-btn" aria-label="Next month" @click="moveMonth(1)">
            <ChevronRight aria-hidden="true" />
          </button>
        </div>

        <table ref="grid" class="month" role="grid" :aria-labelledby="`${uid}-title`" @keydown="onKey">
          <thead>
            <tr>
              <th v-for="[short, long] in WEEKDAYS" :key="short" scope="col" :abbr="long">{{ short }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(week, w) in weeks" :key="w">
              <td v-for="day in week" :key="day" role="gridcell" :aria-selected="day === value">
                <button
                  type="button"
                  class="day"
                  :class="{
                    other: monthOf(day) !== shown,
                    today: day === today,
                    chosen: day === value,
                  }"
                  :tabindex="day === active ? 0 : -1"
                  :data-active="day === active || undefined"
                  :disabled="outOfRange(day)"
                  :aria-label="fullDate(day) + (day === today ? ', today' : '')"
                  :aria-current="day === today ? 'date' : undefined"
                  @click="pick(day)"
                >
                  {{ Number(day.slice(8, 10)) }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <div class="foot">
          <button v-if="clearable" type="button" class="link" :disabled="!value" @click="clear">Clear</button>
          <button type="button" class="link today-link" :disabled="outOfRange(today)" @click="pick(today)">Today</button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.date-picker {
  position: relative;
  width: 100%;
}
.trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  text-align: left;
  white-space: nowrap;
  cursor: pointer;
}
.trigger:disabled {
  cursor: not-allowed;
}
.trigger[aria-invalid='true'],
.trigger[aria-expanded='true'] {
  border-color: var(--color-crimson);
}
.empty {
  color: var(--color-placeholder);
}
.icon {
  flex: none;
  width: 16px;
  height: 16px;
  color: var(--color-intaglio);
}

/* Fixed to the window (placed by position()), so a panel's scroll area does not cut it off. */
.pop {
  position: fixed;
  z-index: 60;
  top: var(--pop-top, auto);
  bottom: var(--pop-bottom, auto);
  left: var(--pop-left, 16px);
  width: var(--pop-width, 292px);
  max-width: calc(100vw - 32px);
  padding: 12px 12px 8px;
  border: 1px solid var(--color-rule-strong);
  border-radius: 12px;
  background: var(--color-sheet);
  box-shadow: var(--shadow-toast);
  transform-origin: top left;
}
.pop.up {
  transform-origin: bottom left;
}
.head {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-bottom: 8px;
  padding-left: 6px;
}
.title {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
}
.month {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
.month th {
  padding: 2px 0 6px;
  font-size: 11px;
  font-weight: 500;
  color: var(--color-intaglio);
  text-align: center;
}
.month td {
  padding: 1px;
  text-align: center;
}
.day {
  display: grid;
  place-items: center;
  width: 100%;
  aspect-ratio: 1;
  max-height: 36px;
  border: 0;
  border-radius: 8px;
  background: none;
  color: var(--color-ink);
  font-family: var(--font-mono);
  font-size: 13px;
  cursor: pointer;
  transition:
    background-color 120ms ease,
    color 120ms ease;
}
.day:hover {
  background: var(--color-row-hover);
}
.day.other {
  color: var(--color-ink-off);
  opacity: 0.6;
}
.day.today {
  box-shadow: inset 0 0 0 1.5px var(--color-crimson);
  color: var(--color-crimson);
  font-weight: 600;
}
.day.chosen {
  background: var(--color-crimson-fill);
  color: #fff;
  font-weight: 600;
  opacity: 1;
}
.day:focus-visible {
  outline: 2px solid var(--color-crimson);
  outline-offset: 1px;
}
.day:disabled {
  color: var(--color-ink-disabled);
  opacity: 0.45;
  text-decoration: line-through;
  cursor: not-allowed;
  background: none;
}
.foot {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px solid var(--color-rule);
}
.link {
  padding: 6px 8px;
  border: 0;
  border-radius: 6px;
  background: none;
  color: var(--color-crimson);
  font: 500 13px var(--font-sans);
  cursor: pointer;
}
.today-link {
  margin-left: auto;
}
.link:hover:not(:disabled) {
  background: var(--color-crimson-wash);
}
.link:disabled {
  color: var(--color-ink-disabled);
  cursor: not-allowed;
}
.link:focus-visible {
  outline: 2px solid var(--color-crimson);
  outline-offset: 1px;
}
.scrim {
  display: none;
}

.pop-enter-active {
  transition:
    opacity 160ms var(--ease-out-quint),
    transform 160ms var(--ease-out-quint);
}
.pop-enter-from {
  opacity: 0;
  transform: translateY(-4px) scale(0.97);
}
.pop.up.pop-enter-from {
  transform: translateY(4px) scale(0.97);
}

/* Phone: the month opens from the bottom, over a scrim. */
@media (max-width: 640px) {
  .scrim {
    position: fixed;
    inset: 0;
    z-index: 59;
    display: block;
    background: var(--color-scrim);
  }
  .pop {
    top: auto;
    right: 0;
    bottom: 0;
    left: 0;
    width: auto;
    max-width: none;
    padding: 16px 16px calc(12px + env(safe-area-inset-bottom, 0px));
    border-radius: 16px 16px 0 0;
  }
  .day {
    max-height: 44px;
    font-size: 14px;
  }
  .pop-enter-active {
    transition: transform 240ms var(--ease-drawer);
  }
  .pop-enter-from,
  .pop.up.pop-enter-from {
    opacity: 1;
    transform: translateY(100%);
  }
}
</style>
