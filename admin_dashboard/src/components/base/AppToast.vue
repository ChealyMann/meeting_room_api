<script setup lang="ts">
import { CircleCheck } from 'lucide-vue-next'
import { computed } from 'vue'

import { useToast } from '../../composables/useToast'

const { toasts } = useToast()
const newest = computed(() => toasts.value[toasts.value.length - 1])
</script>

<template>
  <!-- The live region stays in the page so screen readers hear each new toast. -->
  <div role="status" class="fixed right-6 bottom-6 z-50 max-[760px]:right-4 max-[760px]:bottom-4">
    <Transition name="toast">
      <div v-if="newest" :key="newest.id" class="toast">
        <span class="toast-icon"><CircleCheck aria-hidden="true" /></span>
        <div>
          <b>{{ newest.title }}</b>
          <span v-if="newest.detail" class="mono">{{ newest.detail }}</span>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.toast-enter-active {
  transition:
    opacity 200ms ease,
    transform 260ms var(--ease-out-quint);
}
.toast-leave-active {
  transition: opacity 160ms ease;
}
.toast-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.toast-leave-to {
  opacity: 0;
}
</style>
