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

/** The picker's words, e.g. "All offices", "Search offices", "Unknown office", "No office matches", "Show all offices". */
export interface PickerWords {
  all: string
  search: string
  unknown: string
  none: string
  clear: string
}
</script>

<script setup lang="ts">
// A filter button that opens a short search list instead of a long browser list (owner decision,
// 27 Oct 2026, first for the Rooms office filter). "All …" comes first; groups get a heading, sections
// a thin line. A chosen value not in the items shows as words.unknown. The page decides which items to
// offer (G08: the ones that are off, only when chosen). On a phone the list opens from the bottom.
import { Check, ChevronDown, Search, X } from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'

const props = defineProps<{ id: string; items: PickerItem[]; words: PickerWords }>()
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

const chosen = computed(() => props.items.find((i) => i.value === model.value) ?? null)
const label = computed(() =>
  model.value === null ? props.words.all : chosen.value ? chosen.value.label : props.words.unknown,
)

const typed = computed(() => query.value.trim())
const matches = computed(() => {
  const q = typed.value.toLowerCase()
  if (!q) return props.items
  return props.items.filter(
    (i) => i.label.toLowerCase().includes(q) || (i.keywords ?? '').toLowerCase().includes(q) || (i.group ?? '').toLowerCase().includes(q),
  )
})
/** Every row in order: "All …" and an unknown choice first (not while searching). */
const rows = computed<Row[]>(() => {
  const out: Row[] = []
  if (!typed.value) out.push({ value: null, label: props.words.all })
  if (!typed.value && model.value !== null && !chosen.value) out.push({ value: model.value, label: props.words.unknown })
  let previous: string | undefined
  matches.value.forEach((item, index) => {
    const key = item.group ?? item.section
    const starts = index === 0 || key !== previous
    out.push({
      value: item.value,
      label: item.label,
      line: starts && index > 0,
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

function onOutside(event: Event) {
  if (root.value && !root.value.contains(event.target as Node)) close(false)
}
watch(open, (isOpen) => {
  if (isOpen) document.addEventListener('pointerdown', onOutside)
  else document.removeEventListener('pointerdown', onOutside)
})
onBeforeUnmount(() => document.removeEventListener('pointerdown', onOutside))

async function show() {
  query.value = ''
  open.value = true
  active.value = Math.max(0, rows.value.findIndex((r) => r.value === model.value))
  await nextTick()
  input.value?.focus()
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
  } else if (event.key === 'Enter') {
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
  <div ref="root" class="picker">
    <button
      :id="id"
      ref="button"
      type="button"
      class="input trigger"
      :class="{ set: model !== null }"
      aria-haspopup="listbox"
      :aria-expanded="open"
      :aria-controls="open ? listId : undefined"
      :title="model !== null ? label : undefined"
      @click="toggle"
    >
      <span class="label">{{ label }}</span>
      <ChevronDown v-if="model === null" class="chev" aria-hidden="true" />
    </button>
    <button v-if="model !== null" type="button" class="clear" :aria-label="words.clear" @click="model = null">
      <X aria-hidden="true" />
    </button>

    <div v-if="open" class="scrim" aria-hidden="true" @pointerdown="close(false)" />
    <Transition name="pop" appear>
      <div v-if="open" class="pop">
        <label class="search">
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
        <ul :id="listId" ref="listEl" class="list" role="listbox" :aria-label="words.search">
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
.trigger.set {
  border-color: var(--color-intaglio);
  font-weight: 500;
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

.pop {
  position: absolute;
  z-index: 30;
  top: calc(100% + 6px);
  left: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  width: 300px;
  max-width: calc(100vw - 32px);
  max-height: 400px;
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
.list {
  margin: 0;
  padding: 6px;
  overflow-y: auto;
  overscroll-behavior: contain;
  list-style: none;
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

/* Phone: the list opens from the bottom, over a scrim. */
@media (max-width: 640px) {
  .picker {
    width: 100%;
  }
  .scrim {
    position: fixed;
    inset: 0;
    z-index: 29;
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
