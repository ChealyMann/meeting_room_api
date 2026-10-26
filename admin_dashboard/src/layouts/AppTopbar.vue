<script setup lang="ts">
import { ChevronRight, Clock, Menu, Moon, Sun } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { useUiStore } from '../stores/ui'
import { phnomPenhClock } from '../utils/time'

defineProps<{ menuOpen: boolean }>()
const emit = defineEmits<{ 'toggle-menu': [] }>()

const route = useRoute()
const ui = useUiStore()
const title = computed(() => route.meta.title ?? '')

const now = ref(phnomPenhClock(new Date()))
let timer: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  timer = setInterval(() => (now.value = phnomPenhClock(new Date())), 30_000)
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <header class="topbar">
    <button
      type="button"
      class="icon-btn menu"
      aria-label="Menu"
      :aria-expanded="menuOpen"
      @click="emit('toggle-menu')"
    >
      <Menu aria-hidden="true" />
    </button>
    <button
      type="button"
      class="icon-btn rail-toggle"
      :aria-label="ui.railCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
      :title="ui.railCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
      :aria-pressed="ui.railCollapsed"
      @click="ui.toggleRail()"
    >
      <!-- The same menu icon as the phone button; the label says what a click does. -->
      <Menu aria-hidden="true" />
    </button>
    <nav class="path" aria-label="Breadcrumb">
      <span>Meeting Rooms</span>
      <ChevronRight aria-hidden="true" />
      <b aria-current="page">{{ title }}</b>
    </nav>
    <div class="clock mono">
      <Clock aria-hidden="true" />
      <span>Phnom Penh {{ now }}</span>
    </div>
    <button
      type="button"
      class="icon-btn"
      :aria-label="ui.theme === 'dark' ? 'Switch to day mode' : 'Switch to night mode'"
      :title="ui.theme === 'dark' ? 'Day mode' : 'Night mode'"
      @click="ui.toggleTheme()"
    >
      <Sun v-if="ui.theme === 'dark'" aria-hidden="true" />
      <Moon v-else aria-hidden="true" />
    </button>
  </header>
</template>

<style scoped>
.topbar {
  display: flex;
  flex: none;
  align-items: center;
  gap: 16px;
  height: 56px;
  padding: 0 24px;
  border-bottom: 1px solid var(--color-rule);
  background: var(--color-paper);
}
.menu {
  display: none;
  margin-left: -6px;
}
.rail-toggle {
  margin-left: -8px;
}
.path {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  font-size: 13px;
  color: var(--color-intaglio);
}
.path span,
.path b {
  white-space: nowrap;
}
.path b {
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--color-ink);
  font-weight: 500;
}
.clock {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
  font-size: 12px;
  color: var(--color-intaglio);
  white-space: nowrap;
}
/* Tablets always show the folded rail, phones the drawer: no fold button there. */
@media (max-width: 1100px) {
  .rail-toggle {
    display: none;
  }
}
@media (max-width: 760px) {
  .topbar {
    gap: 8px;
    padding: 0 16px;
  }
  .menu {
    display: inline-grid;
  }
}
@media (max-width: 480px) {
  .path > span,
  .path > svg {
    display: none;
  }
}
</style>
