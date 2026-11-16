<script setup lang="ts">
// The "Approved by" list (owner, 16 Nov 2026), in the To review drawer and the booker's pop-up.
import { Check } from 'lucide-vue-next'
import { computed } from 'vue'

import type { BookingDetail } from '../api/types'
import { approvedBy, waitingFor } from '../utils/approvals'

const props = defineProps<{ booking: BookingDetail }>()
const approvals = computed(() => approvedBy(props.booking))
const waiting = computed(() => waitingFor(props.booking))
</script>

<template>
  <p v-if="!approvals.length" class="none">No one has approved yet.</p>
  <ul v-else class="approvals">
    <li v-for="(a, i) in approvals" :key="i">
      <span class="ap-mark" aria-hidden="true"><Check /></span>
      <span class="ap-text">
        <span class="ap-who">{{ a.who }}</span>
        <span class="ap-role">{{ a.role }}</span>
        <span v-if="a.note" class="ap-note">“{{ a.note }}”</span>
      </span>
      <span class="ap-when mono">{{ a.when }}</span>
    </li>
    <li v-if="waiting" class="ap-wait">
      <span class="ap-mark" aria-hidden="true"><span class="ap-dot" /></span>
      <span class="ap-text"><span class="ap-who">{{ waiting }}</span></span>
    </li>
  </ul>
</template>

<style scoped>
.none {
  margin: 0;
  color: var(--color-ink-off);
  font-size: 13px;
}
/* A green tick, the name over the role (and the note), the time on the right. */
.approvals {
  display: grid;
  margin: 0;
  padding: 0;
  list-style: none;
}
.approvals li {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) auto;
  align-items: start;
  gap: 10px;
  padding: 9px 0;
}
.approvals li + li {
  border-top: 1px solid var(--color-rule);
}
.ap-mark {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--color-ok) 14%, transparent);
  color: var(--color-ok);
}
.ap-mark svg {
  width: 13px;
  height: 13px;
}
.ap-wait .ap-mark {
  background: var(--color-field-disabled);
}
.ap-dot {
  width: 5px;
  height: 5px;
  border-radius: 999px;
  background: var(--color-ink-off);
}
.ap-text {
  display: grid;
  min-width: 0;
}
.ap-who {
  font-size: 13.5px;
  font-weight: 500;
}
.ap-wait .ap-who {
  color: var(--color-ink-off);
  font-weight: 400;
}
.ap-role {
  font-size: 12px;
  color: var(--color-ink-off);
}
.ap-note {
  margin-top: 4px;
  font-size: 12.5px;
  color: var(--color-intaglio);
  overflow-wrap: anywhere;
}
.ap-when {
  padding-top: 2px;
  font-size: 12px;
  color: var(--color-ink-off);
  white-space: nowrap;
}
@media (max-width: 420px) {
  .approvals li {
    grid-template-columns: 22px minmax(0, 1fr);
  }
  .ap-when {
    grid-column: 2;
    padding-top: 0;
  }
}
</style>
