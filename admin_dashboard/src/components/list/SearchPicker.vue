<script lang="ts">
/** One choice in a SearchPicker. */
export interface PickerItem {
  value: number | string
  label: string
  /** More text the search matches (a Khmer name, a province). */
  keywords?: string
  /** A heading over this item and the ones after it with the same group (e.g. the office of a department). */
  group?: string
  /** Like group, but only a thin line marks where it starts (e.g. main offices, then branches). */
  section?: string
}

/**
 * The picker's words. `all` names the empty choice: "All offices" in a filter, "No owner" in an
 * optional field, "Choose an office" (shown greyed) in a required one.
 */
export interface PickerWords {
  all: string
  search: string
  unknown: string
  none: string
  /** The × button's name (filters only). */
  clear?: string
}

/** Lists longer than this get a search box. */
export const SEARCH_FROM = 6
</script>

<script setup lang="ts">
// The app's dropdown (owner decisions, 27 Oct 2026): a button that opens a short list, with a search
// box when the list is long, instead of the browser's own list. Filters (mode "filter", 184px) start
// with "All …" and clear with ×; form fields (mode "field", full width) say what to choose, take the
// field's error state, and offer the empty choice only when optional. Groups get a heading, sections
// a thin line. A chosen value not in the items reads words.unknown; the page decides which items
// to offer (G08). The list is fixed to the window so a panel's scroll area cannot cut it, and opens
// upward when there is no room below. On a phone it opens from the bottom.
import { Check, ChevronDown, Search, X } from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    id: string
    items: PickerItem[]
    words: PickerWords
    mode?: 'filter' | 'field'
    /** Field mode: offer the empty choice (words.all). Filters always offer it. */
    nullable?: boolean
    /** Show the search box; by default only for lists longer than SEARCH_FROM - 1. */
    searchable?: boolean
    disabled?: boolean
    invalid?: boolean
    describedBy?: string
  }>(),
  { mode: 'filter', nullable: false, searchable: undefined, disabled: false, invalid: false, describedBy: undefined },
)
const model = defineModel<number | string | null>({ required: true })

interface Row {
  value: number | string | null
  label: string
  /** Shown above the row: a thin line, and a heading when the row starts a named group. */
  line?: boolean
  heading?: string
}

const open = ref(false)
const query = ref('')
const active = ref(0)
const root = ref<HTMLElement | null>(null)
const button = ref<HTMLButtonElement | null>(null)
const input = ref<HTMLInputElement | null>(null)
const listEl = ref<HTMLElement | null>(null)
const listId = useId()

const isField = computed(() => props.mode === 'field')
const offersEmpty = computed(() => !isField.value || props.nullable)
const hasSearch = computed(() => props.searchable ?? props.items.length >= SEARCH_FROM)

const chosen = computed(() => props.items.find((i) => i.value === model.value) ?? null)
const label = computed(() =>
  model.value === null ? props.words.all : chosen.value ? chosen.value.label : props.words.unknown,
)
/** A required field with nothing chosen shows its prompt greyed, like a placeholder. */
const empty = computed(() => model.value === null && !offersEmpty.value)

const typed = computed(() => query.value.trim())
const matches = computed(() => {
  const q = typed.value.toLowerCase()
  if (!q) return props.items
  return props.items.filter(
    (i) => i.label.toLowerCase().includes(q) || (i.keywords ?? '').toLowerCase().includes(q) || (i.group ?? '').toLowerCase().includes(q),
  )
})
/** Every row in order: the empty choice and an unknown choice first (not while searching). */
const rows = computed<Row[]>(() => {
  const out: Row[] = []
  if (!typed.value && offersEmpty.value) out.push({ value: null, label: props.words.all })
  if (!typed.value && model.value !== null && !chosen.value) out.push({ value: model.value, label: props.words.unknown })
  let previous: string | undefined
  matches.value.forEach((item, index) => {
    const key = item.group ?? item.section
    const starts = index === 0 || key !== previous
    out.push({
      value: item.value,
      label: item.label,
      line: starts && (index > 0 || out.length > 0 && !!item.group),
      heading: starts && item.group ? item.group : undefined,
    })
    previous = key
  })
  return out
})

/** The text in pieces, the search match marked (bold), without v-html. */
function pieces(text: string) {
  const at = typed.value ? text.toLowerCase().indexOf(typed.value.toLowerCase()) : -1
  if (at < 0) return [{ text, hit: false }]
  const end = at + typed.value.length
  return [
    { text: text.slice(0, at), hit: false },
    { text: text.slice(at, end), hit: true },
    { text: text.slice(end), hit: false },
  ].filter((p) => p.text)
}

const optionId = (index: number) => `${listId}-${index}`

