<script setup lang="ts">
// The bookings list's filters (DSH-B01), kept in the address: search, status, province, room,
// and a day range (any session in it). Bookings have no Active filter.
import { X } from 'lucide-vue-next'
import { computed, onMounted, ref, watchEffect } from 'vue'

import { api } from '../../api'
import { listAllRooms, listProvinces } from '../../api/references'
import type { ProvinceRef, RoomListItem } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import DatePicker from '../../components/base/DatePicker.vue'
import ListSearch from '../../components/list/ListSearch.vue'
import SearchPicker, { type PickerItem } from '../../components/list/SearchPicker.vue'
import { useListQuery } from '../../composables/useListQuery'
import { STATUS_LABELS } from '../../utils/bookingLabels'
import { FILTER_WORDS } from '../../utils/pickerWords'
import { formatDay } from '../../utils/time'
import { BOOKING_FILTERS } from './bookingFilters'

/** Words for the active filters, for the "nothing matches" sentence. */
const props = withDefaults(defineProps<{ provinceFilter?: boolean }>(), { provinceFilter: true })
const emit = defineEmits<{ summary: [parts: string[]] }>()

const list = useListQuery(BOOKING_FILTERS, { activeFilter: false })
const f = computed(() => list.filters.value as Record<string, string | number | undefined>)
const text = (key: string) => (f.value[key] as string | undefined) ?? null
/** Any filter set: the bar then offers "Clear filters" at its end. */
const anyFilter = computed(() => Object.keys(list.filters.value).length > 0)

const provinces = ref<ProvinceRef[]>([])
const rooms = ref<RoomListItem[]>([])
onMounted(async () => {
  // A list that fails to load leaves its picker empty; the bookings still show.
  const [p, r] = await Promise.allSettled([listProvinces(api), listAllRooms(api)])
  if (p.status === 'fulfilled') provinces.value = p.value
  if (r.status === 'fulfilled') rooms.value = r.value
})

const statusItems: PickerItem[] = Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label }))
const provinceItems = computed<PickerItem[]>(() =>
  provinces.value.map((p) => ({ value: p.code, label: p.name_en, keywords: p.name_kh })),
)
const roomItems = computed<PickerItem[]>(() =>
  rooms.value.map((r) => ({ value: r.id, label: r.name_en, keywords: `${r.name_kh} ${r.location.name_en}` })),
)

const DAY = /^\d{4}-\d{2}-\d{2}$/
/** A day filter from the address, or null when it is missing or not a date. */
const dayOf = (key: 'from' | 'to') => (text(key) && DAY.test(text(key)!) ? text(key) : null)

watchEffect(() => {
  const day = (key: string) => (text(key) && DAY.test(text(key)!) ? formatDay(text(key)!) : text(key))
  const parts = [
    text('status') ? (STATUS_LABELS[text('status')!] ?? text('status')) : null,
    text('province') ? (provinces.value.find((p) => p.code === text('province'))?.name_en ?? text('province')) : null,
    f.value.room_id ? (rooms.value.find((r) => r.id === f.value.room_id)?.name_en ?? `room ${f.value.room_id}`) : null,
    text('from') ? `from ${day('from')}` : null,
    text('to') ? `to ${day('to')}` : null,
    text('q') ? `“${text('q')}”` : null,
  ]
  emit('summary', parts.filter((part): part is string => !!part))
})
</script>

<template>
  <div class="filters" role="search">
    <ListSearch
      :value="text('q') ?? ''"
      label="Search bookings"
      placeholder="Search title, reference or booker"
      @search="list.set({ q: $event })"
    />
    <SearchPicker
      id="filter-status"
      class="narrow"
      :items="statusItems"
      :words="FILTER_WORDS.bookingStatus"
      :model-value="text('status')"
      @update:model-value="list.set({ status: $event })"
    />
    <SearchPicker
      v-if="props.provinceFilter"
      id="filter-province"
      class="narrow"
      :items="provinceItems"
      :words="FILTER_WORDS.province"
      :model-value="text('province')"
      @update:model-value="list.set({ province: $event })"
    />
    <SearchPicker
      id="filter-room"
      class="narrow"
      :items="roomItems"
      :words="FILTER_WORDS.room"
      :model-value="(f.room_id as number | undefined) ?? null"
      @update:model-value="list.set({ room_id: $event })"
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
  </div>
</template>

<style scoped>
.filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin: 20px 0 16px;
}
.filters > .narrow {
  width: 160px;
}
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
</style>
