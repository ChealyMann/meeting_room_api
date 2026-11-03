<script setup lang="ts">
// An empty list: what is missing, what to do, and a seal with the page's own menu icon
// (DESIGN.md "Empty State", owner decision 30 Oct 2026; replaces the rosette watermark).
// When filters hide every record the seal shows a search icon instead, so the two cases
// never look the same.
import { Inbox, SearchX } from 'lucide-vue-next'
import { computed, inject } from 'vue'
import { routeLocationKey } from 'vue-router'

import { navIcon } from '../../layouts/nav'

const props = withDefaults(defineProps<{ title: string; text: string; filtered?: boolean }>(), {
  filtered: false,
})

// Injected with a default, so the component also works outside a router (tests, previews).
const route = inject(routeLocationKey, null)
const icon = computed(() => (props.filtered ? SearchX : (navIcon(route?.name) ?? Inbox)))
</script>

<template>
  <div class="empty">
    <div class="seal" aria-hidden="true">
      <span><component :is="icon" class="icon" /></span>
    </div>
    <h2>{{ title }}</h2>
    <p>{{ text }}</p>
    <div class="actions"><slot /></div>
  </div>
</template>

<style scoped>
.empty {
  display: grid;
  justify-items: center;
  padding: 40px 16px 36px;
  border-bottom: 1px solid var(--color-rule);
  text-align: center;
}
/* A dashed ring around a crimson-wash disc, as on the Confirm Dialog. */
.seal {
  display: grid;
  place-items: center;
  width: 72px;
  height: 72px;
  margin-bottom: 14px;
  border: 1.5px dashed var(--color-off-ring);
  border-radius: 50%;
}
.seal span {
  display: grid;
  place-items: center;
  width: 54px;
  height: 54px;
  border-radius: 50%;
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
}
.icon {
  width: 24px;
  height: 24px;
  stroke-width: 1.75;
}
h2 {
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 600;
}
p {
  max-width: 40ch;
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--color-intaglio);
}
.actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}
</style>