// Where the list sits: fixed to the window under the button, or above it when there is no room below.
const place = ref({ left: 0, top: 'auto', bottom: 'auto', width: 300, max: 400, up: false })
function position() {
  const rect = button.value?.getBoundingClientRect()
  if (!rect) return
  const below = window.innerHeight - rect.bottom - 12
  const above = rect.top - 12
  const up = below < 260 && above > below
  const width = Math.min(Math.max(rect.width, 300), window.innerWidth - 32)
  place.value = {
    left: Math.max(16, Math.min(rect.left, window.innerWidth - width - 16)),
    top: up ? 'auto' : `${rect.bottom + 6}px`,
    bottom: up ? `${window.innerHeight - rect.top + 6}px` : 'auto',
    width,
    max: Math.max(160, Math.min(400, (up ? above : below) - 6)),
    up,
  }
}
const popStyle = computed(() => ({
  '--pop-left': `${place.value.left}px`,
  '--pop-top': place.value.top,
  '--pop-bottom': place.value.bottom,
  '--pop-width': `${place.value.width}px`,
  '--pop-max': `${place.value.max}px`,
}))

function onOutside(event: Event) {
  if (root.value && !root.value.contains(event.target as Node)) close(false)
}
function onMove() {
  position()
}
watch(open, (isOpen) => {
  const method = isOpen ? 'addEventListener' : 'removeEventListener'
  document[method]('pointerdown', onOutside)
  window[method]('resize', onMove)
  window[method]('scroll', onMove, true)
})
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onOutside)
  window.removeEventListener('resize', onMove)
  window.removeEventListener('scroll', onMove, true)
})

async function show() {
  if (props.disabled) return
  query.value = ''
  position()
  open.value = true
  active.value = Math.max(0, rows.value.findIndex((r) => r.value === model.value))
  await nextTick()
  if (hasSearch.value) input.value?.focus()
  else listEl.value?.focus()
  scrollActive()
}
function close(focusButton = true) {
  open.value = false
  if (focusButton) void nextTick(() => button.value?.focus())
}
function toggle() {
  if (open.value) close()
  else void show()
}
function choose(row: Row | undefined) {
  if (!row) return
  model.value = row.value
  close()
}

function scrollActive() {
  void nextTick(() => listEl.value?.querySelector('[data-active]')?.scrollIntoView?.({ block: 'nearest' }))
}
watch(typed, () => {
  active.value = 0
})
watch(active, scrollActive)

function onKey(event: KeyboardEvent) {
  const last = rows.value.length - 1
  const moves: Record<string, number> = {
    ArrowDown: Math.min(active.value + 1, last),
    ArrowUp: Math.max(active.value - 1, 0),
    Home: 0,
    End: last,
  }
  if (event.key in moves) {
    event.preventDefault()
    active.value = moves[event.key]!
  } else if (event.key === 'Enter' || (event.key === ' ' && !hasSearch.value)) {
    event.preventDefault()
    choose(rows.value[active.value])
  } else if (event.key === 'Escape') {
    // Only the list closes: a side panel behind it ignores an Escape already used.
    event.preventDefault()
    close()
  } else if (event.key === 'Tab') {
    close(false)
  }
}
</script>

<template>
  <div ref="root" class="picker" :class="{ field: isField }">
    <button
      :id="id"
      ref="button"
      type="button"
      class="input trigger"
      :class="{ set: !isField && model !== null, empty, clearable: !isField && model !== null }"
      aria-haspopup="listbox"
      :aria-expanded="open"
      :aria-controls="open ? listId : undefined"
      :aria-invalid="invalid || undefined"
      :aria-describedby="describedBy"
      :disabled="disabled"
      :title="model !== null ? label : undefined"
      @click="toggle"
    >
      <span class="label">{{ label }}</span>
      <ChevronDown v-if="isField || model === null" class="chev" aria-hidden="true" />
    </button>
    <button v-if="!isField && model !== null" type="button" class="clear" :aria-label="words.clear" @click="model = null">
      <X aria-hidden="true" />
    </button>

    <div v-if="open" class="scrim" aria-hidden="true" @pointerdown="close(false)" />
    <Transition name="pop" appear>
      <div v-if="open" class="pop" :class="{ up: place.up }" :style="popStyle">
        <label v-if="hasSearch" class="search">
          <Search aria-hidden="true" />
          <input
            ref="input"
            v-model="query"
            type="search"
            :placeholder="words.search"
            role="combobox"
            :aria-label="words.search"
            aria-autocomplete="list"
            aria-expanded="true"
            :aria-controls="listId"
            :aria-activedescendant="rows.length ? optionId(active) : undefined"
            autocomplete="off"
            @keydown="onKey"
          />
        </label>
        <ul
          :id="listId"
          ref="listEl"
          class="list"
          role="listbox"
          :aria-label="words.search"
          :tabindex="hasSearch ? undefined : 0"
          :aria-activedescendant="!hasSearch && rows.length ? optionId(active) : undefined"
          @keydown="hasSearch ? undefined : onKey($event)"
        >
          <template v-for="(row, index) in rows" :key="String(row.value)">
            <li v-if="row.line" class="line" role="separator" />
            <li v-if="row.heading" class="heading" role="presentation">{{ row.heading }}</li>
            <li
              :id="optionId(index)"
              class="opt"
              role="option"
              :aria-selected="row.value === model"
              :data-active="index === active || undefined"
              @mousedown.prevent
              @mousemove="active = index"
              @click="choose(row)"
            >
              <span class="name"><template v-for="(p, i) in pieces(row.label)" :key="i"><mark v-if="p.hit">{{ p.text }}</mark><template v-else>{{ p.text }}</template></template></span>
              <Check class="tick" aria-hidden="true" />
            </li>
          </template>
          <li v-if="!rows.length" class="none" role="presentation">{{ words.none }} “{{ typed }}”.</li>
        </ul>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
