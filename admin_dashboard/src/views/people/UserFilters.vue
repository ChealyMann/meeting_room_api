<script setup lang="ts">
// The user list's filters (DSH-U01, G02): role, department and status first; division, position
// and province under "More filters". Every value lives in the page address.
import { SlidersHorizontal } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'

import { api } from '../../api'
import { listDepartments, listDivisions, listOffices, listPositions, listProvinces } from '../../api/references'
import type { DepartmentOut, DivisionOut, LocationOut, PositionOut, ProvinceRef, RoleOut } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import DepartmentPicker from '../../components/list/DepartmentPicker.vue'
import ListSearch from '../../components/list/ListSearch.vue'
import SearchPicker, { type PickerItem } from '../../components/list/SearchPicker.vue'
import StatusFilter from '../../components/list/StatusFilter.vue'
import { useListQuery } from '../../composables/useListQuery'
import { FILTER_WORDS } from '../../utils/pickerWords'
import { USER_FILTERS } from './userFilters'

const props = defineProps<{ roles: RoleOut[] }>()

const list = useListQuery(USER_FILTERS)
const f = computed(() => list.filters.value)
const num = (key: string) => (f.value[key] as number | undefined) ?? null
const text = (key: string) => (f.value[key] as string | undefined) ?? null

const offices = ref<LocationOut[]>([])
const departments = ref<DepartmentOut[]>([])
const divisions = ref<DivisionOut[]>([])
const positions = ref<PositionOut[]>([])
const provinces = ref<ProvinceRef[]>([])
onMounted(async () => {
  const [o, d, v, p, pr] = await Promise.all([
    listOffices(api),
    listDepartments(api),
    listDivisions(api),
    listPositions(api),
    listProvinces(api),
  ])
  offices.value = o
  departments.value = d
  divisions.value = v
  positions.value = p
  provinces.value = pr
})

const moreOpen = ref(['division_id', 'position_id', 'province'].some((key) => key in f.value))

const roleItems = computed<PickerItem[]>(() => props.roles.map((r) => ({ value: r.code, label: r.name_en, keywords: r.name_kh })))
const label = (item: { name_en: string; is_active: boolean }) => (item.is_active ? item.name_en : `${item.name_en} (off)`)
const divisionItems = computed<PickerItem[]>(() => {
  const departmentName = (id: number) => departments.value.find((d) => d.id === id)?.name_en ?? 'Other'
  return divisions.value
    .filter((v) => v.is_active || v.id === num('division_id'))
    .map((v) => ({ value: v.id, label: label(v), keywords: `${v.name_kh} ${v.short_name ?? ''}`, group: departmentName(v.department_id) }))
    .sort((a, b) => a.group.localeCompare(b.group))
})
const positionItems = computed<PickerItem[]>(() =>
  positions.value.filter((p) => p.is_active || p.id === num('position_id')).map((p) => ({ value: p.id, label: label(p), keywords: p.name_kh })),
)
const provinceItems = computed<PickerItem[]>(() => provinces.value.map((p) => ({ value: p.code, label: p.name_en, keywords: p.name_kh })))
</script>

<template>
  <div class="filters" role="search">
    <ListSearch
      :value="text('search') ?? ''"
      label="Search users"
      placeholder="Search name, staff ID or email"
      @search="list.set({ search: $event })"
    />
    <SearchPicker
      id="filter-role"
      :items="roleItems"
      :words="FILTER_WORDS.role"
      :model-value="text('role')"
      @update:model-value="list.set({ role: $event })"
    />
    <DepartmentPicker
      id="filter-department"
      :departments="departments"
      :offices="offices"
      :model-value="num('department_id')"
      @update:model-value="list.set({ department_id: $event })"
    />
    <StatusFilter v-model="list.status.value" />
    <span class="spacer" />
    <BaseButton variant="quiet" :aria-expanded="moreOpen" aria-controls="more-user-filters" @click="moreOpen = !moreOpen">
      <SlidersHorizontal aria-hidden="true" />
      {{ moreOpen ? 'Fewer filters' : 'More filters' }}
    </BaseButton>
  </div>

  <div v-if="moreOpen" id="more-user-filters" class="filters more">
    <SearchPicker
      id="filter-division"
      :items="divisionItems"
      :words="FILTER_WORDS.division"
      :model-value="num('division_id')"
      @update:model-value="list.set({ division_id: $event })"
    />
    <SearchPicker
      id="filter-position"
      :items="positionItems"
      :words="FILTER_WORDS.position"
      :model-value="num('position_id')"
      @update:model-value="list.set({ position_id: $event })"
    />
    <SearchPicker
      id="filter-province"
      :items="provinceItems"
      :words="FILTER_WORDS.province"
      :model-value="text('province')"
      @update:model-value="list.set({ province: $event })"
    />
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
.spacer {
  flex: 1;
}
</style>
