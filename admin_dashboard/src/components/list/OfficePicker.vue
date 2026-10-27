<script setup lang="ts">
// The office filter (owner decision, 27 Oct 2026): a button that opens a short search list
// instead of the long browser list of ~20 offices. Main offices first, a thin line, then the
// branches. G08: offices that are off are hidden unless chosen ("(off)"); a chosen id that is
// not in the list shows as "Unknown office". On a phone the list opens from the bottom.
import { Check, ChevronDown, Search, X } from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'

import type { LocationOut } from '../../api/types'

const props = defineProps<{ id: string; offices: LocationOut[] }>()
const model = defineModel<number | null>({ required: true })

interface Row {
  id: number | null
  name: string
}

const open = ref(false)
const query = ref('')
const active = ref(0)
const root = ref<HTMLElement | null>(null)
const button = ref<HTMLButtonElement | null>(null)
const input = ref<HTMLInputElement | null>(null)
const listEl = ref<HTMLElement | null>(null)
const listId = useId()

const nameOf = (o: LocationOut) => (o.is_active ? o.name_en : `${o.name_en} (off)`)
const isBranch = (o: LocationOut) => /\bbranch$/i.test(o.name_en.trim())

const chosen = computed(() => props.offices.find((o) => o.id === model.value) ?? null)
const label = computed(() =>
  model.value === null ? 'All offices' : chosen.value ? nameOf(chosen.value) : 'Unknown office',
)

const words = computed(() => query.value.trim())
const shown = computed(() => {
  const q = words.value.toLowerCase()
  return props.offices
    .filter((o) => o.is_active || o.id === model.value)
    .filter(
      (o) =>
        !q ||
        o.name_en.toLowerCase().includes(q) ||
        o.name_kh.includes(words.value) ||
        o.province.name_en.toLowerCase().includes(q),
    )
})
const mainRows = computed<Row[]>(() => shown.value.filter((o) => !isBranch(o)).map((o) => ({ id: o.id, name: nameOf(o) })))
const branchRows = computed<Row[]>(() => shown.value.filter(isBranch).map((o) => ({ id: o.id, name: nameOf(o) })))
/** Every row in order: "All offices" and an unknown choice first (not while searching). */
const rows = computed<Row[]>(() => [
  ...(words.value ? [] : [{ id: null, name: 'All offices' }]),
  ...(!words.value && model.value !== null && !chosen.value ? [{ id: model.value, name: 'Unknown office' }] : []),
  ...mainRows.value,
  ...branchRows.value,
])
/** Where the thin line goes: before the first branch, when main offices come before it. */
const lineBefore = computed(() =>
  mainRows.value.length && branchRows.value.length ? rows.value.length - branchRows.value.length : -1,
)

/** The text in pieces, the search match marked (bold), without v-html. */
function pieces(text: string) {
  const at = words.value ? text.toLowerCase().indexOf(words.value.toLowerCase()) : -1
  if (at < 0) return [{ text, hit: false }]
  const end = at + words.value.length
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
  active.value = Math.max(0, rows.value.findIndex((r) => r.id === model.value))
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
  model.value = row.id
  close()
}

function scrollActive() {
  void nextTick(() => listEl.value?.querySelector('[data-active]')?.scrollIntoView?.({ block: 'nearest' }))
}
watch(words, () => {
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
    <button v-if="model !== null" type="button" class="clear" aria-label="Show all offices" @click="model = null">
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
            placeholder="Search offices"
            role="combobox"
            aria-label="Search offices"
            aria-autocomplete="list"
            aria-expanded="true"
            :aria-controls="listId"
            :aria-activedescendant="rows.length ? optionId(active) : undefined"
            autocomplete="off"
            @keydown="onKey"
          />
        </label>
        <ul :id="listId" ref="listEl" class="list" role="listbox" aria-label="Offices">
          <template v-for="(row, index) in rows" :key="row.id ?? 'all'">
            <li v-if="index === lineBefore" class="line" role="separator" />
            <li
              :id="optionId(index)"
              class="opt"
              role="option"
              :aria-selected="row.id === model"
              :data-active="index === active || undefined"
              @mousedown.prevent
              @mousemove="active = index"
              @click="choose(row)"
            >
              <span class="name"><template v-for="(p, i) in pieces(row.name)" :key="i"><mark v-if="p.hit">{{ p.text }}</mark><template v-else>{{ p.text }}</template></template></span>
              <Check class="tick" aria-hidden="true" />
            </li>
          </template>
          <li v-if="!rows.length" class="none" role="presentation">No office matches “{{ words }}”.</li>
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
