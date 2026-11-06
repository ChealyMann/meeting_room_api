<script setup lang="ts">
// The head of every queue page (To review, IT setup): today's ring, the title, one calm line,
// and a tab switch with numbers. The page says what goes in; this draws it the same way.
import { computed, ref, watch } from 'vue'

export interface HeadRing {
  /** Parts of the whole, 0 to 1, drawn one after the other from the top. */
  parts: Array<{ value: number; tone: 'ok' | 'no' }>
  /** "6/9" */
  label: string
  /** What a screen reader hears, e.g. "6 of 9 decided today". */
  spoken: string
}
export interface HeadTab {
  key: string
  label: string
  /** null: not known yet (no number shown). */
  count: number | null
}

const props = defineProps<{ title: string; line: string | null; ring: HeadRing | null; tabs: HeadTab[]; tab: string }>()
const emit = defineEmits<{ select: [string] }>()

// The ring: a circle of length 100 (pathLength); each part starts where the one before ended.
const arcs = computed(() => {
  let start = 0
  return (props.ring?.parts ?? []).map((p) => {
    const arc = { tone: p.tone, dash: `${p.value * 100} 100`, offset: -start * 100 }
    start += p.value
    return arc
  })
})

// Arrow keys pick the next tab; the focus follows once the page shows it (roving tabindex).
const buttons = ref<HTMLButtonElement[]>([])
let moving = false
function move(from: number, step: number) {
  const next = props.tabs[(from + step + props.tabs.length) % props.tabs.length]!
  moving = true
  emit('select', next.key)
}
watch(
  () => props.tab,
  (tab) => {
    if (!moving) return
    moving = false
    buttons.value[props.tabs.findIndex((t) => t.key === tab)]?.focus()
  },
  { flush: 'post' },
)
</script>

<template>
  <div class="review-head">
    <div class="today-ring" :class="{ empty: ring?.label === '0/0' }" :role="ring ? 'img' : undefined" :aria-label="ring?.spoken">
      <svg viewBox="0 0 60 60" aria-hidden="true">
        <circle class="track" cx="30" cy="30" r="25" />
        <circle
          v-for="(a, k) in arcs"
          :key="k"
          class="arc"
          :class="a.tone === 'ok' ? 'approved' : 'rejected'"
          cx="30"
          cy="30"
          r="25"
          pathLength="100"
          :stroke-dasharray="a.dash"
          :stroke-dashoffset="a.offset"
        />
      </svg>
      <span class="ring-text mono" aria-hidden="true">{{ ring?.label ?? '' }}</span>
    </div>
    <div class="title">
      <h1>{{ title }}</h1>
      <p v-if="line" class="sub">{{ line }}</p>
    </div>
    <div class="tab-switch" role="tablist" aria-label="What to show">
      <button
        v-for="(t, k) in tabs"
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
        {{ t.label }}<em v-if="t.count !== null" class="mono">{{ t.count }}</em>
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
.today-ring.empty .ring-text {
  color: var(--color-ink-disabled);
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
