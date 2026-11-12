<script lang="ts">
/** "just now", "42 s ago", "3 min ago", "2 h ago". */
export function updatedAgo(lastOk: number, now: number): string {
  const s = Math.max(0, Math.round((now - lastOk) / 1000))
  if (s < 10) return 'just now'
  if (s < 60) return `${s} s ago`
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  return `${Math.floor(s / 3600)} h ago`
}
</script>

<script setup lang="ts">
// The refresh button (owner pick, 12 Nov 2026: option 2): a square icon button beside the page's
// main button. It refreshes now, turns while it works, and says on hover when the data last
// loaded. Amber when the server cannot be reached (OfflineNote says it in words).
import { RotateCw } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import type { LiveRefresh } from '../../composables/useLiveRefresh'

const props = defineProps<{ live: LiveRefresh }>()

// The hover text follows the clock; ten seconds is close enough.
const now = ref(Date.now())
let tick: ReturnType<typeof setInterval> | undefined
onMounted(() => (tick = setInterval(() => (now.value = Date.now()), 10_000)))
onBeforeUnmount(() => clearInterval(tick))

const title = computed(() =>
  props.live.failing.value ? "Can't reach the server · Try again" : `Updated ${updatedAgo(props.live.lastOk.value, now.value)} · Refresh`,
)
function refresh() {
  now.value = Date.now()
  void props.live.run()
}
</script>

<template>
  <button
    type="button"
    class="btn refresh"
    :class="{ turning: live.refreshing.value, off: live.failing.value }"
    aria-label="Refresh"
    :title="title"
    :aria-busy="live.refreshing.value || undefined"
    @click="refresh"
  >
    <RotateCw aria-hidden="true" />
  </button>
</template>

<style scoped>
.refresh {
  width: 36px;
  padding: 0;
  color: var(--color-intaglio);
}
.refresh svg {
  width: 16px;
  height: 16px;
}
/* One smooth turn per refresh; a slow one keeps turning until it is done. */
.refresh.turning svg {
  animation: turn 700ms var(--ease-out-quint) infinite;
}
.refresh.off {
  border-color: var(--color-warn);
  color: var(--color-warn);
}
@keyframes turn {
  to {
    transform: rotate(360deg);
  }
}
@media (hover: hover) and (pointer: fine) {
  .refresh:hover {
    color: var(--color-ink);
  }
}
@media (prefers-reduced-motion: reduce) {
  .refresh.turning svg {
    animation-duration: 1.6s;
    animation-timing-function: linear;
  }
}
</style>
