<script setup lang="ts">
// Step 3, Food & IT: two lists side by side. Food groups start with the one that suits the first
// session (no label says so). A note field shows under a list once something in it is picked.
import { computed } from 'vue'

import type { ServiceOut } from '../../../api/services'
import { foodGroupFirst } from '../rules'
import ServiceList from './ServiceList.vue'
import type { BookingDraft } from './useBookingDraft'

defineProps<{ foods: ServiceOut[]; its: ServiceOut[] }>()
const draft = defineModel<BookingDraft>('draft', { required: true })

const FOOD_LABELS = { BREAKFAST: 'Breakfast', MEALS: 'Meals', BREAKS: 'Breaks & drinks', OTHER: 'Other' }
const IT_LABELS = { SCREENS: 'Screens & video', SOUND: 'Sound & language', DEVICES: 'Devices & network', SUPPORT: 'Support', OTHER: 'Other' }
const IT_ORDER = ['SCREENS', 'SOUND', 'DEVICES', 'SUPPORT']

const firstStart = computed(() => {
  const sorted = [...draft.value.sessions].sort((x, y) => (x.date === y.date ? x.a - y.a : x.date < y.date ? -1 : 1))
  return sorted[0]?.a ?? 540
})
const foodOrder = computed(() => {
  const head = foodGroupFirst(firstStart.value)
  return [head, ...['BREAKFAST', 'MEALS', 'BREAKS'].filter((g) => g !== head)]
})

function toggle(list: 'foods' | 'its', id: number) {
  const now = draft.value[list]
  draft.value[list] = now.includes(id) ? now.filter((x) => x !== id) : [...now, id]
}
</script>

<template>
  <div class="ss">
    <ServiceList
      kind="food"
      title="Food & drinks"
      :items="foods"
      :group-order="foodOrder"
      :group-labels="FOOD_LABELS"
      :picked="draft.foods"
      search-label="food"
      @toggle="toggle('foods', $event)"
    >
      <textarea v-if="draft.foods.length" v-model="draft.foodNote" name="foodNote" class="note" rows="3" placeholder="Note for the kitchen" aria-label="Note for the kitchen" />
    </ServiceList>
    <ServiceList
      kind="it"
      title="IT help"
      :items="its"
      :group-order="IT_ORDER"
      :group-labels="IT_LABELS"
      :picked="draft.its"
      search-label="IT help"
      @toggle="toggle('its', $event)"
    >
      <textarea v-if="draft.its.length" v-model="draft.itNote" name="itNote" class="note" rows="3" placeholder="Note for IT" aria-label="Note for IT" />
    </ServiceList>
  </div>
</template>

<style scoped>
.ss {
  display: grid;
  flex: 1;
  grid-template-columns: 1fr 1fr;
  gap: 28px;
  min-height: 0;
}
/* The note: 3 lines from the start (owner, 16 Nov 2026: "bigger"), then it grows with the text (up to 7 lines). */
.note {
  flex: none;
  box-sizing: border-box;
  min-height: 80px;
  max-height: 160px;
  margin-top: 10px;
  padding: 10px 14px;
  field-sizing: content;
  line-height: 20px;
  border: 0;
  border-radius: 12px;
  outline: none;
  background: var(--color-field-disabled);
  color: var(--color-ink);
  font: inherit;
  font-size: 14px;
  resize: none;
  transition: background-color 160ms ease, box-shadow 160ms ease;
}
.note:focus {
  background: var(--color-sheet);
  box-shadow: 0 0 0 1.5px var(--color-ink);
}
@media (max-width: 1000px) {
  .ss {
    grid-template-columns: 1fr;
  }
}
</style>
