<script setup lang="ts">
import { CalendarX, CircleCheck, CircleDashed, EyeOff } from 'lucide-vue-next'

// State by shape and word, never colour alone (DESIGN.md "State cell").
// A missing `bookable` means "no such mark" (places), not "not bookable": Vue would make it false.
withDefaults(defineProps<{ active: boolean; bookable?: boolean; private?: boolean }>(), { bookable: undefined })
</script>

<template>
  <div class="state-cell">
    <span class="state" :class="active ? 'active' : 'off'">
      <CircleCheck v-if="active" aria-hidden="true" />
      <CircleDashed v-else aria-hidden="true" />
      {{ active ? 'Active' : 'Inactive' }}
    </span>
    <span v-if="active && bookable === false" class="mark unbookable">
      <CalendarX aria-hidden="true" />Not bookable
    </span>
    <span v-if="private" class="mark private"><EyeOff aria-hidden="true" />Private</span>
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
/* A circle check for Active, a dashed circle for Inactive (owner decision, 27 Oct 2026: no dot). */
.state svg.lucide {
  flex: none;
  width: 16px;
  height: 16px;
}
.state.active svg {
  color: var(--color-ok);
}
.state.off {
  color: var(--color-ink-off);
}
.state.off svg {
  color: var(--color-off-ring);
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
