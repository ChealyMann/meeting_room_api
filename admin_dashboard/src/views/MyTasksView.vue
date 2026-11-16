<script setup lang="ts">
// IT Staff's My tasks (spec 2026-11-05-owner-and-it-pages-design, Part B): the setups assigned
// to me that are not ready yet, by setup day, read only (only the IT Lead marks ready).
import { computed, onMounted, ref } from 'vue'

import { api } from '../api'
import { listAllRooms } from '../api/references'
import OfflineNote from '../components/list/OfflineNote.vue'
import RefreshButton from '../components/list/RefreshButton.vue'
import type { RoomListItem } from '../api/types'
import { usePhnomPenhToday } from '../composables/usePhnomPenhToday'
import { reportWaiting } from '../composables/useWaitingCounts'
import { myTasksLine, type SetupRow } from '../utils/itQueue'
import ITQueue from './it/ITQueue.vue'

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

// The queue hands up its refresh status for the button and the note.
const queue = ref<InstanceType<typeof ITQueue> | null>(null)
const live = computed(() => queue.value?.live ?? null)

function onLoaded(items: SetupRow[], total: number) {
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
      <RefreshButton v-if="live" :live="live" />
    </div>
    <OfflineNote v-if="live" :live="live" />
    <ITQueue ref="queue" tab="mine" :rooms="rooms" :actions="false" @loaded="onLoaded" />
  </div>
</template>

<style scoped src="./listPage.css"></style>

<style scoped>
.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}
.sub {
  margin: 3px 0 0;
  font-size: 13px;
  color: var(--color-intaglio);
}
</style>