/* 184px keeps the Rooms filter row on one line at 1366px; a longer name ends in "…" (full name on hover). */
.picker {
  position: relative;
  width: 184px;
  max-width: 100%;
}
/* The same box as the other filters: the name fills it, the arrow (or ×) sits at the right edge. */
.trigger {
  display: flex;
  align-items: center;
  width: 100%;
  padding-right: 34px;
  text-align: left;
  cursor: pointer;
}
.picker.field {
  width: 100%;
}
.trigger.set {
  border-color: var(--color-intaglio);
  font-weight: 500;
}
.trigger.empty .label {
  color: var(--color-placeholder);
}
.trigger:disabled {
  cursor: not-allowed;
}
.trigger[aria-invalid='true'] {
  border-color: var(--color-crimson);
}
.trigger[aria-expanded='true'] {
  border-color: var(--color-crimson);
}
.label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.chev {
  position: absolute;
  top: 50%;
  right: 10px;
  width: 16px;
  height: 16px;
  transform: translateY(-50%);
  color: var(--color-intaglio);
  pointer-events: none;
}
.clear {
  position: absolute;
  top: 50%;
  right: 6px;
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  transform: translateY(-50%);
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--color-intaglio);
  cursor: pointer;
}
.clear:hover {
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
}
.clear svg.lucide {
  width: 14px;
  height: 14px;
}

/* Fixed to the window (placed by position()), so a panel's scroll area does not cut it off. */
.pop {
  position: fixed;
  z-index: 60;
  top: var(--pop-top, auto);
  bottom: var(--pop-bottom, auto);
  left: var(--pop-left, 16px);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  width: var(--pop-width, 300px);
  max-width: calc(100vw - 32px);
  max-height: var(--pop-max, 400px);
  overflow: hidden;
  border: 1px solid var(--color-rule-strong);
  border-radius: 12px;
  background: var(--color-sheet);
  box-shadow: var(--shadow-toast);
  transform-origin: top left;
}
.search {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--color-rule);
}
.search svg.lucide {
  flex: none;
  width: 16px;
  height: 16px;
  color: var(--color-intaglio);
}
.search input {
  flex: 1;
  min-width: 0;
  height: 30px;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--color-ink);
  font: inherit;
}
.search input::placeholder {
  color: var(--color-placeholder);
}
.pop.up {
  transform-origin: bottom left;
}
.list {
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
  display: grid;
  grid-template-columns: minmax(0, 1fr) 16px;
  align-items: center;
  gap: 12px;
  padding: 7px 10px;
  border-radius: 8px;
  cursor: pointer;
}
.opt[data-active] {
  background: var(--color-row-hover);
}
.name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.name mark {
  background: none;
  color: inherit;
  font-weight: 600;
}
.tick {
  width: 16px;
  height: 16px;
  color: var(--color-crimson);
  visibility: hidden;
}
.opt[aria-selected='true'] .name {
  color: var(--color-crimson);
  font-weight: 500;
}
.opt[aria-selected='true'] .tick {
  visibility: visible;
}
.line {
  height: 1px;
  margin: 4px 10px;
  background: var(--color-rule);
}
.heading {
  padding: 6px 10px 2px;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-intaglio);
}
.none {
  padding: 20px 10px;
  color: var(--color-intaglio);
  text-align: center;
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

/* Phone: the list opens from the bottom, over a scrim. */
@media (max-width: 640px) {
  .picker {
    width: 100%;
  }
  .pop.up.pop-enter-from {
    transform: translateY(100%);
  }
  .scrim {
    position: fixed;
    inset: 0;
    z-index: 59;
    display: block;
    background: var(--color-scrim);
  }
  .pop {
    position: fixed;
    top: auto;
    right: 0;
    bottom: 0;
    left: 0;
    width: auto;
    max-width: none;
    max-height: 75vh;
    padding-bottom: env(safe-area-inset-bottom, 0px);
    border-radius: 16px 16px 0 0;
  }
  .pop-enter-active {
    transition: transform 240ms var(--ease-drawer);
  }
  .pop-enter-from {
    opacity: 1;
    transform: translateY(100%);
  }
}
</style>
