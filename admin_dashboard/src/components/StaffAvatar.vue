<script setup lang="ts">
// A person's round photo (it needs the token, so it is loaded as a blob), or their initials on
// crimson wash while it loads or when they have none. The name is said by the text beside it.
import { computed } from 'vue'

import { usePrivateImage } from '../composables/usePrivateImage'

const props = withDefaults(defineProps<{ name: string; photo: string | null; size?: number }>(), { size: 32 })

const { imageUrl } = usePrivateImage(() => props.photo)
const initials = computed(() =>
  props.name
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word.charAt(0).toUpperCase())
    .join(''),
)
</script>

<template>
  <span class="staff-avatar" :style="{ width: `${size}px`, height: `${size}px`, fontSize: `${Math.round(size * 0.34)}px` }" aria-hidden="true">
    <img v-if="imageUrl" :src="imageUrl" alt="" />
    <template v-else>{{ initials }}</template>
  </span>
</template>

<style scoped>
.staff-avatar {
  display: inline-grid;
  flex: none;
  place-items: center;
  overflow: hidden;
  border-radius: 50%;
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
  font-weight: 600;
  line-height: 1;
}
img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
