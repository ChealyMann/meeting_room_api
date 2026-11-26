<script setup lang="ts">
// A room's photos filling their box: they fade into each other (nothing slides), with dots,
// arrows on hover and the arrow keys. No photo: the door tile from RoomPhoto.
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { watch } from 'vue'

import { apiBaseUrl } from '../../api'
import type { PhotoOut } from '../../api/types'
import RoomPhoto from '../../components/RoomPhoto.vue'

// `dots: false` when the page shows its own small photos; `v-model:shown` shares the photo shown.
const props = withDefaults(defineProps<{ photos: PhotoOut[]; name: string; dots?: boolean }>(), { dots: true })
const shown = defineModel<number>('shown', { default: 0 })
watch(
  () => props.photos,
  () => (shown.value = 0),
)
const step = (n: number) => {
  const count = props.photos.length
  if (count) shown.value = (shown.value + n + count) % count
}
function key(e: KeyboardEvent) {
  if (e.key === 'ArrowLeft') step(-1)
  if (e.key === 'ArrowRight') step(1)
}
</script>

<template>
  <div class="gal" tabindex="0" :aria-label="`${name} photos, use the arrow keys`" @keydown="key">
    <template v-if="photos.length">
      <img
        v-for="(p, n) in photos"
        :key="p.id"
        :src="`${apiBaseUrl}${p.url}`"
        :alt="n === shown ? `${name}, photo ${n + 1}` : ''"
        :class="{ on: n === shown }"
      />
    </template>
    <RoomPhoto v-else class="none" :path="null" :alt="name" />
    <template v-if="photos.length > 1">
      <button type="button" class="gal-arrow prev" aria-label="Last photo" @click.stop="step(-1)"><ChevronLeft :size="18" /></button>
      <button type="button" class="gal-arrow next" aria-label="Next photo" @click.stop="step(1)"><ChevronRight :size="18" /></button>
      <div v-if="dots" class="gal-dots">
        <button
          v-for="(p, n) in photos"
          :key="p.id"
          type="button"
          :class="{ on: n === shown }"
          :aria-label="`Photo ${n + 1}`"
          :aria-current="n === shown || undefined"
          @click.stop="shown = n"
        />
      </div>
    </template>
  </div>
</template>

<style scoped>
.gal {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 220px;
  overflow: hidden;
  background: var(--color-field-disabled);
}
.gal:focus-visible {
  outline: 2px solid var(--color-crimson);
  outline-offset: 3px;
}
img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0;
  transition: opacity 280ms ease;
}
img.on {
  opacity: 1;
}
.none {
  position: absolute;
  inset: 0;
}
.gal-arrow {
  position: absolute;
  top: 50%;
  z-index: 2;
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  margin-top: -19px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.94);
  color: #2a1c13;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.18);
  opacity: 0;
  cursor: pointer;
  transition: opacity 160ms ease, transform 160ms var(--ease-out-quint);
}
.gal-arrow:active {
  transform: scale(0.93);
}
.prev {
  left: 16px;
}
.next {
  right: 16px;
}
.gal:hover .gal-arrow,
.gal:focus-within .gal-arrow {
  opacity: 1;
}
.gal-dots {
  position: absolute;
  top: 24px;
  left: 28px;
  z-index: 2;
  display: flex;
  gap: 6px;
  padding: 6px 9px;
  border-radius: 999px;
  background: rgba(20, 10, 8, 0.32);
  backdrop-filter: blur(8px);
}
.gal-dots button {
  width: 6px;
  height: 6px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: background-color 160ms ease, transform 160ms var(--ease-out-quint);
}
.gal-dots button.on {
  background: #fff;
  transform: scale(1.35);
}
@media (hover: none) {
  .gal-arrow {
    opacity: 1;
  }
}
@media (prefers-reduced-motion: reduce) {
  img,
  .gal-arrow,
  .gal-dots button {
    transition-duration: 1ms;
  }
}
</style>
