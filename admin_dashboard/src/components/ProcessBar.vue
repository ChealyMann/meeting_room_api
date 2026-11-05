<script setup lang="ts">
// A booking's steps as circles on a line (DESIGN.md "Booking Panel", History). Done is filled
// ledger green with a check, stop crimson with an x, now a dashed amber ring with a clock, todo
// an empty ring. `gap` draws the line into a step as a dashed amber line: on the Pitika queue
// that gap is the Pitika's decision, waiting (owner pick, 5 Nov 2026: "gap is you").
import { Check, Clock, X } from 'lucide-vue-next'

export interface ProcessStep {
  label: string
  state: 'done' | 'stop' | 'now' | 'todo'
  gap?: boolean
}

withDefaults(defineProps<{ steps: ProcessStep[]; size?: 'small' | 'large' }>(), { size: 'small' })

const SPOKEN = { done: 'done', stop: 'stopped here', now: 'now', todo: 'not yet' } as const
</script>

<template>
  <ol class="process-bar" :class="size" aria-label="Steps">
    <li v-for="(s, i) in steps" :key="i" class="step" :class="[s.state, { gap: s.gap }]">
      <span class="c" aria-hidden="true">
        <Check v-if="s.state === 'done'" />
        <X v-else-if="s.state === 'stop'" />
        <Clock v-else-if="s.state === 'now'" />
      </span>
      <span class="n">{{ s.label }}</span>
      <span class="sr-only">, {{ s.gap ? 'after your decision, ' : '' }}{{ SPOKEN[s.state] }}</span>
    </li>
  </ol>
</template>

<style scoped>
.process-bar {
  --size: 20px;
  display: flex;
  margin: 0;
  padding: 0;
  list-style: none;
}
.process-bar.large {
  --size: 28px;
  padding: 14px 8px 12px;
  border-radius: 10px;
  background: var(--color-paper);
}
.step {
  position: relative;
  flex: 1;
  min-width: 0;
  display: grid;
  justify-items: center;
  gap: 4px;
  text-align: center;
}
.step:not(:first-child)::before {
  content: '';
  position: absolute;
  top: calc(var(--size) / 2 - 1px);
  right: 50%;
  width: 100%;
  height: 2px;
  background: var(--color-rule-strong);
}
.step:is(.done, .stop, .now):not(:first-child)::before {
  background: var(--color-ok);
}
.step.gap::before {
  height: 0;
  border-top: 2px dashed var(--color-warn);
  background: none !important;
}
.c {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  width: var(--size);
  height: var(--size);
  border: 2px solid var(--color-rule-strong);
  border-radius: 50%;
  background: var(--color-sheet);
  color: var(--color-ink-off);
}
.done .c {
  border-color: var(--color-ok);
  background: var(--color-ok);
  color: var(--color-sheet);
}
.stop .c {
  border-color: var(--color-crimson);
  background: var(--color-crimson);
  color: var(--color-sheet);
}
.now .c {
  border-color: var(--color-warn);
  border-style: dashed;
  background: color-mix(in srgb, var(--color-warn) 10%, var(--color-sheet));
  color: var(--color-warn);
}
.c :deep(svg.lucide) {
  width: calc(var(--size) / 2);
  height: calc(var(--size) / 2);
  stroke-width: 2.5;
}
.n {
  font-size: 10.5px;
  line-height: 1.2;
  color: var(--color-intaglio);
  overflow-wrap: anywhere;
}
.large .n {
  font-size: 11px;
}
.done .n {
  color: var(--color-ink);
}
.stop .n {
  color: var(--color-crimson);
  font-weight: 500;
}
.now .n {
  color: var(--color-warn);
  font-weight: 600;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}
</style>
