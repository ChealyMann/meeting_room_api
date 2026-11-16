<script setup lang="ts" generic="T extends string">
// The tab bar of a booking pop-up (owner pick, 16 Nov 2026): the same in To review, the room
// owner's review, IT setup and My bookings. Each tab is `tab-{id}` and controls `tabpanel-{id}`.
// The bar sticks to the top while the panel scrolls. Left and right arrows move between tabs.
import { ref } from 'vue'

defineProps<{ tabs: Array<{ id: T; label: string }> }>()
const model = defineModel<T>({ required: true })

const bar = ref<HTMLElement | null>(null)
function move(event: KeyboardEvent, step: number) {
  const buttons = [...(bar.value?.querySelectorAll<HTMLButtonElement>('[role="tab"]') ?? [])]
  const at = buttons.indexOf(event.target as HTMLButtonElement)
  const next = buttons[(at + step + buttons.length) % buttons.length]
  next?.focus()
  next?.click()
}
</script>

<template>
  <div ref="bar" class="tabs" role="tablist" aria-label="Booking">
    <button
      v-for="t in tabs"
      :id="`tab-${t.id}`"
      :key="t.id"
      type="button"
      role="tab"
      :aria-selected="model === t.id"
      :aria-controls="`tabpanel-${t.id}`"
      :tabindex="model === t.id ? 0 : -1"
      @click="model = t.id"
      @keydown.right.prevent="move($event, 1)"
      @keydown.left.prevent="move($event, -1)"
    >
      {{ t.label }}
    </button>
  </div>
</template>

<style scoped>
/* Sticky 16px higher than the panel body's top padding, with that strip filled by the bar's own
   background: rows scrolled under it never peek out above the tabs. Pop-ups take 16px off the
   space above the bar, so nothing moves before scrolling. */
.tabs {
  position: sticky;
  top: -16px;
  z-index: 2;
  display: flex;
  gap: 4px;
  margin-inline: -20px;
  padding: 16px 20px 0;
  overflow-x: auto;
  border-bottom: 1px solid var(--color-rule);
  background: var(--color-sheet);
}
.tabs button {
  flex: none;
  margin-bottom: -1px;
  padding: 10px;
  border: 0;
  border-bottom: 2px solid transparent;
  background: none;
  color: var(--color-intaglio);
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}
.tabs button[aria-selected='true'] {
  border-bottom-color: var(--color-crimson);
  color: var(--color-ink);
  font-weight: 500;
}
.tabs button:focus-visible {
  outline: 2px solid var(--color-ink);
  outline-offset: -2px;
}
@media (hover: hover) and (pointer: fine) {
  .tabs button:hover {
    color: var(--color-ink);
  }
}
</style>
