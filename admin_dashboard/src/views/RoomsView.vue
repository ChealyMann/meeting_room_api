<script setup lang="ts">
// Rooms (DSH-R01): a filtered, paged list. A room's panel opens through the address
// (?room=12, ?room=new), so a reload keeps it open.
import { CircleAlert, Plus } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '../api'
import { ApiError } from '../api/errors'
import { listRooms, type RoomFilters as RoomFilterParams } from '../api/rooms'
import type { Page, RoomListItem } from '../api/types'
import BaseButton from '../components/base/BaseButton.vue'
import EmptyState from '../components/list/EmptyState.vue'
import PagingFoot from '../components/list/PagingFoot.vue'
import TableSkeleton from '../components/list/TableSkeleton.vue'
import { useListQuery } from '../composables/useListQuery'
import RoomFilters from './rooms/RoomFilters.vue'
import { ROOM_FILTERS } from './rooms/roomFilters'
import RoomsTable from './rooms/RoomsTable.vue'

const route = useRoute()
const router = useRouter()
const list = useListQuery(ROOM_FILTERS)

const result = ref<Page<RoomListItem> | null>(null)
const loading = ref(true)
const error = ref('')
const summary = ref<string[]>([])
const savedId = ref<number | null>(null)
let latest = 0

async function load() {
  const request = ++latest
  loading.value = true
  error.value = ''
  try {
    const page = await listRooms(api, list.apiParams.value as RoomFilterParams)
    if (request === latest) result.value = page
  } catch (err) {
    if (request === latest) error.value = err instanceof ApiError ? err.message : 'Something went wrong.'
  } finally {
    if (request === latest) loading.value = false
  }
}

watch(() => JSON.stringify(list.apiParams.value), load, { immediate: true })

const total = computed(() => result.value?.total ?? 0)
const count = computed(() => `${String(total.value).padStart(3, '0')} ${total.value === 1 ? 'room' : 'rooms'}`)
const filtered = computed(() => Object.keys(list.filters.value).length > 0 || list.status.value !== 'active')

function open(id: number | 'new') {
  void router.push({ query: { ...route.query, room: String(id) } })
}

/** After a save in a panel: reload the list and tint the saved row. */
async function refresh(roomId?: number) {
  savedId.value = roomId ?? null
  await load()
}

defineExpose({ refresh })

const SKELETON_COLUMNS = ['72px', '1.6fr', '1fr', '1.2fr', '48px', '96px', '1fr', '96px', '32px']
</script>

<template>
  <div class="rooms-page">
    <div class="page-head">
      <h1>Rooms</h1>
      <span v-if="result" class="mono count">{{ count }}</span>
      <BaseButton variant="primary" class="new" @click="open('new')">
        <Plus aria-hidden="true" />
        New room
      </BaseButton>
    </div>

    <RoomFilters @summary="summary = $event" />

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
        <EmptyState
          v-if="filtered"
          title="No rooms match"
          :text="`Nothing matches ${summary.join(', ')}.`"
        >
          <BaseButton @click="list.reset()">Clear filters</BaseButton>
          <BaseButton variant="primary" @click="open('new')">New room</BaseButton>
        </EmptyState>
        <EmptyState v-else title="No rooms yet" text="Add the first meeting room.">
          <BaseButton variant="primary" @click="open('new')">New room</BaseButton>
        </EmptyState>
      </template>
      <div v-else-if="result" class="table-scroll" :aria-busy="loading || undefined">
        <RoomsTable :rooms="result.items" :saved-id="savedId" @open="open" />
      </div>
    </div>

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

<style scoped>
.rooms-page {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
}
.page-head {
  display: flex;
  align-items: flex-end;
  gap: 16px;
}
h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -0.01em;
}
.count {
  padding-bottom: 3px;
  font-size: 12px;
  color: var(--color-intaglio);
}
.new {
  margin-left: auto;
}
.load-error {
  margin: 16px 0;
  align-items: center;
}
.load-error > div {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 12px;
}
</style>
