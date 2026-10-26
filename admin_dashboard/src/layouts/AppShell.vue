<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import AppToast from '../components/base/AppToast.vue'
import AppRail from './AppRail.vue'
import AppTopbar from './AppTopbar.vue'

// Below 760px the rail is a drawer opened from the top bar.
const railOpen = ref(false)
const route = useRoute()
watch(
  () => route.fullPath,
  () => (railOpen.value = false),
)
</script>

<template>
  <div class="shell">
    <a href="#main" class="skip">Skip to content</a>
    <AppRail :open="railOpen" @close="railOpen = false" />
    <div v-if="railOpen" class="drawer-scrim" aria-hidden="true" @click="railOpen = false" />
    <div class="work">
      <AppTopbar :menu-open="railOpen" @toggle-menu="railOpen = !railOpen" />
      <main id="main" tabindex="-1" class="page">
        <RouterView />
      </main>
    </div>
    <AppToast />
  </div>
</template>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: 248px minmax(0, 1fr);
  height: 100vh;
  height: 100dvh;
  min-height: 640px;
}
.work {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}
.page {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: 24px;
}
.page:focus {
  outline: none;
}
.skip {
  position: fixed;
  left: 12px;
  top: 12px;
  z-index: 60;
  padding: 8px 12px;
  border-radius: 8px;
  background: var(--color-sheet);
  color: var(--color-ink);
  box-shadow: var(--shadow-toast);
  transform: translateY(-200%);
}
.skip:focus {
  transform: none;
}
.drawer-scrim {
  display: none;
}
@media (max-width: 1100px) {
  .shell {
    grid-template-columns: 64px minmax(0, 1fr);
  }
}
@media (max-width: 760px) {
  .shell {
    grid-template-columns: minmax(0, 1fr);
    min-height: 0;
  }
  .page {
    padding: 20px 16px;
  }
  .drawer-scrim {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 30;
    background: rgba(38, 7, 7, 0.32);
  }
}
</style>
