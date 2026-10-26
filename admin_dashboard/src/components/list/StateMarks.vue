<script setup lang="ts">
import { CalendarX, Lock } from 'lucide-vue-next'

// State by shape and word, never colour alone (DESIGN.md "State cell").
// A missing `bookable` means "no such mark" (places), not "not bookable": Vue would make it false.
withDefaults(defineProps<{ active: boolean; bookable?: boolean; private?: boolean }>(), { bookable: undefined })
</script>

<template>
  <div class="state-cell">
    <span class="state" :class="active ? 'active' : 'off'">{{ active ? 'Active' : 'Inactive' }}</span>
    <span v-if="active && bookable === false" class="mark unbookable">
      <CalendarX aria-hidden="true" />Not bookable
    </span>
    <span v-if="private" class="mark private"><Lock aria-hidden="true" />Private</span>
  </div>
</template>

<style scoped>
.state-cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.state {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  white-space: nowrap;
}
.state::before {
  content: '';
  flex: none;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.state.active::before {
  background: var(--color-ok);
}
.state.off {
  color: var(--color-ink-off);
}
.state.off::before {
  width: 7px;
  height: 7px;
  border: 1.5px solid var(--color-off-ring);
}
.mark {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  white-space: nowrap;
}
.mark svg.lucide {
  width: 13px;
  height: 13px;
}
.private {
  color: var(--color-warn);
}
.unbookable {
  color: var(--color-ink-off);
}
</style>
