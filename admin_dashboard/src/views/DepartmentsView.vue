<script setup lang="ts">
// Departments (DSH-O01): a filtered, paged list by office. The open department lives in the
// address (?id=3, ?id=new), so a reload keeps the panel open.
import { CircleAlert, Ellipsis, LoaderCircle, Plus } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'

import { api } from '../api'
import { getDepartment, listDepartmentPage, type DepartmentFilters } from '../api/organisation'
import { listOffices } from '../api/references'
import type { DepartmentOut, LocationOut } from '../api/types'
import BaseButton from '../components/base/BaseButton.vue'
import EmptyState from '../components/list/EmptyState.vue'
import OfficePicker from '../components/list/OfficePicker.vue'
import ListSearch from '../components/list/ListSearch.vue'
import PagingFoot from '../components/list/PagingFoot.vue'
import StateMarks from '../components/list/StateMarks.vue'
import StatusFilter from '../components/list/StatusFilter.vue'
import TableSkeleton from '../components/list/TableSkeleton.vue'
import { usePanelParam } from '../composables/usePanelParam'
import { usePanelRecord } from '../composables/usePanelRecord'
import { useResourceList } from '../composables/useResourceList'
import { serial } from '../utils/serial'
import DepartmentFormPanel from './organisation/DepartmentFormPanel.vue'

const { list, result, loading, error, filtered, savedId, load, refresh } = useResourceList<DepartmentOut>(
  { location_id: 'int', search: 'string' },
  (params) => listDepartmentPage(api, params as DepartmentFilters),
)
const panel = usePanelParam()

const officeId = computed(() => (list.filters.value.location_id as number | undefined) ?? null)
const search = computed(() => (list.filters.value.search as string | undefined) ?? '')

// The list only has the office id; names come from the office list ("#id" when unknown).
const offices = ref<LocationOut[]>([])
onMounted(async () => {
  offices.value = await listOffices(api)
})
const officeName = (id: number) => offices.value.find((o) => o.id === id)?.name_en ?? `#${id}`
function chooseOffice(id: number | null) {
  list.set({ location_id: id })
}

const total = computed(() => result.value?.total ?? 0)
const count = computed(() => `${String(total.value).padStart(3, '0')} ${total.value === 1 ? 'department' : 'departments'}`)
const words = computed(() =>
  [
    officeId.value !== null ? officeName(officeId.value) : null,
    search.value ? `“${search.value}”` : null,
    list.status.value === 'active' ? 'active only' : list.status.value === 'inactive' ? 'inactive only' : null,
  ].filter((part): part is string => !!part),
)

// The department is loaded before its panel opens (see usePanelRecord), so a reload on ?id=… works too.
const { record: editDepartment, error: openError, openingId, load: loadEdit } = usePanelRecord(panel.id, (id) =>
  getDepartment(api, id),
)

async function onSaved(department: DepartmentOut) {
  panel.close()
  await refresh(department.id)
}

const SKELETON_COLUMNS = ['72px', '1.8fr', '1.2fr', '64px', '96px', '32px']
</script>

<template>
  <div class="places-page">
    <div class="page-head">
      <h1>Departments</h1>
      <span v-if="result" class="mono count">{{ count }}</span>
      <BaseButton variant="primary" class="new" @click="panel.open('new')">
        <Plus aria-hidden="true" />
        New department
      </BaseButton>
    </div>

    <div class="filters" role="search">
      <ListSearch
        :value="search"
        label="Search departments"
        placeholder="Search Khmer or English name"
        @search="list.set({ search: $event })"
      />
      <OfficePicker id="filter-office" :offices="offices" :model-value="officeId" @update:model-value="chooseOffice" />
      <StatusFilter v-model="list.status.value" />
    </div>

    <div v-if="openError" class="summary open-error" role="alert">
      <CircleAlert aria-hidden="true" />
      <div>
        <b>{{ serial('DP', panel.id.value) }}: {{ openError }}</b>
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
        <EmptyState v-if="filtered" title="No departments match" :text="`Nothing matches ${words.join(', ')}.`">
          <BaseButton @click="list.reset()">Clear filters</BaseButton>
          <BaseButton variant="primary" @click="panel.open('new')">New department</BaseButton>
        </EmptyState>
        <EmptyState v-else title="No departments yet" text="Add the first department.">
          <BaseButton variant="primary" @click="panel.open('new')">New department</BaseButton>
        </EmptyState>
      </template>
      <div v-else-if="result" class="table-scroll" :aria-busy="loading || undefined">
        <table class="list">
          <caption class="sr-only">Departments</caption>
          <thead>
            <tr>
              <th class="col-serial" scope="col">Serial</th>
              <th scope="col">Department</th>
              <th scope="col">Office</th>
              <th class="num col-order" scope="col">Order</th>
              <th scope="col">State</th>
              <th scope="col"><span class="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="department in result.items"
              :key="department.id"
              :class="{ 'is-off': !department.is_active, 'just-saved': department.id === savedId }"
              :aria-busy="department.id === openingId || undefined"
              tabindex="0"
              @click="panel.open(department.id)"
              @keydown.enter="panel.open(department.id)"
            >
              <td class="col-serial"><span class="serial"><span class="prefix">DP</span>·{{ String(department.id).padStart(4, '0') }}</span></td>
              <td class="name-plate">
                <span class="kh">{{ department.name_kh }}</span>
                <span class="en">{{ department.name_en }}</span>
              </td>
              <td>{{ officeName(department.location_id) }}</td>
              <td class="num mono col-order">{{ department.sort_order }}</td>
              <td class="state-col"><StateMarks :active="department.is_active" /></td>
              <td class="row-actions">
                <button
                  type="button"
                  class="icon-btn"
                  :aria-label="`Open ${department.name_en}`"
                  @click.stop="panel.open(department.id)"
                >
                  <LoaderCircle v-if="department.id === openingId" class="spin" aria-hidden="true" />
                  <Ellipsis v-else aria-hidden="true" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <DepartmentFormPanel
      v-if="panel.isNew.value"
      :department="null"
      :default-office-id="officeId"
      @saved="onSaved"
      @close="panel.close"
    />
    <DepartmentFormPanel
      v-else-if="editDepartment"
      :key="`department-${editDepartment.id}`"
      :department="editDepartment"
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
@media (max-width: 760px) {
  .col-order {
    display: none;
  }
}
</style>
