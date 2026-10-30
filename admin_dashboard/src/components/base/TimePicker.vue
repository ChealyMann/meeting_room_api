<script setup lang="ts">
// A time field in the dashboard's own look, instead of the browser's time box (owner decision,
// 30 Oct 2026). The value stays "HH:MM" (24 hours, as the API takes it). The pop-up has an Hour
// column and a Minute column: pick the hour, then the minute, and it closes. Arrow keys move,
// Left/Right switch columns, Enter picks, Escape closes. Placed like the search pickers: fixed to
// the window, above the field when there is no room below.
import { Clock } from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    id: string
    /** The field's name, for the pop-up's accessible name ("Opening time"). */
    label: string
    invalid?: boolean
    describedBy?: string
    disabled?: boolean
    /** Minutes between choices. */
    step?: number
  }>(),
  { invalid: false, describedBy: undefined, disabled: false, step: 5 },
)

const model = defineModel<string>({ required: true })

type Column = 'hour' | 'minute'

const pad = (n: number) => String(n).padStart(2, '0')
const HOURS = Array.from({ length: 24 }, (_, i) => pad(i))

const valid = computed(() => /^\d{2}:\d{2}$/.test(model.value))
const hour = computed(() => (valid.value ? model.value.slice(0, 2) : '08'))
const minute = computed(() => (valid.value ? model.value.slice(3, 5) : '00'))
// The steps, plus a minute already set off them (e.g. 08:07), so it shows as chosen.
const minutes = computed(() => {
  const list = Array.from({ length: Math.ceil(60 / props.step) }, (_, i) => pad(i * props.step))
  return list.includes(minute.value) ? list : [...list, minute.value].sort()
})

const uid = useId()
const open = ref(false)
const column = ref<Column>('hour')
const activeHour = ref(0)
const activeMinute = ref(0)
const root = ref<HTMLElement | null>(null)
const button = ref<HTMLButtonElement | null>(null)
const hourList = ref<HTMLElement | null>(null)
const minuteList = ref<HTMLElement | null>(null)

const optionId = (col: Column, index: number) => `${uid}-${col}-${index}`

