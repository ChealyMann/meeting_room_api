<script setup lang="ts">
// Says it in words when a page cannot reach the server (owner pick, option 2): a soft amber note
// above the list — what is shown is the last data that loaded, and "Try again". After "too many
// requests" it counts down instead, with Try again off until then. Nothing while all is well.
import { WifiOff } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import type { LiveRefresh } from '../../composables/useLiveRefresh'
import { updatedAgo } from './RefreshButton.vue'

const props = defineProps<{ live: LiveRefresh }>()
// The clock, for "loaded 2 min ago" and the "too many requests" count down.
const now = ref(Date.now())
let tick: ReturnType<typeof setInterval> | undefined
onMounted(() => (tick = setInterval(() => (now.value = Date.now()), 1_000)))
onBeforeUnmount(() => clearInterval(tick))

const ago = computed(() => updatedAgo(props.live.lastOk.value, now.value))
/** Seconds left after "too many requests"; 0 = none. */
const waitLeft = computed(() => Math.max(0, Math.ceil((props.live.waitUntil.value - now.value) / 1000)))
</script>

<template>
  <p v-if="live.failing.value" class="offline-note" role="status">
    <WifiOff aria-hidden="true" />
    <span v-if="waitLeft">Too many requests. Trying again in {{ waitLeft }} s.</span>
    <span v-else>Can't reach the server. Showing what was loaded {{ ago }}.</span>
    <button type="button" :disabled="live.refreshing.value || waitLeft > 0" @click="live.run()">Try again</button>
  </p>
</template>

<style scoped>
.offline-note {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 12px;
  padding: 9px 12px;
  border-radius: 10px;
  background: var(--color-saved-tint);
  color: var(--color-warn);
  font-size: 13px;
}
.offline-note svg {
  flex: none;
  width: 15px;
  height: 15px;
}
.offline-note span {
  flex: 1;
}
button {
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  font-weight: 600;
  text-decoration: underline;
  cursor: pointer;
}
button:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
