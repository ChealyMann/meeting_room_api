<script setup lang="ts">
// Says it in words when a page cannot reach the server (owner pick, option 2): a soft amber note
// above the list — what is shown is the last data that loaded, and "Try again". Nothing otherwise.
import { WifiOff } from 'lucide-vue-next'
import { computed } from 'vue'

import type { LiveRefresh } from '../../composables/useLiveRefresh'
import { updatedAgo } from './RefreshButton.vue'

const props = defineProps<{ live: LiveRefresh }>()
// Read when the note shows or changes; the next refresh (15 s) re-renders it anyway.
const ago = computed(() => updatedAgo(props.live.lastOk.value, props.live.failing.value ? Date.now() : props.live.lastOk.value))
</script>

<template>
  <p v-if="live.failing.value" class="offline-note" role="status">
    <WifiOff aria-hidden="true" />
    <span>Can't reach the server. Showing what was loaded {{ ago }}.</span>
    <button type="button" :disabled="live.refreshing.value" @click="live.run()">Try again</button>
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
