<script setup lang="ts">
// Rows (a time line by day) or Cards (photo cards): one choice for both IT pages, kept in this
// browser (owner decision, 6 Nov 2026).
import { LayoutGrid, Rows3 } from 'lucide-vue-next'

import { useUiStore } from '../../stores/ui'

const ui = useUiStore()
</script>

<template>
  <div class="view-switch" role="group" aria-label="Show setups as">
    <button type="button" :aria-pressed="ui.itView === 'rows'" @click="ui.setItView('rows')">
      <Rows3 aria-hidden="true" />Rows
    </button>
    <button type="button" :aria-pressed="ui.itView === 'cards'" @click="ui.setItView('cards')">
      <LayoutGrid aria-hidden="true" />Cards
    </button>
  </div>
</template>

<style scoped>
.view-switch {
  display: inline-flex;
  flex: none;
  height: 36px;
  padding: 3px;
  border: 1px solid var(--color-rule-strong);
  border-radius: 8px;
  background: var(--color-sheet);
}
.view-switch button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 12px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--color-intaglio);
  font: inherit;
  font-size: 13px;
  cursor: pointer;
  transition:
    background-color 140ms ease,
    color 140ms ease;
}
.view-switch button[aria-pressed='true'] {
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
  font-weight: 500;
}
.view-switch :deep(svg.lucide) {
  width: 15px;
  height: 15px;
}
</style>
