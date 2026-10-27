<script setup lang="ts">
// The room list's filter row (DSH-R01, G02). Every value lives in the page address.
import { Search, SlidersHorizontal } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref, watch, watchEffect } from 'vue'

import { api } from '../../api'
import {
  listBuildings,
  listEquipment,
  listFloors,
  listOffices,
  listProvinces,
  listRoomOwners,
  listRoomTypes,
} from '../../api/references'
import type {
  BuildingOut,
  CategoryOut,
  EquipmentOut,
  FloorOut,
  LocationOut,
  ProvinceRef,
  UserListItem,
} from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import OfficePicker from '../../components/list/OfficePicker.vue'
import SearchPicker, { type PickerItem } from '../../components/list/SearchPicker.vue'
import StatusFilter from '../../components/list/StatusFilter.vue'
import { useListQuery } from '../../composables/useListQuery'
import { FILTER_WORDS } from '../../utils/pickerWords'
import { selectOptions } from '../../utils/selectOptions'
import { MORE_FILTERS, ROOM_FILTERS } from './roomFilters'

/** Words for the active filters, for the "nothing matches" sentence. */
const emit = defineEmits<{ summary: [parts: string[]] }>()

const list = useListQuery(ROOM_FILTERS)
const f = computed(() => list.filters.value as Record<string, never>)
const num = (key: string) => (f.value[key] as number | undefined) ?? null

const offices = ref<LocationOut[]>([])
const buildings = ref<BuildingOut[]>([])
const floors = ref<FloorOut[]>([])
const roomTypes = ref<CategoryOut[]>([])
const provinces = ref<ProvinceRef[]>([])
const equipment = ref<EquipmentOut[]>([])
const owners = ref<UserListItem[]>([])

const moreOpen = ref(MORE_FILTERS.some((key) => key in list.filters.value))

onMounted(async () => {
  const [o, t] = await Promise.all([listOffices(api), listRoomTypes(api)])
  offices.value = o
  roomTypes.value = t
})

// Only the answer for the parent chosen last counts: answers can come back out of order.
watch(
  () => num('location_id'),
  async (id) => {
    const items = id ? await listBuildings(api, id) : []
    if (num('location_id') === id) buildings.value = items
  },
  { immediate: true },
)
watch(
  () => num('building_id'),
  async (id) => {
    const items = id ? await listFloors(api, id) : []
    if (num('building_id') === id) floors.value = items
  },
  { immediate: true },
)
watch(
  moreOpen,
  async (open) => {
    if (!open || provinces.value.length) return
    const [p, e, o] = await Promise.all([listProvinces(api), listEquipment(api), listRoomOwners(api)])
    provinces.value = p
    equipment.value = e
    owners.value = o
  },
  { immediate: true },
)

const buildingOptions = computed(() =>
  selectOptions(buildings.value, num('building_id'), (b) => b.name_en, 'Unknown building'),
)
const floorOptions = computed(() =>
  selectOptions(floors.value, num('floor_id'), (fl) => fl.floor_label, 'Unknown floor'),
)
const typeOptions = computed(() =>
  selectOptions(roomTypes.value, num('category_id'), (t) => t.name_en, 'Unknown room type'),
)


// Choosing a parent clears its children: a floor from another office is never sent.
function chooseOffice(id: number | null) {
  list.set({ location_id: id, building_id: null, floor_id: null })
}
function chooseBuilding(id: number | null) {
  list.set({ building_id: id, floor_id: null })
}

// Search waits until typing stops (300ms), so the list is not reloaded per key.
const searchText = ref((f.value.search as string | undefined) ?? '')
let searchTimer: ReturnType<typeof setTimeout> | undefined
watch(searchText, (text) => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    if (text.trim() !== ((f.value.search as string | undefined) ?? '')) list.set({ search: text.trim() })
  }, 300)
})
watch(
  () => f.value.search as string | undefined,
  (search) => {
    if ((search ?? '') !== searchText.value.trim()) searchText.value = search ?? ''
  },
)
onBeforeUnmount(() => clearTimeout(searchTimer))

