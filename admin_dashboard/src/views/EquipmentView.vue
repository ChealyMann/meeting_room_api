<script setup lang="ts">
// Equipment (DSH-C02): a searchable, paged list with each item's icon. The open item lives in
// the address (?id=4, ?id=new), so a reload keeps the panel open.
import { CircleAlert, CircleHelp, Ellipsis, LoaderCircle, Plus } from 'lucide-vue-next'
import { computed } from 'vue'

import { api } from '../api'
import { getEquipment, listEquipmentPage, type CatalogFilters } from '../api/catalog'
import type { EquipmentOut } from '../api/types'
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
import { iconFor } from '../utils/equipmentIcons'
import { serial } from '../utils/serial'
import EquipmentFormPanel from './catalog/EquipmentFormPanel.vue'

const { list, result, loading, error, filtered, savedId, load, refresh } = useResourceList<EquipmentOut>(
  { search: 'string' },
  (params) => listEquipmentPage(api, params as CatalogFilters),
)
const panel = usePanelParam()

const search = computed(() => (list.filters.value.search as string | undefined) ?? '')

const total = computed(() => result.value?.total ?? 0)
const count = computed(() => `${String(total.value).padStart(3, '0')} ${total.value === 1 ? 'item' : 'items'}`)
const words = computed(() =>
  [
    search.value ? `“${search.value}”` : null,
    list.status.value === 'active' ? 'active only' : list.status.value === 'inactive' ? 'inactive only' : null,
  ].filter((part): part is string => !!part),
)

// The item is loaded before its panel opens (see usePanelRecord), so a reload on ?id=… works too.
const { record: editItem, error: openError, openingId, load: loadEdit } = usePanelRecord(panel.id, (id) =>
  getEquipment(api, id),
)

async function onSaved(item: EquipmentOut) {
  panel.close()
  await refresh(item.id)
}

const SKELETON_COLUMNS = ['72px', '40px', '2fr', '64px', '96px', '32px']
</script>

<template>
  <div class="places-page">
    <div class="page-head">
      <h1>Equipment</h1>
      <span v-if="result" class="mono count">{{ count }}</span>
      <BaseButton variant="primary" class="new" @click="panel.open('new')">
        <Plus aria-hidden="true" />
        New item
      </BaseButton>
    </div>

    <div class="filters" role="search">
      <ListSearch
        :value="search"
        label="Search equipment"
        placeholder="Search name"
        @search="list.set({ search: $event })"
      />
      <StatusFilter v-model="list.status.value" />
    </div>

    <div v-if="openError" class="summary open-error" role="alert">
      <CircleAlert aria-hidden="true" />
      <div>
        <b>{{ serial('EQ', panel.id.value) }}: {{ openError }}</b>
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
        <EmptyState v-if="filtered" title="No equipment matches" :text="`Nothing matches ${words.join(', ')}.`">
          <BaseButton @click="list.reset()">Clear filters</BaseButton>
          <BaseButton variant="primary" @click="panel.open('new')">New item</BaseButton>
        </EmptyState>
        <EmptyState v-else title="No equipment yet" text="Add the first item.">
          <BaseButton variant="primary" @click="panel.open('new')">New item</BaseButton>
        </EmptyState>
      </template>
      <div v-else-if="result" class="table-scroll" :aria-busy="loading || undefined">
        <table class="list">
          <caption class="sr-only">Equipment</caption>
          <thead>
            <tr>
              <th class="col-serial" scope="col">Serial</th>
              <th class="col-icon" scope="col"><span class="sr-only">Icon</span></th>
              <th scope="col">Name</th>
              <th class="num" scope="col">Order</th>
              <th scope="col">State</th>
              <th scope="col"><span class="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in result.items"
              :key="item.id"
              :class="{ 'is-off': !item.is_active, 'just-saved': item.id === savedId }"
              :aria-busy="item.id === openingId || undefined"
              tabindex="0"
              @click="panel.open(item.id)"
              @keydown.enter="panel.open(item.id)"
            >
              <td class="col-serial"><span class="serial"><span class="prefix">EQ</span>·{{ String(item.id).padStart(4, '0') }}</span></td>
              <td class="col-icon">
                <component :is="iconFor(item.icon)" v-if="iconFor(item.icon)" aria-hidden="true" />
                <CircleHelp v-else-if="item.icon" class="unknown" :aria-label="`Unknown icon ${item.icon}`" />
              </td>
              <td class="name">{{ item.name }}</td>
              <td class="num mono">{{ item.sort_order }}</td>
              <td class="state-col"><StateMarks :active="item.is_active" /></td>
              <td class="row-actions">
                <button
                  type="button"
                  class="icon-btn"
                  :aria-label="`Open ${item.name}`"
                  @click.stop="panel.open(item.id)"
                >
                  <LoaderCircle v-if="item.id === openingId" class="spin" aria-hidden="true" />
                  <Ellipsis v-else aria-hidden="true" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <EquipmentFormPanel v-if="panel.isNew.value" :item="null" @saved="onSaved" @close="panel.close" />
    <EquipmentFormPanel
      v-else-if="editItem"
      :key="`equipment-${editItem.id}`"
      :item="editItem"
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
.col-icon {
  width: 40px;
  color: var(--color-ink);
}
.col-icon svg.lucide {
  width: 20px;
  height: 20px;
}
.col-icon .unknown {
  color: var(--color-ink-off);
}
/* The name takes the spare width, so the icon sits right after the serial. */
.name {
  width: 100%;
  font-weight: 500;
}
</style>
