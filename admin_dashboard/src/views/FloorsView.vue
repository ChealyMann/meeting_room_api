<script setup lang="ts">
// Floors (DSH-P04, P05): a filtered, paged list. The open floor lives in the address
// (?id=7, ?id=new), so a reload keeps the panel open.
import { CircleAlert, Ellipsis, Plus } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'

import { api } from '../api'
import { ApiError } from '../api/errors'
import { getFloor, listFloorPage, type FloorFilters } from '../api/places'
import { listBuildings, listOffices } from '../api/references'
import type { BuildingOut, FloorDetail, FloorOut, LocationOut } from '../api/types'
import BaseButton from '../components/base/BaseButton.vue'
import SidePanel from '../components/base/SidePanel.vue'
import EmptyState from '../components/list/EmptyState.vue'
import ListSearch from '../components/list/ListSearch.vue'
import PagingFoot from '../components/list/PagingFoot.vue'
import StateMarks from '../components/list/StateMarks.vue'
import StatusFilter from '../components/list/StatusFilter.vue'
import TableSkeleton from '../components/list/TableSkeleton.vue'
import { usePanelParam } from '../composables/usePanelParam'
import { useResourceList } from '../composables/useResourceList'
import { selectOptions } from '../utils/selectOptions'
import { serial } from '../utils/serial'
import FloorFormPanel from './places/FloorFormPanel.vue'

const { list, result, loading, error, filtered, savedId, load, refresh } = useResourceList<FloorOut>(
  { location_id: 'int', building_id: 'int', search: 'string' },
  (params) => listFloorPage(api, params as FloorFilters),
)
const panel = usePanelParam()

const officeId = computed(() => (list.filters.value.location_id as number | undefined) ?? null)
const buildingId = computed(() => (list.filters.value.building_id as number | undefined) ?? null)
const search = computed(() => (list.filters.value.search as string | undefined) ?? '')

// The list only has the building id; building and office names come from the full lists.
const offices = ref<LocationOut[]>([])
const allBuildings = ref<BuildingOut[]>([])
onMounted(async () => {
  const [o, b] = await Promise.all([listOffices(api), listBuildings(api)])
  offices.value = o
  allBuildings.value = b
})
const buildingOf = (id: number) => allBuildings.value.find((b) => b.id === id)
const officeName = (id: number) => offices.value.find((o) => o.id === id)?.name_en ?? `#${id}`
const buildingName = (id: number) => buildingOf(id)?.name_en ?? `#${id}`

// The Building filter lists the chosen office's buildings. Only the answer for the office
// chosen last counts: answers can come back out of order.
const officeBuildings = ref<BuildingOut[]>([])
watch(
  officeId,
  async (id) => {
    const items = id ? await listBuildings(api, id) : []
    if (officeId.value === id) officeBuildings.value = items
  },
  { immediate: true },
)

const officeOptions = computed(() =>
  selectOptions(offices.value, officeId.value, (o) => o.name_en, 'Unknown office'),
)
const buildingOptions = computed(() =>
  selectOptions(officeBuildings.value, buildingId.value, (b) => b.name_en, 'Unknown building'),
)
const idOf = (event: Event) => {
  const value = (event.target as HTMLSelectElement).value
  return value ? Number(value) : null
}
// Choosing an office clears the building: a building from another office is never sent.
function chooseOffice(event: Event) {
  list.set({ location_id: idOf(event), building_id: null })
}

const total = computed(() => result.value?.total ?? 0)
const count = computed(() => `${String(total.value).padStart(3, '0')} ${total.value === 1 ? 'floor' : 'floors'}`)
const words = computed(() =>
  [
    officeId.value !== null ? officeName(officeId.value) : null,
    buildingId.value !== null ? buildingName(buildingId.value) : null,
    search.value ? `“${search.value}”` : null,
    list.status.value === 'active' ? 'active only' : list.status.value === 'inactive' ? 'inactive only' : null,
  ].filter((part): part is string => !!part),
)

// The edit form needs the floor; load it here so a reload on ?id=7 works too.
// Only the answer for the floor in the address counts; a failure is shown with "Try again".
const editFloor = ref<FloorDetail | null>(null)
const editError = ref('')
let editRequest = 0
async function loadEdit() {
  const request = ++editRequest
  editFloor.value = null
  editError.value = ''
  const id = panel.id.value
  if (id === null) return
  try {
    const floor = await getFloor(api, id)
    if (request === editRequest) editFloor.value = floor
  } catch (err) {
    if (request === editRequest) editError.value = err instanceof ApiError ? err.message : 'Something went wrong.'
  }
}
watch(panel.id, loadEdit, { immediate: true })

async function onSaved(floor: FloorDetail) {
  panel.close()
  await refresh(floor.id)
}

const SKELETON_COLUMNS = ['72px', '1.2fr', '1.2fr', '1.2fr', '64px', '96px', '32px']
</script>

