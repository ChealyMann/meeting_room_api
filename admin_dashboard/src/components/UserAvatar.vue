<script setup lang="ts">
// A user's round photo, or their initials when they have none (the photo needs the bearer
// token, so it loads as an object URL). Decorative: the name always stands beside it.
import { computed } from 'vue'

import { usePrivateImage } from '../composables/usePrivateImage'

const props = defineProps<{ path: string | null; name: string; version?: string }>()

const { imageUrl } = usePrivateImage(
  () => props.path,
  () => props.version,
)

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
  <span class="avatar" aria-hidden="true">
    <img v-if="imageUrl" :src="imageUrl" alt="" />
    <template v-else>{{ initials }}</template>
  </span>
</template>

<style scoped>
.avatar {
  flex: none;
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border: 1px solid var(--color-rule);
  border-radius: 50%;
  overflow: hidden;
  background: var(--color-paper);
  color: var(--color-crimson);
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
