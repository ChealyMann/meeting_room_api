<script setup lang="ts">
// IT Staff's My tasks (spec 2026-11-05-owner-and-it-pages-design, Part B): the setups assigned
// to me that are not ready yet, by setup day, read only (only the IT Lead marks ready).
import { onMounted, ref } from 'vue'

import { api } from '../api'
import { listAllRooms } from '../api/references'
import type { ITTicketItem, RoomListItem } from '../api/types'
import { usePhnomPenhToday } from '../composables/usePhnomPenhToday'
import { reportWaiting } from '../composables/useWaitingCounts'
import { myTasksLine } from '../utils/itQueue'
import ITQueue from './it/ITQueue.vue'
import ViewSwitch from './it/ViewSwitch.vue'

const today = usePhnomPenhToday()
const line = ref<string | null>(null)
// Rooms, loaded once: where each room is (office · building · floor) and its photo.
const rooms = ref<RoomListItem[]>([])
onMounted(async () => {
  try {
    rooms.value = await listAllRooms(api)
  } catch {
    // rows show no place line and the plain tile
  }
})

function onLoaded(items: ITTicketItem[], total: number) {
  line.value = myTasksLine(items, today.value)
  reportWaiting('my-tasks', total) // the menu agrees
}
</script>

<template>
  <div class="places-page my-tasks">
    <div class="head">
      <div>
        <h1>My tasks</h1>
        <p v-if="line" class="sub">{{ line }}</p>
      </div>
      <ViewSwitch />
    </div>
    <ITQueue tab="mine" :rooms="rooms" :actions="false" @loaded="onLoaded" />
  </div>
</template>

<style scoped src="./listPage.css"></style>

<style scoped>
.head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}
.sub {
  margin: 3px 0 0;
  font-size: 13px;
  color: var(--color-intaglio);
}
</style>
