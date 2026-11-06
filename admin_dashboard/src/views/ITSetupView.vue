<script setup lang="ts">
// The IT Lead's IT setup (spec 2026-11-05-owner-and-it-pages-design, Part B): today's ring and
// line, the tabs To assign · In progress · Ready (missed setups show on Ready), and the filters
// (search, setup day range) kept in the address and shared by the tabs.
import { X } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '../api'
import { getItSummary } from '../api/it'
import { listAllRooms } from '../api/references'
import type { ITSummary, RoomListItem } from '../api/types'
import BaseButton from '../components/base/BaseButton.vue'
import DatePicker from '../components/base/DatePicker.vue'
import ListSearch from '../components/list/ListSearch.vue'
import QueueHead, { type HeadTab } from '../components/QueueHead.vue'
import { useListQuery } from '../composables/useListQuery'
import { usePhnomPenhToday } from '../composables/usePhnomPenhToday'
import { reportWaiting } from '../composables/useWaitingCounts'
import { itRing, itSummaryLine, itTabFrom, type ItTab } from '../utils/itQueue'
import ITQueue from './it/ITQueue.vue'
import ViewSwitch from './it/ViewSwitch.vue'

// The filter bar only: each tab's list (ITQueue) reads the same address keys.
const list = useListQuery({ from: 'string', to: 'string', q: 'string' }, { activeFilter: false })
const f = computed(() => list.filters.value as Record<string, string | undefined>)
const anyFilter = computed(() => Object.keys(list.filters.value).length > 0)
const DAY = /^\d{4}-\d{2}-\d{2}$/
const dayOf = (key: 'from' | 'to') => {
  const value = f.value[key]
  return typeof value === 'string' && DAY.test(value) ? value : null
}

const summary = ref<ITSummary | null>(null)
async function loadSummary() {
  try {
    summary.value = await getItSummary(api)
    reportWaiting('it-setup', summary.value.to_assign) // the menu agrees
  } catch {
    // no ring and no numbers: the lists still work
  }
}
const today = usePhnomPenhToday()
onMounted(loadSummary)
watch(today, loadSummary)

// Rooms, loaded once: where each room is (office · building · floor) and its photo.
const rooms = ref<RoomListItem[]>([])
onMounted(async () => {
  try {
    rooms.value = await listAllRooms(api)
  } catch {
    // rows show no place line and the plain tile
  }
})

const route = useRoute()
const router = useRouter()
const tab = computed<ItTab>(() => itTabFrom(route.query.tab))
const tabs = computed<HeadTab[]>(() => {
  const s = summary.value
  return [
    { key: 'to_assign', label: 'To assign', count: s ? s.to_assign : null },
    { key: 'in_progress', label: 'In progress', count: s ? s.in_progress : null },
    { key: 'ready', label: 'Ready', count: s ? s.ready_today : null },
  ]
})
/** Another tab: the filters stay; the page and the open setup do not. */
function selectTab(next: string) {
  const query = { ...route.query }
  for (const key of ['tab', 'page', 'id']) delete query[key]
  if (next !== 'to_assign') query.tab = next
  void router.replace({ query })
}
</script>

<template>
  <div class="places-page it-setup">
    <QueueHead
      title="IT setup"
      :line="summary ? itSummaryLine(summary) : null"
      :ring="summary ? itRing(summary) : null"
      :tabs="tabs"
      :tab="tab"
      @select="selectTab"
    />

    <div class="filters" role="search">
      <ListSearch
        :value="f.q ?? ''"
        label="Search setups"
        placeholder="Search title or reference"
        @search="list.set({ q: $event })"
      />
      <div class="day">
        <span class="label" aria-hidden="true">From</span>
        <DatePicker
          id="filter-from"
          label="From"
          placeholder="Any day"
          clearable
          :max="dayOf('to')"
          :model-value="dayOf('from')"
          @update:model-value="list.set({ from: $event })"
        />
      </div>
      <div class="day">
        <span class="label" aria-hidden="true">To</span>
        <DatePicker
          id="filter-to"
          label="To"
          placeholder="Any day"
          clearable
          :min="dayOf('from')"
          :model-value="dayOf('to')"
          @update:model-value="list.set({ to: $event })"
        />
      </div>
      <BaseButton v-if="anyFilter" variant="quiet" class="clear-filters" @click="list.reset()">
        <X aria-hidden="true" />
        Clear filters
      </BaseButton>
      <ViewSwitch class="view-end" />
    </div>

    <ITQueue :key="tab" :tab="tab" :rooms="rooms" :actions="true" @changed="loadSummary" />
  </div>
</template>

<style scoped src="./listPage.css"></style>

<style scoped>
.day {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  color: var(--color-ink-off);
}
.day .date-picker {
  width: 164px;
}
.clear-filters {
  color: var(--color-crimson);
}
.view-end {
  margin-left: auto;
}
</style>
