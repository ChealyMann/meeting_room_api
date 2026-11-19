<script setup lang="ts">
// A filter chip with a small box under it (Find a room). Not set: a light chip with a ▾. Set: a
// dark chip with its value and × to clear it. The box closes with Done, Escape, or a click outside.
import { ChevronDown, X } from 'lucide-vue-next'
import { onBeforeUnmount, ref, useId, watch } from 'vue'

defineProps<{ label: string; set: boolean; wide?: boolean }>()
const emit = defineEmits<{ clear: []; close: [] }>()
const open = ref(false)
const root = ref<HTMLElement | null>(null)
const boxId = useId()

function close() {
  if (!open.value) return
  open.value = false
  emit('close')
}
function clearIt() {
  close()
  emit('clear')
}
function onDocClick(event: MouseEvent) {
  if (root.value && !root.value.contains(event.target as Node)) close()
}
function onKey(event: KeyboardEvent) {
  // An Escape a list inside already used (the time picker) closes only that list.
  if (event.key === 'Escape' && !event.defaultPrevented) close()
}
watch(open, (now) => {
  if (now) {
    document.addEventListener('mousedown', onDocClick)
    document.addEventListener('keydown', onKey)
  } else {
    document.removeEventListener('mousedown', onDocClick)
    document.removeEventListener('keydown', onKey)
  }
})
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onDocClick)
  document.removeEventListener('keydown', onKey)
})
defineExpose({ close })
</script>

<template>
  <div ref="root" class="f-chip-wrap">
    <div class="f-chip" :class="{ set, open }">
      <button type="button" class="f-open" :aria-expanded="open" :aria-controls="boxId" @click="open ? close() : (open = true)">
        <slot name="icon" />
        <span class="f-label">{{ label }}</span>
        <ChevronDown v-if="!set" :size="14" aria-hidden="true" />
      </button>
      <button v-if="set" type="button" class="f-clear" :aria-label="`Clear ${label}`" @click="clearIt">
        <X :size="11" aria-hidden="true" />
      </button>
    </div>
    <div v-if="open" :id="boxId" class="f-box" :class="{ wide }" role="dialog" :aria-label="label">
      <slot />
      <button type="button" class="f-done" @click="close">Done</button>
    </div>
  </div>
</template>

<style scoped>
.f-chip-wrap {
  position: relative;
}
.f-chip {
  display: inline-flex;
  align-items: center;
  height: 40px;
  border: 1px solid var(--color-rule-strong);
  border-radius: 999px;
  background: var(--color-sheet);
  color: var(--color-ink);
  transition: background-color 150ms ease, border-color 150ms ease, color 150ms ease;
}
.f-chip.set {
  border-color: var(--color-ink);
  background: var(--color-ink);
  color: var(--color-sheet);
}
.f-open {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 100%;
  padding: 0 14px;
  border: 0;
  border-radius: 999px;
  background: none;
  color: inherit;
  font: inherit;
  font-size: 13.5px;
  white-space: nowrap;
  cursor: pointer;
}
.f-chip.set .f-open {
  padding-right: 6px;
}
.f-label {
  max-width: 340px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.f-clear {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  margin-right: 8px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  color: inherit;
  cursor: pointer;
}
.f-box {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  z-index: 20;
  display: grid;
  gap: 12px;
  min-width: 280px;
  padding: 16px;
  border-radius: 16px;
  background: var(--color-sheet);
  box-shadow: 0 14px 34px rgba(42, 28, 19, 0.16), 0 2px 6px rgba(42, 28, 19, 0.08);
  color: var(--color-ink);
}
.f-box.wide {
  min-width: 360px;
}
.f-done {
  justify-self: end;
  height: 34px;
  padding: 0 14px;
  border: 0;
  border-radius: 10px;
  background: var(--color-ink);
  color: var(--color-sheet);
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}
@media (hover: hover) and (pointer: fine) {
  .f-chip:not(.set):hover {
    border-color: var(--color-intaglio);
  }
}
@media (max-width: 760px) {
  .f-box,
  .f-box.wide {
    position: fixed;
    top: auto;
    right: 12px;
    bottom: 12px;
    left: 12px;
    min-width: 0;
    max-height: 80vh;
    overflow: auto;
  }
  .f-label {
    max-width: 220px;
  }
}
</style>
