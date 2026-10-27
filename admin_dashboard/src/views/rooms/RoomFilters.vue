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
import StatusFilter from '../../components/list/StatusFilter.vue'
import { useListQuery } from '../../composables/useListQuery'
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

const toId = (event: Event) => {
  const value = (event.target as HTMLSelectElement).value
  return value ? Number(value) : null
}

// Choosing a parent clears its children: a floor from another office is never sent.
function chooseOffice(id: number | null) {
  list.set({ location_id: id, building_id: null, floor_id: null })
}
function chooseBuilding(event: Event) {
  list.set({ building_id: toId(event), floor_id: null })
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

const ownerValue = computed(() =>
  f.value.has_owner === false ? 'none' : num('owner_id') !== null ? String(num('owner_id')) : '',
)
function chooseOwner(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  list.set({
    owner_id: value && value !== 'none' ? Number(value) : null,
    has_owner: value === 'none' ? false : null,
  })
}

const triState = (key: string) => (f.value[key] === true ? 'yes' : f.value[key] === false ? 'no' : '')
function chooseTriState(key: string, event: Event) {
  const value = (event.target as HTMLSelectElement).value
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
    <label>
      <span class="sr-only">Building</span>
      <select
        id="filter-building"
        class="input"
        :value="num('building_id') ?? ''"
        :disabled="num('location_id') === null"
        @change="chooseBuilding"
      >
        <option value="">All buildings</option>
        <option v-for="b in buildingOptions" :key="b.value" :value="b.value">{{ b.label }}</option>
      </select>
    </label>
    <label>
      <span class="sr-only">Floor</span>
      <select
        id="filter-floor"
        class="input"
        :value="num('floor_id') ?? ''"
        :disabled="num('building_id') === null"
        @change="list.set({ floor_id: toId($event) })"
      >
        <option value="">All floors</option>
        <option v-for="fl in floorOptions" :key="fl.value" :value="fl.value">{{ fl.label }}</option>
      </select>
    </label>
    <label>
      <span class="sr-only">Room type</span>
      <select
        id="filter-type"
        class="input"
        :value="num('category_id') ?? ''"
        @change="list.set({ category_id: toId($event) })"
      >
        <option value="">All types</option>
        <option v-for="t in typeOptions" :key="t.value" :value="t.value">{{ t.label }}</option>
      </select>
    </label>
    <StatusFilter v-model="list.status.value" />
    <span class="spacer" />
    <BaseButton variant="quiet" :aria-expanded="moreOpen" aria-controls="more-filters" @click="moreOpen = !moreOpen">
      <SlidersHorizontal aria-hidden="true" />
      {{ moreOpen ? 'Fewer filters' : 'More filters' }}
    </BaseButton>
  </div>

  <div v-if="moreOpen" id="more-filters" class="filters more">
    <label>
      <span class="sr-only">Province</span>
      <select id="filter-province" class="input" :value="f.province ?? ''" @change="list.set({ province: ($event.target as HTMLSelectElement).value })">
        <option value="">All provinces</option>
        <option v-for="p in provinces" :key="p.code" :value="p.code">{{ p.name_en }}</option>
      </select>
    </label>
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
    <label>
      <span class="sr-only">Owner</span>
      <select id="filter-owner" class="input" :value="ownerValue" @change="chooseOwner">
        <option value="">Any owner</option>
        <option value="none">No owner</option>
        <option v-for="o in owners" :key="o.id" :value="String(o.id)">{{ o.name_en }}</option>
      </select>
    </label>
    <label>
      <span class="sr-only">Bookable</span>
      <select id="filter-bookable" class="input" :value="triState('is_bookable')" @change="chooseTriState('is_bookable', $event)">
        <option value="">Bookable or not</option>
        <option value="yes">Bookable</option>
        <option value="no">Not bookable</option>
      </select>
    </label>
    <label>
      <span class="sr-only">Private</span>
      <select id="filter-private" class="input" :value="triState('is_private')" @change="chooseTriState('is_private', $event)">
        <option value="">Private or public</option>
        <option value="yes">Private</option>
        <option value="no">Public</option>
      </select>
    </label>
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
