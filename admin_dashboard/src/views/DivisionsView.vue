<script setup lang="ts">
// Divisions (DSH-O02): a filtered, paged list by department. The open division lives in the
// address (?id=12, ?id=new), so a reload keeps the panel open.
import { CircleAlert, Ellipsis, LoaderCircle, Plus } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'

import { api } from '../api'
import { getDivision, listDivisionPage, type DivisionFilters } from '../api/organisation'
import { listDepartments, listOffices } from '../api/references'
import type { DepartmentOut, DivisionOut, LocationOut } from '../api/types'
import BaseButton from '../components/base/BaseButton.vue'
import EmptyState from '../components/list/EmptyState.vue'
import ListSearch from '../components/list/ListSearch.vue'
import PagingFoot from '../components/list/PagingFoot.vue'
import StateMarks from '../components/list/StateMarks.vue'
import StatusFilter from '../components/list/StatusFilter.vue'
import TableSkeleton from '../components/list/TableSkeleton.vue'
import { usePanelParam } from '../composables/usePanelParam'
import { usePanelRecord } from '../composables/usePanelRecord'
import { useResourceList } from '../composables/useResourceList'
import { departmentGroups } from '../utils/departmentOptions'
import { serial } from '../utils/serial'
import DivisionFormPanel from './organisation/DivisionFormPanel.vue'

const { list, result, loading, error, filtered, savedId, load, refresh } = useResourceList<DivisionOut>(
  { department_id: 'int', search: 'string' },
  (params) => listDivisionPage(api, params as DivisionFilters),
)
const panel = usePanelParam()

const departmentId = computed(() => (list.filters.value.department_id as number | undefined) ?? null)
const search = computed(() => (list.filters.value.search as string | undefined) ?? '')

// The list only has the department id; department and office names come from the full lists.
const offices = ref<LocationOut[]>([])
const departments = ref<DepartmentOut[]>([])
onMounted(async () => {
  const [o, d] = await Promise.all([listOffices(api), listDepartments(api)])
  offices.value = o
  departments.value = d
})
const departmentOf = (id: number) => departments.value.find((d) => d.id === id)
const departmentName = (id: number) => departmentOf(id)?.name_en ?? `#${id}`
const officeName = (id: number) => offices.value.find((o) => o.id === id)?.name_en ?? `#${id}`
// One group per office: the API filters divisions by department only, so the office helps choose.
const groups = computed(() => departmentGroups(departments.value, offices.value, departmentId.value))
function chooseDepartment(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  list.set({ department_id: value ? Number(value) : null })
}

const total = computed(() => result.value?.total ?? 0)
const count = computed(() => `${String(total.value).padStart(3, '0')} ${total.value === 1 ? 'division' : 'divisions'}`)
const words = computed(() =>
  [
    departmentId.value !== null ? departmentName(departmentId.value) : null,
    search.value ? `“${search.value}”` : null,
    list.status.value === 'active' ? 'active only' : list.status.value === 'inactive' ? 'inactive only' : null,
  ].filter((part): part is string => !!part),
)

// The division is loaded before its panel opens (see usePanelRecord), so a reload on ?id=… works too.
const { record: editDivision, error: openError, openingId, load: loadEdit } = usePanelRecord(panel.id, (id) =>
  getDivision(api, id),
)

async function onSaved(division: DivisionOut) {
  panel.close()
  await refresh(division.id)
}

const SKELETON_COLUMNS = ['72px', '1.6fr', '1.2fr', '1.2fr', '64px', '96px', '32px']
</script>

