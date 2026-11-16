<script setup lang="ts">
// A room's cover photo, small and wide (the shape of a room photo), with a count badge when the
// room has more than one. No photo, or a file that does not load: a dashed box, never a broken image.
import { Image, ImageOff } from 'lucide-vue-next'
import { ref, watch } from 'vue'

import { apiBaseUrl } from '../../api'

const props = defineProps<{ path: string | null; count: number }>()

const failed = ref(false)
watch(
  () => props.path,
  () => (failed.value = false),
)
</script>

<template>
  <span v-if="path && !failed" class="room-thumb">
    <img :src="`${apiBaseUrl}${path}`" alt="" loading="lazy" @error="failed = true" />
    <span v-if="count > 1" class="photo-count" :aria-label="`${count} photos`">
      <Image aria-hidden="true" />{{ count }}
    </span>
  </span>
  <span v-else class="room-thumb none" title="No photo">
    <ImageOff aria-hidden="true" />
  </span>
</template>

<style scoped>
.room-thumb {
  position: relative;
  flex: none;
  display: grid;
  place-items: center;
  width: 64px;
  height: 44px;
  overflow: hidden;
  border-radius: 6px;
  background: var(--color-paper);
}
img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.photo-count {
  position: absolute;
  right: 3px;
  bottom: 3px;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 0 5px;
  border-radius: 4px;
  background: rgba(20, 12, 8, 0.62);
  color: #fff;
  font-family: var(--font-mono);
  font-size: 10px;
  line-height: 15px;
}
.photo-count :deep(svg.lucide) {
  width: 10px;
  height: 10px;
}
.room-thumb.none {
  border: 1px dashed var(--color-rule-strong);
  background: none;
  color: var(--color-off-ring);
}
.room-thumb.none :deep(svg.lucide) {
  width: 18px;
  height: 18px;
  stroke-width: 1.8;
}
</style>
