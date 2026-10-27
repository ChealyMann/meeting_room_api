<script setup lang="ts">
// Room types (DSH-C01): a searchable, paged list. The open room type lives in the address
// (?id=2, ?id=new), so a reload keeps the panel open.
import { CircleAlert, Ellipsis, LoaderCircle, Plus } from 'lucide-vue-next'
import { computed } from 'vue'

import { api } from '../api'
import { getRoomType, listRoomTypePage, type CatalogFilters } from '../api/catalog'
import type { CategoryOut } from '../api/types'
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
import RoomTypeFormPanel from './catalog/RoomTypeFormPanel.vue'

const { list, result, loading, error, filtered, savedId, load, refresh } = useResourceList<CategoryOut>(
  { search: 'string' },
  (params) => listRoomTypePage(api, params as CatalogFilters),
)
const panel = usePanelParam()

const search = computed(() => (list.filters.value.search as string | undefined) ?? '')

const total = computed(() => result.value?.total ?? 0)
const count = computed(() => `${String(total.value).padStart(3, '0')} ${total.value === 1 ? 'room type' : 'room types'}`)
const words = computed(() =>
  [
    search.value ? `“${search.value}”` : null,
    list.status.value === 'active' ? 'active only' : list.status.value === 'inactive' ? 'inactive only' : null,
  ].filter((part): part is string => !!part),
)

// The room type is loaded before its panel opens (see usePanelRecord), so a reload on ?id=… works too.
const { record: editRoomType, error: openError, openingId, load: loadEdit } = usePanelRecord(panel.id, (id) =>
  getRoomType(api, id),
)

async function onSaved(roomType: CategoryOut) {
  panel.close()
  await refresh(roomType.id)
}

const SKELETON_COLUMNS = ['72px', '2fr', '64px', '96px', '32px']
</script>

<template>
  <div class="places-page">
    <div class="page-head">
      <h1>Room types</h1>
      <span v-if="result" class="mono count">{{ count }}</span>
      <BaseButton variant="primary" class="new" @click="panel.open('new')">
        <Plus aria-hidden="true" />
        New room type
      </BaseButton>
    </div>

    <div class="filters" role="search">
      <ListSearch
        :value="search"
        label="Search room types"
        placeholder="Search Khmer or English name"
        @search="list.set({ search: $event })"
      />
      <StatusFilter v-model="list.status.value" />
    </div>

    <div v-if="openError" class="summary open-error" role="alert">
      <CircleAlert aria-hidden="true" />
      <div>
        <b>{{ serial('RT', panel.id.value) }}: {{ openError }}</b>
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
        <EmptyState v-if="filtered" title="No room types match" :text="`Nothing matches ${words.join(', ')}.`">
          <BaseButton @click="list.reset()">Clear filters</BaseButton>
          <BaseButton variant="primary" @click="panel.open('new')">New room type</BaseButton>
        </EmptyState>
        <EmptyState v-else title="No room types yet" text="Add the first room type.">
          <BaseButton variant="primary" @click="panel.open('new')">New room type</BaseButton>
        </EmptyState>
      </template>
      <div v-else-if="result" class="table-scroll" :aria-busy="loading || undefined">
        <table class="list">
          <caption class="sr-only">Room types</caption>
          <thead>
            <tr>
              <th class="col-serial" scope="col">Serial</th>
              <th scope="col">Room type</th>
              <th class="num" scope="col">Order</th>
              <th scope="col">State</th>
              <th scope="col"><span class="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="roomType in result.items"
              :key="roomType.id"
              :class="{ 'is-off': !roomType.is_active, 'just-saved': roomType.id === savedId }"
              :aria-busy="roomType.id === openingId || undefined"
              tabindex="0"
              @click="panel.open(roomType.id)"
              @keydown.enter="panel.open(roomType.id)"
            >
              <td class="col-serial"><span class="serial"><span class="prefix">RT</span>·{{ String(roomType.id).padStart(4, '0') }}</span></td>
              <td class="name-plate">
                <span class="kh">{{ roomType.name_kh }}</span>
                <span class="en">{{ roomType.name_en }}</span>
              </td>
              <td class="num mono">{{ roomType.sort_order }}</td>
              <td class="state-col"><StateMarks :active="roomType.is_active" /></td>
              <td class="row-actions">
                <button
                  type="button"
                  class="icon-btn"
                  :aria-label="`Open ${roomType.name_en}`"
                  @click.stop="panel.open(roomType.id)"
                >
                  <LoaderCircle v-if="roomType.id === openingId" class="spin" aria-hidden="true" />
                  <Ellipsis v-else aria-hidden="true" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <RoomTypeFormPanel v-if="panel.isNew.value" :room-type="null" @saved="onSaved" @close="panel.close" />
    <RoomTypeFormPanel
      v-else-if="editRoomType"
      :key="`room-type-${editRoomType.id}`"
      :room-type="editRoomType"
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
