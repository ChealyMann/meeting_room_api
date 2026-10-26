<script setup lang="ts">
import type { Status } from '../../composables/useListQuery'

const model = defineModel<Status>({ required: true })

const OPTIONS: Array<{ value: Status; label: string }> = [
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
  { value: 'all', label: 'All' },
]
</script>

<template>
  <div class="segmented" role="group" aria-label="Status">
    <button
      v-for="option in OPTIONS"
      :key="option.value"
      type="button"
      :aria-pressed="model === option.value"
      @click="model = option.value"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<style scoped>
.segmented {
  display: inline-flex;
  height: 36px;
  padding: 3px;
  border: 1px solid var(--color-rule-strong);
  border-radius: 8px;
  background: var(--color-sheet);
}
.segmented button {
  padding: 0 12px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--color-intaglio);
  font-size: 13px;
  cursor: pointer;
  transition:
    background-color 140ms ease,
    color 140ms ease;
}
.segmented button[aria-pressed='true'] {
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
  font-weight: 500;
}
</style>
