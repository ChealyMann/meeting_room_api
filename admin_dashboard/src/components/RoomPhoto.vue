<script setup lang="ts">
// A room's photo (a cover or its thumbnail, served by the API without a token), or a paper tile
// with a door when the room has none or the file does not load: never a broken image.
import { DoorOpen } from 'lucide-vue-next'
import { ref, watch } from 'vue'

import { apiBaseUrl } from '../api'

const props = defineProps<{ path: string | null; alt: string }>()

const failed = ref(false)
watch(
  () => props.path,
  () => (failed.value = false),
)
</script>

<template>
  <div class="room-photo" :class="{ none: !path || failed }">
    <img v-if="path && !failed" :src="`${apiBaseUrl}${path}`" :alt="alt" loading="lazy" @error="failed = true" />
    <DoorOpen v-else aria-hidden="true" />
  </div>
</template>

<style scoped>
.room-photo {
  display: grid;
  place-items: center;
  overflow: hidden;
  background: var(--color-paper);
  color: var(--color-off-ring);
}
.room-photo.none {
  border: 1px solid var(--color-rule);
}
img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.room-photo :deep(svg.lucide) {
  width: 28px;
  height: 28px;
  stroke-width: 1.5;
}
</style>
