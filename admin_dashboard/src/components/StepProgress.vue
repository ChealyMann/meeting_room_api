<script setup lang="ts">
// The steps of a booking as a thin bar (owner pick, 16 Nov 2026, look B): one segment per step,
// green done, amber now, crimson stopped, grey to come; under it "Step 2 of 4" and where it
// is ("Waiting for Pitika"). Used on top of every booking pop-up.
import { computed } from 'vue'

import type { ProcessStep } from '../utils/bookingHistory'

const props = defineProps<{
  steps: ProcessStep[]
  /** The words on the right; empty hides them (the booker's status band says it already). */
  label?: string
}>()

const NOW_WORDS: Record<string, string> = {
  Pitika: 'Waiting for Pitika',
  'Room owner': 'Waiting for the room owner',
  'IT setup': 'IT is setting up the room',
}
const SPOKEN = { done: 'done', stop: 'stopped here', now: 'now', todo: 'not yet' } as const

const where = computed(() => {
  const steps = props.steps
  const stop = steps.findIndex((s) => s.state === 'stop')
  const now = steps.findIndex((s) => s.state === 'now')
  if (stop >= 0) {
    const s = steps[stop]!
    return { at: stop + 1, tone: 'stop', words: s.label === 'Cancelled' ? 'Cancelled' : `Stopped at ${s.label}` }
  }
  if (now >= 0) {
    const s = steps[now]!
    return { at: now + 1, tone: 'wait', words: NOW_WORDS[s.label] ?? `Waiting for ${s.label}` }
  }
  // Nothing waiting: it is at the last step that is done.
  const last = steps.map((s) => s.state).lastIndexOf('done')
  return { at: last + 1, tone: 'ok', words: steps[last]?.label ?? '' }
})
const words = computed(() => props.label ?? where.value.words)
</script>

<template>
  <div class="step-progress">
    <ol class="bar" aria-label="Steps" :style="{ gridTemplateColumns: `repeat(${steps.length}, minmax(0, 1fr))` }">
      <li v-for="(s, i) in steps" :key="i" class="seg" :class="s.state" :title="s.label">
        <span class="sr-only">{{ s.label }}, {{ SPOKEN[s.state] }}</span>
      </li>
    </ol>
    <p class="line">
      <span>Step {{ where.at }} of {{ steps.length }}</span>
      <b v-if="words" :class="where.tone">{{ words }}</b>
    </p>
  </div>
</template>

<style scoped>
.bar {
  display: grid;
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.seg {
  height: 4px;
  border-radius: 4px;
  background: var(--color-rule);
}
.seg.done {
  background: var(--color-ok);
}
.seg.now {
  background: var(--color-warn);
}
.seg.stop {
  background: var(--color-crimson);
}
.line {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin: 6px 0 0;
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.line b {
  font-weight: 500;
  text-align: right;
}
.line .ok {
  color: var(--color-ok);
}
.line .wait {
  color: var(--color-warn);
}
.line .stop {
  color: var(--color-crimson);
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
