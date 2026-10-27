<script setup lang="ts">
// Picks an equipment item's icon (DSH-C02): a preview of the choice, a search, a grid of
// icons (one radio group, arrow keys move) and "No icon". The value is the Lucide name; a
// stored name that is not in the list is kept and previewed as "Unknown icon".
import { CircleHelp } from 'lucide-vue-next'
import { computed, nextTick, ref } from 'vue'

import { EQUIPMENT_ICONS, iconFor } from '../utils/equipmentIcons'

defineProps<{ id: string }>()
const model = defineModel<string | null>({ required: true })

const query = ref('')
const shown = computed(() => {
  const words = query.value.trim().toLowerCase()
  if (!words) return EQUIPMENT_ICONS
  return EQUIPMENT_ICONS.filter((i) => i.name.includes(words) || i.label.toLowerCase().includes(words))
})

const chosen = computed(() => EQUIPMENT_ICONS.find((i) => i.name === model.value) ?? null)
const unknown = computed(() => !!model.value && !iconFor(model.value))

// One tab stop for the grid: the chosen icon when shown, else the first one.
const tabStop = computed(() => (shown.value.some((i) => i.name === model.value) ? model.value : shown.value[0]?.name))

const buttons = ref<HTMLButtonElement[]>([])
async function move(from: number, step: number) {
  const list = shown.value
  if (!list.length) return
  const next = step === Infinity ? list.length - 1 : step === -Infinity ? 0 : (from + step + list.length) % list.length
  model.value = list[next]!.name
  await nextTick()
  buttons.value[next]?.focus()
}
function onKey(event: KeyboardEvent, index: number) {
  const steps: Record<string, number> = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1, Home: -Infinity, End: Infinity }
  const step = steps[event.key]
  if (step === undefined) return
  event.preventDefault()
  void move(index, step)
}
</script>

<template>
  <div class="icon-picker">
    <div class="preview" aria-live="polite">
      <span class="swatch" :class="{ empty: !model, unknown }">
        <component :is="chosen.icon" v-if="chosen" aria-hidden="true" />
        <CircleHelp v-else-if="unknown" aria-hidden="true" />
      </span>
      <span v-if="chosen" class="words">
        <b>{{ chosen.label }}</b>
        <span class="mono">{{ chosen.name }}</span>
      </span>
      <span v-else-if="unknown" class="words">
        <b>Unknown icon</b>
        <span class="mono stored">{{ model }}</span>
      </span>
      <span v-else class="words"><b>No icon</b></span>
    </div>

    <div class="tools">
      <input
        v-model="query"
        class="input"
        type="search"
        placeholder="Search icons"
        aria-label="Search icons"
        :aria-controls="`${id}-grid`"
      />
      <button type="button" class="none-btn" :aria-pressed="model === null" @click="model = null">No icon</button>
    </div>

    <div v-if="shown.length" :id="`${id}-grid`" class="grid" role="radiogroup" aria-label="Icons">
      <button
        v-for="(item, index) in shown"
        :key="item.name"
        ref="buttons"
        type="button"
        role="radio"
        :aria-checked="item.name === model"
        :aria-label="item.label"
        :title="item.label"
        :tabindex="item.name === tabStop ? 0 : -1"
        @click="model = item.name"
        @keydown="onKey($event, index)"
      >
        <component :is="item.icon" aria-hidden="true" />
      </button>
    </div>
    <p v-else :id="`${id}-grid`" class="no-match">No icons match.</p>
  </div>
</template>

<style scoped>
.icon-picker {
  display: grid;
  gap: 10px;
  min-width: 0;
}
.preview {
  display: flex;
  align-items: center;
  gap: 12px;
}
.swatch {
  display: grid;
  flex: none;
  place-items: center;
  width: 56px;
  height: 56px;
  border: 1px solid var(--color-rule-strong);
  border-radius: 10px;
  background: var(--color-paper);
  color: var(--color-ink);
}
.swatch svg.lucide {
  width: 32px;
  height: 32px;
}
.swatch.empty {
  border-style: dashed;
}
.swatch.unknown {
  color: var(--color-ink-off);
}
.words {
  display: grid;
  min-width: 0;
}
.words b {
  font-size: 13.5px;
  font-weight: 500;
}
.words .mono {
  font-size: 12px;
  color: var(--color-intaglio);
  overflow-wrap: anywhere;
}
.tools {
  display: flex;
  gap: 8px;
}
.tools .input {
  flex: 1;
  min-width: 0;
}
.none-btn {
  flex: none;
  padding: 0 12px;
  border: 1px solid var(--color-rule-strong);
  border-radius: 8px;
  background: var(--color-sheet);
  color: var(--color-ink);
  font-size: 13px;
}
.none-btn[aria-pressed='true'] {
  border-color: var(--color-crimson);
  color: var(--color-crimson);
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(40px, 1fr));
  gap: 6px;
  max-height: 188px;
  overflow-y: auto;
  padding: 2px;
}
.grid button {
  display: grid;
  place-items: center;
  height: 40px;
  border: 1px solid var(--color-rule);
  border-radius: 8px;
  background: var(--color-sheet);
  color: var(--color-ink);
  transition: border-color 120ms ease, background-color 120ms ease;
}
.grid button:hover {
  border-color: var(--color-rule-strong);
  background: var(--color-paper);
}
.grid button[aria-checked='true'] {
  border-color: var(--color-crimson);
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
}
.grid svg.lucide {
  width: 20px;
  height: 20px;
}
.no-match {
  margin: 0;
  padding: 12px 0;
  font-size: 13px;
  color: var(--color-intaglio);
}
</style>
