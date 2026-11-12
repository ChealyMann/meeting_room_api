<script setup lang="ts">
// The four steps in a soft segmented bar; a finished step has a green tick and can be opened again.
import { Check } from 'lucide-vue-next'

defineProps<{ steps: string[]; current: number; reachable: (step: number) => boolean }>()
const emit = defineEmits<{ jump: [number] }>()
</script>

<template>
  <ol class="bf-steps" aria-label="Steps">
    <li v-for="(name, i) in steps" :key="name">
      <button
        type="button"
        :class="{ on: i + 1 === current, done: i + 1 < current }"
        :disabled="!reachable(i + 1)"
        :aria-current="i + 1 === current ? 'step' : undefined"
        :aria-label="`${i + 1}. ${name}`"
        @click="emit('jump', i + 1)"
      >
        <span class="n"><Check v-if="i + 1 < current" :size="12" :stroke-width="3" /><template v-else>{{ i + 1 }}</template></span>
        <span class="t">{{ name }}</span>
      </button>
    </li>
  </ol>
</template>

<style scoped>
.bf-steps {
  display: inline-flex;
  gap: 2px;
  margin: 0;
  padding: 3px;
  border-radius: 12px;
  background: var(--color-field-disabled);
  list-style: none;
}
.bf-steps li {
  display: flex;
}
button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 34px;
  padding: 0 12px 0 6px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: var(--color-intaglio);
  font: inherit;
  font-size: 13.5px;
  white-space: nowrap;
  cursor: pointer;
  transition: background-color 160ms ease, color 160ms ease, box-shadow 160ms ease, transform 160ms var(--ease-out-quint);
}
button:active:not(:disabled) {
  transform: scale(0.97);
}
button:disabled {
  color: var(--color-ink-off);
  cursor: default;
}
button.on {
  background: var(--color-sheet);
  color: var(--color-ink);
  font-weight: 500;
  box-shadow: 0 1px 3px rgba(42, 28, 19, 0.14);
}
.n {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--color-sheet);
  color: var(--color-intaglio);
  font-size: 11.5px;
  font-weight: 600;
  transition: background-color 200ms ease, color 200ms ease;
}
button.on .n {
  background: var(--color-crimson-fill);
  color: #fff;
}
button.done .n {
  background: var(--color-ok);
  color: #fff;
}
@media (hover: hover) and (pointer: fine) {
  button:not(.on):not(:disabled):hover {
    color: var(--color-ink);
  }
}
@media (max-width: 640px) {
  button:not(.on) .t {
    display: none;
  }
}
</style>
