<script setup lang="ts">
// The To review head (spec 2026-11-05-pitika-decided-design, "Head"): today's ring, the title,
// one calm line, and the Waiting / Approved / Rejected switch with today's numbers.
import { computed, ref, watch } from 'vue'

import type { PitikaSummary } from '../../api/types'
import { ringArcs, summaryLine, type Tab } from '../../utils/decided'

const props = withDefaults(defineProps<{ summary: PitikaSummary | null; tab: Tab; title?: string }>(), { title: 'To review' })
const emit = defineEmits<{ select: [Tab] }>()

const TABS: Array<{ key: Tab; label: string; count: (s: PitikaSummary) => number }> = [
  { key: 'waiting', label: 'Waiting', count: (s) => s.waiting },
  { key: 'approved', label: 'Approved', count: (s) => s.approved_today },
  { key: 'rejected', label: 'Rejected', count: (s) => s.rejected_today },
]

const arcs = computed(() => (props.summary ? ringArcs(props.summary) : null))
const ringLabel = computed(() => {
  if (!arcs.value) return undefined
  const [decided, whole] = arcs.value.label.split('/')
  return `${decided} of ${whole} decided today`
})
// The ring: a circle of length 100 (pathLength), drawn in two arcs from the top.
const approvedDash = computed(() => `${(arcs.value?.approved ?? 0) * 100} 100`)
const rejectedDash = computed(() => `${(arcs.value?.rejected ?? 0) * 100} 100`)
const rejectedOffset = computed(() => -(arcs.value?.approved ?? 0) * 100)

// Arrow keys pick the next tab; the focus follows once the page shows it (roving tabindex).
const buttons = ref<HTMLButtonElement[]>([])
let moving = false
function move(from: number, step: number) {
  const next = TABS[(from + step + TABS.length) % TABS.length]!
  moving = true
  emit('select', next.key)
}
watch(
  () => props.tab,
  (tab) => {
    if (!moving) return
    moving = false
    buttons.value[TABS.findIndex((t) => t.key === tab)]?.focus()
  },
  { flush: 'post' },
)
</script>

<template>
  <div class="review-head">
    <div class="today-ring" :role="ringLabel ? 'img' : undefined" :aria-label="ringLabel">
      <svg viewBox="0 0 60 60" aria-hidden="true">
        <circle class="track" cx="30" cy="30" r="25" />
        <circle class="arc approved" cx="30" cy="30" r="25" pathLength="100" :stroke-dasharray="approvedDash" />
        <circle
          class="arc rejected"
          cx="30"
          cy="30"
          r="25"
          pathLength="100"
          :stroke-dasharray="rejectedDash"
          :stroke-dashoffset="rejectedOffset"
        />
      </svg>
      <span class="ring-text mono" aria-hidden="true">{{ arcs?.label ?? '' }}</span>
    </div>
    <div class="title">
      <h1>{{ title }}</h1>
      <p v-if="summary" class="sub">{{ summaryLine(summary) }}</p>
    </div>
    <div class="tab-switch" role="tablist" aria-label="Bookings to show">
      <button
        v-for="(t, k) in TABS"
        :key="t.key"
        ref="buttons"
        type="button"
        role="tab"
        :class="{ on: t.key === tab }"
        :aria-selected="t.key === tab ? 'true' : 'false'"
        :tabindex="t.key === tab ? 0 : -1"
        @click="emit('select', t.key)"
        @keydown.right.prevent="move(k, 1)"
        @keydown.left.prevent="move(k, -1)"
      >
        {{ t.label }}<em v-if="summary" class="mono">{{ t.count(summary) }}</em>
      </button>
    </div>
  </div>
</template>

<style scoped>
.review-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px 18px;
}
.today-ring {
  position: relative;
  flex: none;
  width: 60px;
  height: 60px;
}
.today-ring svg {
  width: 60px;
  height: 60px;
  transform: rotate(-90deg);
}
.today-ring circle {
  fill: none;
  stroke-width: 7;
}
.track {
  stroke: var(--color-rule);
}
.arc {
  stroke-linecap: butt;
  transition: stroke-dasharray 0.4s ease;
}
.approved {
  stroke: var(--color-ok);
}
.rejected {
  stroke: var(--color-crimson);
}
.ring-text {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--color-ink);
}
.title {
  flex: 1;
  min-width: 180px;
}
h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -0.01em;
}
.sub {
  margin: 3px 0 0;
  font-size: 13px;
  color: var(--color-intaglio);
}
.tab-switch {
  display: inline-flex;
  gap: 2px;
  padding: 3px;
  border-radius: 10px;
  background: var(--color-field-disabled);
}
.tab-switch button {
  padding: 6px 14px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  font: inherit;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-intaglio);
  white-space: nowrap;
  cursor: pointer;
}
.tab-switch button.on {
  background: var(--color-sheet);
  color: var(--color-ink);
  box-shadow: 0 1px 2px rgba(42, 28, 19, 0.08);
}
.tab-switch button:focus-visible {
  outline: 2px solid var(--color-thread);
  outline-offset: 1px;
}
.tab-switch em {
  margin-left: 6px;
  font-style: normal;
  font-size: 11px;
  color: var(--color-ink-off);
}
.tab-switch button.on em {
  color: var(--color-ink);
}
.mono {
  font-family: var(--font-mono);
}
@media (prefers-reduced-motion: reduce) {
  .arc {
    transition: none;
  }
}
</style>