<template>
  <div class="places-page">
    <div class="page-head">
      <h1>Divisions</h1>
      <span v-if="result" class="mono count">{{ count }}</span>
      <BaseButton variant="primary" class="new" @click="panel.open('new')">
        <Plus aria-hidden="true" />
        New division
      </BaseButton>
    </div>

    <div class="filters" role="search">
      <ListSearch
        :value="search"
        label="Search divisions"
        placeholder="Search name or short name"
        @search="list.set({ search: $event })"
      />
      <label>
        <span class="sr-only">Department</span>
        <select id="filter-department" class="input" :value="departmentId ?? ''" @change="chooseDepartment">
          <option value="">All departments</option>
          <optgroup v-for="g in groups" :key="g.label" :label="g.label || 'Not found'">
            <option v-for="d in g.options" :key="d.value" :value="d.value">{{ d.label }}</option>
          </optgroup>
        </select>
      </label>
      <StatusFilter v-model="list.status.value" />
    </div>

    <div v-if="openError" class="summary open-error" role="alert">
      <CircleAlert aria-hidden="true" />
      <div>
        <b>{{ serial('DV', panel.id.value) }}: {{ openError }}</b>
        <BaseButton variant="quiet" @click="loadEdit">Try again</BaseButton>
        <BaseButton variant="quiet" @click="panel.close">Close</BaseButton>
      </div>
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
        <EmptyState v-if="filtered" title="No divisions match" :text="`Nothing matches ${words.join(', ')}.`">
          <BaseButton @click="list.reset()">Clear filters</BaseButton>
          <BaseButton variant="primary" @click="panel.open('new')">New division</BaseButton>
        </EmptyState>
        <EmptyState v-else title="No divisions yet" text="Add the first division.">
          <BaseButton variant="primary" @click="panel.open('new')">New division</BaseButton>
        </EmptyState>
      </template>
      <div v-else-if="result" class="table-scroll" :aria-busy="loading || undefined">
        <table class="list">
          <caption class="sr-only">Divisions</caption>
          <thead>
            <tr>
              <th class="col-serial" scope="col">Serial</th>
              <th scope="col">Division</th>
              <th scope="col">Department</th>
              <th class="col-office" scope="col">Office</th>
              <th class="num col-order" scope="col">Order</th>
              <th scope="col">State</th>
              <th scope="col"><span class="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="division in result.items"
              :key="division.id"
              :class="{ 'is-off': !division.is_active, 'just-saved': division.id === savedId }"
              :aria-busy="division.id === openingId || undefined"
              tabindex="0"
              @click="panel.open(division.id)"
              @keydown.enter="panel.open(division.id)"
            >
              <td class="col-serial"><span class="serial"><span class="prefix">DV</span>·{{ String(division.id).padStart(4, '0') }}</span></td>
              <td class="name-plate">
                <span class="kh">{{ division.name_kh }}</span>
                <span class="en">{{ division.name_en }}
                  <span v-if="division.short_name" class="mono short">{{ division.short_name }}</span></span>
              </td>
              <td>{{ departmentName(division.department_id) }}</td>
              <td class="col-office" :class="{ none: !departmentOf(division.department_id) }">
                {{ departmentOf(division.department_id) ? officeName(departmentOf(division.department_id)!.location_id) : 'Unknown' }}
              </td>
              <td class="num mono col-order">{{ division.sort_order }}</td>
              <td class="state-col"><StateMarks :active="division.is_active" /></td>
              <td class="row-actions">
                <button
                  type="button"
                  class="icon-btn"
                  :aria-label="`Open ${division.name_en}`"
                  @click.stop="panel.open(division.id)"
                >
                  <LoaderCircle v-if="division.id === openingId" class="spin" aria-hidden="true" />
                  <Ellipsis v-else aria-hidden="true" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <DivisionFormPanel
      v-if="panel.isNew.value"
      :division="null"
      :default-department-id="departmentId"
      @saved="onSaved"
      @close="panel.close"
    />
    <DivisionFormPanel
      v-else-if="editDivision"
      :key="`division-${editDivision.id}`"
      :division="editDivision"
      @saved="onSaved"
      @close="panel.close"
    />

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

<style scoped src="./listPage.css"></style>

<style scoped>
.short {
  margin-left: 4px;
  font-size: 11.5px;
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