<template>
  <div class="places-page">
    <div class="page-head">
      <h1>Floors</h1>
      <span v-if="result" class="mono count">{{ count }}</span>
      <BaseButton variant="primary" class="new" @click="panel.open('new')">
        <Plus aria-hidden="true" />
        New floor
      </BaseButton>
    </div>

    <div class="filters" role="search">
      <ListSearch
        :value="search"
        label="Search floors"
        placeholder="Search floor name"
        @search="list.set({ search: $event })"
      />
      <label>
        <span class="sr-only">Office</span>
        <select id="filter-office" class="input" :value="officeId ?? ''" @change="chooseOffice">
          <option value="">All offices</option>
          <option v-for="o in officeOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>
      </label>
      <label>
        <span class="sr-only">Building</span>
        <select
          id="filter-building"
          class="input"
          :value="buildingId ?? ''"
          :disabled="officeId === null"
          @change="list.set({ building_id: idOf($event) })"
        >
          <option value="">All buildings</option>
          <option v-for="b in buildingOptions" :key="b.value" :value="b.value">{{ b.label }}</option>
        </select>
      </label>
      <StatusFilter v-model="list.status.value" />
    </div>

    <div class="sheet">
      <div v-if="error" class="summary load-error" role="alert">
        <CircleAlert aria-hidden="true" />
        <div>
          <b>{{ error }}</b>
          <BaseButton variant="quiet" @click="load">Try again</BaseButton>
        </div>
      </div>
      <TableSkeleton v-else-if="loading && !result" :columns="SKELETON_COLUMNS" />
      <template v-else-if="result && !result.items.length">
        <EmptyState v-if="filtered" title="No floors match" :text="`Nothing matches ${words.join(', ')}.`">
          <BaseButton @click="list.reset()">Clear filters</BaseButton>
          <BaseButton variant="primary" @click="panel.open('new')">New floor</BaseButton>
        </EmptyState>
        <EmptyState v-else title="No floors yet" text="Add the first floor.">
          <BaseButton variant="primary" @click="panel.open('new')">New floor</BaseButton>
        </EmptyState>
      </template>
      <div v-else-if="result" class="table-scroll" :aria-busy="loading || undefined">
        <table class="list">
          <caption class="sr-only">Floors</caption>
          <thead>
            <tr>
              <th class="col-serial" scope="col">Serial</th>
              <th scope="col">Floor</th>
              <th scope="col">Building</th>
              <th class="col-office" scope="col">Office</th>
              <th class="num col-order" scope="col">Order</th>
              <th scope="col">State</th>
              <th scope="col"><span class="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="floor in result.items"
              :key="floor.id"
              :class="{ 'is-off': !floor.is_active, 'just-saved': floor.id === savedId }"
              tabindex="0"
              @click="panel.open(floor.id)"
              @keydown.enter="panel.open(floor.id)"
            >
              <td class="col-serial"><span class="serial"><span class="prefix">FL</span>·{{ String(floor.id).padStart(4, '0') }}</span></td>
              <td class="floor">{{ floor.floor_label }}</td>
              <td>{{ buildingName(floor.building_id) }}</td>
              <td class="col-office" :class="{ none: !buildingOf(floor.building_id) }">
                {{ buildingOf(floor.building_id) ? officeName(buildingOf(floor.building_id)!.location_id) : 'Unknown' }}
              </td>
              <td class="num mono col-order">{{ floor.sort_order }}</td>
              <td class="state-col"><StateMarks :active="floor.is_active" /></td>
              <td class="row-actions">
                <button
                  type="button"
                  class="icon-btn"
                  :aria-label="`Open ${floor.floor_label}`"
                  @click.stop="panel.open(floor.id)"
                >
                  <Ellipsis aria-hidden="true" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <FloorFormPanel
      v-if="panel.isNew.value"
      :floor="null"
      :default-office-id="officeId"
      :default-building-id="buildingId"
      @saved="onSaved"
      @close="panel.close"
    />
    <FloorFormPanel
      v-else-if="editFloor"
      :key="`floor-${editFloor.id}`"
      :floor="editFloor"
      @saved="onSaved"
      @close="panel.close"
    />
    <SidePanel
      v-else-if="panel.id.value !== null"
      :open="true"
      title="Floor"
      :serial="serial('FL', panel.id.value)"
      @close="panel.close"
    >
      <div v-if="editError" class="summary" role="alert">
        <CircleAlert aria-hidden="true" />
        <div>
          <b>{{ editError }}</b>
          <BaseButton variant="quiet" @click="loadEdit">Try again</BaseButton>
        </div>
      </div>
      <div v-else class="panel-loading" aria-hidden="true">
        <div v-for="n in 4" :key="n" class="skeleton-bar" :style="{ width: `${40 + n * 8}%` }" />
      </div>
    </SidePanel>

    <PagingFoot
      v-if="result && total > 0"
      :page="list.page.value"
      :size="list.size.value"
      :total="total"
      @update:page="list.page.value = $event"
      @update:size="list.size.value = $event"
    />
  </div>
</template>

<style scoped src="./places/placePage.css"></style>

<style scoped>
.floor {
  font-weight: 500;
}
.none {
  color: var(--color-ink-off);
}
@media (max-width: 1100px) {
  .col-order {
    display: none;
  }
}
@media (max-width: 760px) {
  .col-office {
    display: none;
  }
}
</style>
