<script setup lang="ts">
// Rooms (DSH-R01): a filtered, paged list. A room's panel opens through the address
// (?room=12, ?room=new), so a reload keeps it open.
import { CircleAlert, Plus } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '../api'
import { ApiError } from '../api/errors'
import { getRoom, listRooms, type RoomFilters as RoomFilterParams } from '../api/rooms'
import type { Page, RoomDetail, RoomListItem } from '../api/types'
import BaseButton from '../components/base/BaseButton.vue'
import SidePanel from '../components/base/SidePanel.vue'
import EmptyState from '../components/list/EmptyState.vue'
import PagingFoot from '../components/list/PagingFoot.vue'
import TableSkeleton from '../components/list/TableSkeleton.vue'
import { useListQuery } from '../composables/useListQuery'
import RoomDetailPanel, { type RoomStep } from './rooms/RoomDetailPanel.vue'
import RoomFilters from './rooms/RoomFilters.vue'
import RoomFormPanel from './rooms/RoomFormPanel.vue'
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
    if (request !== latest) return
    // A page past the end (after turning off the last room on it, or an old link): go to the last page.
    const last = Math.ceil(page.total / list.size.value)
    if (!page.items.length && page.total > 0 && list.page.value > last) {
      list.page.value = last
      return
    }
    result.value = page
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

// ---- Panels: the open room lives in the address (?room=12, ?room=12&edit=1, ?room=new) ----
const PANEL_KEYS = ['room', 'edit', 'step']
const one = (value: unknown) => (Array.isArray(value) ? value[0] : value) as string | undefined
const roomParam = computed(() => one(route.query.room))
const roomId = computed(() => (/^\d+$/.test(roomParam.value ?? '') ? Number(roomParam.value) : null))
const editing = computed(() => roomId.value !== null && one(route.query.edit) === '1')
const step = computed(() => {
  const value = one(route.query.step)
  return value === 'photos' || value === 'equipment' ? (value as RoomStep) : undefined
})

function panelQuery(changes: Record<string, string | undefined>) {
  const query: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(route.query)) {
    if (!PANEL_KEYS.includes(key)) query[key] = value
  }
  for (const [key, value] of Object.entries(changes)) {
    if (value !== undefined) query[key] = value
  }
  return query as Record<string, string>
}

function open(id: number | 'new') {
  void router.push({ query: panelQuery({ room: String(id) }) })
}
function closePanel() {
  void router.push({ query: panelQuery({}) })
}
function startEdit() {
  void router.push({ query: panelQuery({ room: String(roomId.value), edit: '1' }) })
}

// The edit form needs the full room; load it here so a reload on ?edit=1 works too.
// Only the answer for the room in the address counts; a failure is shown with "Try again".
const editRoom = ref<RoomDetail | null>(null)
const editError = ref('')
let editRequest = 0
async function loadEdit() {
  const request = ++editRequest
  editRoom.value = null
  editError.value = ''
  const id = roomId.value
  if (id === null || !editing.value) return
  try {
    const room = await getRoom(api, id)
    if (request === editRequest) editRoom.value = room
  } catch (err) {
    if (request === editRequest) editError.value = err instanceof ApiError ? err.message : 'Something went wrong.'
  }
}
watch([roomId, editing], loadEdit, { immediate: true })

// A new room continues with its photos, then its equipment (DSH-R08).
async function onCreated(room: RoomDetail) {
  void router.push({ query: panelQuery({ room: String(room.id), step: 'photos' }) })
  await refresh(room.id)
}
function stepTo(next: RoomStep) {
  void router.push({ query: panelQuery({ room: String(roomId.value), step: next }) })
}
async function finishSteps() {
  const id = roomId.value
  closePanel()
  await refresh(id ?? undefined)
}
async function onEdited(room: RoomDetail) {
  void router.push({ query: panelQuery({ room: String(room.id) }) })
  await refresh(room.id)
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

    <RoomFormPanel v-if="roomParam === 'new'" :room="null" @saved="onCreated" @close="closePanel" />
    <RoomFormPanel
      v-else-if="editing && editRoom"
      :key="`edit-${editRoom.id}`"
      :room="editRoom"
      @saved="onEdited"
      @close="closePanel"
    />
    <SidePanel
      v-else-if="editing"
      :open="true"
      title="Edit room"
      :serial="`RM·${String(roomId).padStart(4, '0')}`"
      @close="closePanel"
    >
      <div v-if="editError" class="summary" role="alert">
        <CircleAlert aria-hidden="true" />
        <div>
          <b>{{ editError }}</b>
          <BaseButton variant="quiet" @click="loadEdit">Try again</BaseButton>
        </div>
      </div>
      <div v-else class="panel-loading" aria-hidden="true">
        <div v-for="n in 6" :key="n" class="skeleton-bar" :style="{ width: `${40 + n * 8}%` }" />
      </div>
    </SidePanel>
    <RoomDetailPanel
      v-else-if="roomId !== null"
      :key="`room-${roomId}`"
      :room-id="roomId"
      :step="step"
      @edit="startEdit"
      @changed="refresh($event.id)"
      @close="closePanel"
    >
      <template v-if="step" #step>
        <div class="steps">
          <span v-if="step === 'photos'">Step 2 of 3 · Photos</span>
          <span v-else>Step 3 of 3 · Equipment</span>
          <BaseButton v-if="step === 'photos'" variant="quiet" @click="stepTo('equipment')">Next: equipment</BaseButton>
          <BaseButton v-else variant="primary" @click="finishSteps">Done</BaseButton>
        </div>
      </template>
    </RoomDetailPanel>

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
.steps {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  padding: 8px 12px;
  border-radius: 8px;
  background: var(--color-paper);
  font-size: 13px;
  color: var(--color-intaglio);
}
.steps .btn {
  margin-left: auto;
}
.panel-loading {
  display: grid;
  gap: 14px;
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