const minSeats = ref(String(num('min_capacity') ?? ''))
watch(
  () => num('min_capacity'),
  (value) => (minSeats.value = value === null ? '' : String(value)),
)
function chooseMinSeats() {
  const value = Number(minSeats.value)
  list.set({ min_capacity: Number.isInteger(value) && value >= 1 ? value : null })
}

const chosenEquipment = computed(() => (f.value.equipment_ids as number[] | undefined) ?? [])
function toggleEquipment(id: number, on: boolean) {
  const ids = new Set(chosenEquipment.value)
  if (on) ids.add(id)
  else ids.delete(id)
  list.set({ equipment_ids: [...ids].sort((a, b) => a - b) })
}

// "No owner" is its own choice ('none' → has_owner=false); a person is their id.
const ownerItems = computed<PickerItem[]>(() => [
  { value: 'none', label: 'No owner' },
  ...owners.value.map((o) => ({ value: o.id, label: o.name_en, keywords: o.name_kh })),
])
const ownerValue = computed(() => (f.value.has_owner === false ? 'none' : num('owner_id')))
function chooseOwner(value: number | string | null) {
  list.set({
    owner_id: typeof value === 'number' ? value : null,
    has_owner: value === 'none' ? false : null,
  })
}
const provinceItems = computed<PickerItem[]>(() =>
  provinces.value.map((p) => ({ value: p.code, label: p.name_en, keywords: p.name_kh })),
)

const triState = (key: string) => (f.value[key] === true ? 'yes' : f.value[key] === false ? 'no' : null)
function chooseTriState(key: string, value: number | string | null) {
  list.set({ [key]: value === 'yes' ? true : value === 'no' ? false : null })
}

watchEffect(() => {
  const nameOf = <T extends { id: number }>(items: T[], id: number | null, label: (i: T) => string) =>
    id === null ? null : (items.find((i) => i.id === id) ? label(items.find((i) => i.id === id)!) : `#${id}`)
  const parts = [
    nameOf(offices.value, num('location_id'), (o) => o.name_en),
    nameOf(buildings.value, num('building_id'), (b) => b.name_en),
    nameOf(floors.value, num('floor_id'), (fl) => fl.floor_label),
    nameOf(roomTypes.value, num('category_id'), (t) => t.name_en),
    f.value.province ? (provinces.value.find((p) => p.code === f.value.province)?.name_en ?? f.value.province) : null,
    num('min_capacity') ? `${num('min_capacity')}+ seats` : null,
    chosenEquipment.value.length ? 'with the chosen equipment' : null,
    f.value.has_owner === false ? 'no owner' : nameOf(owners.value, num('owner_id'), (o) => o.name_en),
    f.value.is_bookable === true ? 'bookable' : f.value.is_bookable === false ? 'not bookable' : null,
    f.value.is_private === true ? 'private' : f.value.is_private === false ? 'public' : null,
    f.value.search ? `“${f.value.search}”` : null,
    list.status.value === 'active' ? 'active only' : list.status.value === 'inactive' ? 'inactive only' : null,
  ]
  emit('summary', parts.filter((part): part is string => !!part))
})
</script>

