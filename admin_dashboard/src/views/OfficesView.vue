<script setup lang="ts">
// Offices (DSH-P01, P02, P05): a filtered, paged list. The open office lives in the address
// (?id=3, ?id=new), so a reload keeps the panel open.
import { CircleAlert, Ellipsis, LoaderCircle, Plus } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'

import { api } from '../api'
import { getOffice, listOfficePage, type OfficeFilters } from '../api/places'
import { listProvinces } from '../api/references'
import type { LocationOut, ProvinceRef } from '../api/types'
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
import { serial } from '../utils/serial'
import OfficeFormPanel from './places/OfficeFormPanel.vue'

const { list, result, loading, error, filtered, savedId, load, refresh } = useResourceList<LocationOut>(
  { province: 'string', search: 'string' },
  (params) => listOfficePage(api, params as OfficeFilters),
)
const panel = usePanelParam()

const province = computed(() => (list.filters.value.province as string | undefined) ?? '')
const search = computed(() => (list.filters.value.search as string | undefined) ?? '')

// The API refuses a province code it does not know, so an old link's code is dropped.
const provinces = ref<ProvinceRef[]>([])
onMounted(async () => {
  provinces.value = await listProvinces(api)
})
watch([provinces, province], () => {
  if (provinces.value.length && province.value && !provinces.value.some((p) => p.code === province.value)) {
    list.set({ province: null })
  }
})

const total = computed(() => result.value?.total ?? 0)
const count = computed(() => `${String(total.value).padStart(3, '0')} ${total.value === 1 ? 'office' : 'offices'}`)
const words = computed(() =>
  [
    province.value ? (provinces.value.find((p) => p.code === province.value)?.name_en ?? province.value) : null,
    search.value ? `“${search.value}”` : null,
    list.status.value === 'active' ? 'active only' : list.status.value === 'inactive' ? 'inactive only' : null,
  ].filter((part): part is string => !!part),
)

// The office is loaded before its panel opens (see usePanelRecord), so a reload on ?id=… works too.
const { record: editOffice, error: openError, openingId, load: loadEdit } = usePanelRecord(panel.id, (id) =>
  getOffice(api, id),
)

async function onSaved(office: LocationOut) {
  panel.close()
  await refresh(office.id)
}

const SKELETON_COLUMNS = ['72px', '1.6fr', '1fr', '1.6fr', '96px', '32px']
</script>

<template>
  <div class="places-page">
    <div class="page-head">
      <h1>Offices</h1>
      <span v-if="result" class="mono count">{{ count }}</span>
      <BaseButton variant="primary" class="new" @click="panel.open('new')">
        <Plus aria-hidden="true" />
        New office
      </BaseButton>
    </div>

    <div class="filters" role="search">
      <ListSearch
        :value="search"
        label="Search offices"
        placeholder="Search name or address"
        @search="list.set({ search: $event })"
      />
      <label>
        <span class="sr-only">Province</span>
        <select
          id="filter-province"
          class="input"
          :value="province"
          @change="list.set({ province: ($event.target as HTMLSelectElement).value })"
        >
          <option value="">All provinces</option>
          <option v-for="p in provinces" :key="p.code" :value="p.code">{{ p.name_en }}</option>
        </select>
      </label>
      <StatusFilter v-model="list.status.value" />
    </div>

    <div v-if="openError" class="summary open-error" role="alert">
      <CircleAlert aria-hidden="true" />
      <div>
        <b>{{ serial('OF', panel.id.value) }}: {{ openError }}</b>
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
        <EmptyState v-if="filtered" title="No offices match" :text="`Nothing matches ${words.join(', ')}.`">
          <BaseButton @click="list.reset()">Clear filters</BaseButton>
          <BaseButton variant="primary" @click="panel.open('new')">New office</BaseButton>
        </EmptyState>
        <EmptyState v-else title="No offices yet" text="Add the first office.">
          <BaseButton variant="primary" @click="panel.open('new')">New office</BaseButton>
        </EmptyState>
      </template>
      <div v-else-if="result" class="table-scroll" :aria-busy="loading || undefined">
        <table class="list">
          <caption class="sr-only">Offices</caption>
          <thead>
            <tr>
              <th class="col-serial" scope="col">Serial</th>
              <th scope="col">Office</th>
              <th scope="col">Province</th>
              <th class="col-address" scope="col">Address</th>
              <th scope="col">State</th>
              <th scope="col"><span class="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="office in result.items"
              :key="office.id"
              :class="{ 'is-off': !office.is_active, 'just-saved': office.id === savedId }"
              :aria-busy="office.id === openingId || undefined"
              tabindex="0"
              @click="panel.open(office.id)"
              @keydown.enter="panel.open(office.id)"
            >
              <td class="col-serial"><span class="serial"><span class="prefix">OF</span>·{{ String(office.id).padStart(4, '0') }}</span></td>
              <td class="name-plate">
                <span class="kh">{{ office.name_kh }}</span>
                <span class="en">{{ office.name_en }}</span>
              </td>
              <td>{{ office.province.name_en }}</td>
              <td class="col-address" :class="{ none: !office.address }">
                <span class="one-line" :title="office.address ?? undefined">{{ office.address ?? 'None' }}</span>
              </td>
              <td class="state-col"><StateMarks :active="office.is_active" /></td>
              <td class="row-actions">
                <button
                  type="button"
                  class="icon-btn"
                  :aria-label="`Open ${office.name_en}`"
                  @click.stop="panel.open(office.id)"
                >
                  <LoaderCircle v-if="office.id === openingId" class="spin" aria-hidden="true" />
                  <Ellipsis v-else aria-hidden="true" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <OfficeFormPanel v-if="panel.isNew.value" :office="null" @saved="onSaved" @close="panel.close" />
    <OfficeFormPanel
      v-else-if="editOffice"
      :key="`office-${editOffice.id}`"
      :office="editOffice"
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

<style scoped src="./places/placePage.css"></style>

<style scoped>
.col-address {
  max-width: 0;
  width: 34%;
}
.one-line {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.none {
  color: var(--color-ink-off);
}
@media (max-width: 760px) {
  .col-address {
    display: none;
  }
}
</style>