// Where the pop-up sits: under the field, or above it when there is no room below.
const place = ref({ left: 0, top: 'auto', bottom: 'auto', width: 176, up: false })
function position() {
  const rect = button.value?.getBoundingClientRect()
  if (!rect) return
  const below = window.innerHeight - rect.bottom - 12
  const above = rect.top - 12
  const up = below < 260 && above > below
  const width = Math.min(Math.max(rect.width, 176), window.innerWidth - 32)
  place.value = {
    left: Math.max(16, Math.min(rect.left, window.innerWidth - width - 16)),
    top: up ? 'auto' : `${rect.bottom + 6}px`,
    bottom: up ? `${window.innerHeight - rect.top + 6}px` : 'auto',
    width,
    up,
  }
}
const popStyle = computed(() => ({
  '--pop-left': `${place.value.left}px`,
  '--pop-top': place.value.top,
  '--pop-bottom': place.value.bottom,
  '--pop-width': `${place.value.width}px`,
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

function listOf(col: Column) {
  return col === 'hour' ? hourList.value : minuteList.value
}
function scrollInto(col: Column, block: ScrollLogicalPosition = 'nearest') {
  void nextTick(() => listOf(col)?.querySelector('[data-active]')?.scrollIntoView?.({ block }))
}
async function focusColumn(col: Column) {
  column.value = col
  await nextTick()
  listOf(col)?.focus()
  scrollInto(col)
}

async function show() {
  if (props.disabled) return
  position()
  activeHour.value = Math.max(0, HOURS.indexOf(hour.value))
  activeMinute.value = Math.max(0, minutes.value.indexOf(minute.value))
  open.value = true
  await focusColumn('hour')
  scrollInto('hour', 'center')
  scrollInto('minute', 'center')
}
function close(focusButton = true) {
  open.value = false
  if (focusButton) void nextTick(() => button.value?.focus())
}
function toggle() {
  if (open.value) close()
  else void show()
}

function pickHour(index: number) {
  activeHour.value = index
  model.value = `${HOURS[index]}:${minute.value}`
  void focusColumn('minute')
}
function pickMinute(index: number) {
  activeMinute.value = index
  model.value = `${hour.value}:${minutes.value[index]}`
  close()
}

function onKey(col: Column, event: KeyboardEvent) {
  const active = col === 'hour' ? activeHour : activeMinute
  const last = (col === 'hour' ? HOURS : minutes.value).length - 1
  const moves: Record<string, number> = {
    ArrowDown: Math.min(active.value + 1, last),
    ArrowUp: Math.max(active.value - 1, 0),
    Home: 0,
    End: last,
  }
  if (event.key in moves) {
    event.preventDefault()
    active.value = moves[event.key]!
    scrollInto(col)
  } else if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    if (col === 'hour') pickHour(active.value)
    else pickMinute(active.value)
  } else if (event.key === 'ArrowRight' && col === 'hour') {
    event.preventDefault()
    void focusColumn('minute')
  } else if (event.key === 'ArrowLeft' && col === 'minute') {
    event.preventDefault()
    void focusColumn('hour')
  } else if (event.key === 'Escape') {
    // Only the pop-up closes: a side panel behind it ignores an Escape already used.
    event.preventDefault()
    close()
  } else if (event.key === 'Tab') {
    close(false)
  }
}
</script>

<template>
  <div ref="root" class="time-picker">
    <button
      :id="id"
      ref="button"
      type="button"
      class="input trigger mono"
      aria-haspopup="dialog"
      :aria-expanded="open"
      :aria-invalid="invalid || undefined"
      :aria-describedby="describedBy"
      :disabled="disabled"
      @click="toggle"
    >
      <span :class="{ empty: !valid }">{{ valid ? model : '--:--' }}</span>
      <Clock class="icon" aria-hidden="true" />
    </button>

    <div v-if="open" class="scrim" aria-hidden="true" @pointerdown="close(false)" />
    <Transition name="pop" appear>
      <div v-if="open" class="pop" :class="{ up: place.up }" :style="popStyle" role="dialog" :aria-label="`${label} time`">
        <div class="col">
          <span class="col-head" aria-hidden="true">Hour</span>
          <ul
            ref="hourList"
            class="list"
            role="listbox"
            aria-label="Hour"
            tabindex="0"
            :aria-activedescendant="optionId('hour', activeHour)"
            @keydown="onKey('hour', $event)"
            @focus="column = 'hour'"
          >
            <li
              v-for="(h, index) in HOURS"
              :id="optionId('hour', index)"
              :key="h"
              class="opt"
              role="option"
              :aria-selected="h === hour"
              :data-active="index === activeHour || undefined"
              :data-current="(column === 'hour' && index === activeHour) || undefined"
              @mousedown.prevent
              @click="pickHour(index)"
            >
              {{ h }}
            </li>
          </ul>
        </div>
        <div class="col">
          <span class="col-head" aria-hidden="true">Min</span>
          <ul
            ref="minuteList"
            class="list"
            role="listbox"
            aria-label="Minute"
            tabindex="0"
            :aria-activedescendant="optionId('minute', activeMinute)"
            @keydown="onKey('minute', $event)"
            @focus="column = 'minute'"
          >
            <li
              v-for="(m, index) in minutes"
              :id="optionId('minute', index)"
              :key="m"
              class="opt"
              role="option"
              :aria-selected="m === minute"
              :data-active="index === activeMinute || undefined"
              :data-current="(column === 'minute' && index === activeMinute) || undefined"
              @mousedown.prevent
              @click="pickMinute(index)"
            >
              {{ m }}
            </li>
          </ul>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.time-picker {
  position: relative;
  width: 100%;
}
.trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  text-align: left;
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
  display: grid;
  grid-template-columns: 1fr 1fr;
  width: var(--pop-width, 176px);
  max-width: calc(100vw - 32px);
  overflow: hidden;
  border: 1px solid var(--color-rule-strong);
  border-radius: 12px;
  background: var(--color-sheet);
  box-shadow: var(--shadow-toast);
  transform-origin: top left;
}
.pop.up {
  transform-origin: bottom left;
}
.col + .col {
  border-left: 1px solid var(--color-rule);
}
.col-head {
  display: block;
  padding: 8px 0 6px;
  border-bottom: 1px solid var(--color-rule);
  font-size: 10.5px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-align: center;
  text-transform: uppercase;
  color: var(--color-intaglio);
}
.list {
  height: 224px;
  margin: 0;
  padding: 6px;
  overflow-y: auto;
  overscroll-behavior: contain;
  list-style: none;
}
.list:focus {
  outline: none;
}
.opt {
  padding: 6px 0;
  border-radius: 7px;
  font-family: var(--font-mono);
  font-size: 13.5px;
  text-align: center;
  cursor: pointer;
}
.opt:hover,
.opt[data-current] {
  background: var(--color-row-hover);
}
.list:focus-visible .opt[data-current] {
  box-shadow: inset 0 0 0 1.5px var(--color-crimson);
}
.opt[aria-selected='true'] {
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
  font-weight: 600;
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

/* Phone: the columns open from the bottom, over a scrim. */
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
    padding-bottom: env(safe-area-inset-bottom, 0px);
    border-radius: 16px 16px 0 0;
  }
  .list {
    height: 40vh;
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