<template>
  <div class="filters" role="search">
    <label class="search">
      <span class="sr-only">Search rooms</span>
      <Search aria-hidden="true" />
      <input v-model="searchText" class="input" type="search" placeholder="Search name or description" />
    </label>
    <OfficePicker id="filter-office" :offices="offices" :model-value="num('location_id')" @update:model-value="chooseOffice" />
    <SearchPicker
      id="filter-building"
      class="narrow"
      :items="buildingOptions"
      :words="FILTER_WORDS.building"
      :model-value="num('building_id')"
      :disabled="num('location_id') === null"
      @update:model-value="chooseBuilding($event as number | null)"
    />
    <SearchPicker
      id="filter-floor"
      class="narrow"
      :items="floorOptions"
      :words="FILTER_WORDS.floor"
      :model-value="num('floor_id')"
      :disabled="num('building_id') === null"
      @update:model-value="list.set({ floor_id: $event })"
    />
    <SearchPicker
      id="filter-type"
      class="narrow"
      :items="typeOptions"
      :words="FILTER_WORDS.roomType"
      :model-value="num('category_id')"
      @update:model-value="list.set({ category_id: $event })"
    />
    <StatusFilter v-model="list.status.value" />
    <span class="spacer" />
    <BaseButton variant="quiet" :aria-expanded="moreOpen" aria-controls="more-filters" @click="moreOpen = !moreOpen">
      <SlidersHorizontal aria-hidden="true" />
      {{ moreOpen ? 'Fewer filters' : 'More filters' }}
    </BaseButton>
  </div>

  <div v-if="moreOpen" id="more-filters" class="filters more">
    <SearchPicker
      id="filter-province"
      :items="provinceItems"
      :words="FILTER_WORDS.province"
      :model-value="(f.province as string | undefined) ?? null"
      @update:model-value="list.set({ province: $event })"
    />
    <label class="seats">
      <span class="sr-only">Minimum seats</span>
      <input
        v-model="minSeats"
        class="input mono"
        type="number"
        min="1"
        max="10000"
        placeholder="Min. seats"
        @change="chooseMinSeats"
      />
    </label>
    <details class="multi">
      <summary class="input">
        Equipment<span v-if="chosenEquipment.length" class="mono"> · {{ chosenEquipment.length }}</span>
      </summary>
      <div class="menu">
        <p class="hint">Rooms that have all of:</p>
        <label v-for="e in equipment.filter((x) => x.is_active || chosenEquipment.includes(x.id))" :key="e.id" class="check">
          <input
            type="checkbox"
            :checked="chosenEquipment.includes(e.id)"
            @change="toggleEquipment(e.id, ($event.target as HTMLInputElement).checked)"
          />
          {{ e.name }}
        </label>
        <p v-if="!equipment.length" class="hint">No equipment yet.</p>
      </div>
    </details>
    <SearchPicker
      id="filter-owner"
      :items="ownerItems"
      :words="FILTER_WORDS.owner"
      :model-value="ownerValue"
      @update:model-value="chooseOwner"
    />
    <SearchPicker
      id="filter-bookable"
      :items="[{ value: 'yes', label: 'Bookable' }, { value: 'no', label: 'Not bookable' }]"
      :words="FILTER_WORDS.bookable"
      :model-value="triState('is_bookable')"
      @update:model-value="chooseTriState('is_bookable', $event)"
    />
    <SearchPicker
      id="filter-private"
      :items="[{ value: 'yes', label: 'Private' }, { value: 'no', label: 'Public' }]"
      :words="FILTER_WORDS.private"
      :model-value="triState('is_private')"
      @update:model-value="chooseTriState('is_private', $event)"
    />
  </div>
</template>

<style scoped>
/* Building, floor and type stay as narrow as the old lists, so the first row fits at 1366px. */
.filters > .narrow {
  width: 136px;
}
.filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin: 20px 0 16px;
}
.filters.more {
  margin-top: -8px;
}
.search {
  position: relative;
  flex: 1 1 240px;
  max-width: 320px;
}
.search svg.lucide {
  position: absolute;
  top: 50%;
  left: 10px;
  transform: translateY(-50%);
  color: var(--color-intaglio);
  pointer-events: none;
}
.search .input {
  padding-left: 34px;
}
.filters select.input {
  width: auto;
  min-width: 136px;
}
.seats .input {
  width: 120px;
}
.spacer {
  flex: 1;
}
.multi {
  position: relative;
}
.multi summary {
  display: flex;
  align-items: center;
  min-width: 136px;
  list-style: none;
  cursor: pointer;
}
.multi summary::-webkit-details-marker {
  display: none;
}
.menu {
  position: absolute;
  z-index: 5;
  top: calc(100% + 4px);
  left: 0;
  display: grid;
  gap: 6px;
  min-width: 220px;
  max-height: 280px;
  overflow-y: auto;
  padding: 10px 12px;
  border: 1px solid var(--color-rule-strong);
  border-radius: 8px;
  background: var(--color-sheet);
  box-shadow: var(--shadow-toast);
}
.hint {
  margin: 0;
  font-size: 12px;
  color: var(--color-intaglio);
}
.check {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13.5px;
}
.check input {
  accent-color: var(--color-crimson-fill);
}
</style>
