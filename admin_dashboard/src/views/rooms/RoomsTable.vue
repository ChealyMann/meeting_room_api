<script setup lang="ts">
// The room list as an open sheet (DESIGN.md "Table"). Rows open the room's panel.
import { Ellipsis } from 'lucide-vue-next'

import type { RoomListItem } from '../../api/types'
import StateMarks from '../../components/list/StateMarks.vue'

defineProps<{ rooms: RoomListItem[]; savedId?: number | null }>()
const emit = defineEmits<{ open: [id: number] }>()

const hours = (room: RoomListItem) => `${room.start_time.slice(0, 5)}–${room.end_time.slice(0, 5)}`
const digits = (id: number) => String(id).padStart(4, '0')
</script>

<template>
  <table class="list rooms">
    <caption class="sr-only">Rooms</caption>
    <thead>
      <tr>
        <th class="col-serial" scope="col">Serial</th>
        <th scope="col">Room</th>
        <th class="col-type" scope="col">Type</th>
        <th scope="col">Place</th>
        <th class="num" scope="col">Seats</th>
        <th class="col-hours" scope="col">Hours</th>
        <th class="col-owner" scope="col">Owner</th>
        <th scope="col">State</th>
        <th scope="col"><span class="sr-only">Actions</span></th>
      </tr>
    </thead>
    <tbody>
      <tr
        v-for="room in rooms"
        :key="room.id"
        :class="{ 'is-off': !room.is_active, 'just-saved': room.id === savedId }"
        tabindex="0"
        @click="emit('open', room.id)"
        @keydown.enter="emit('open', room.id)"
      >
        <td class="col-serial"><span class="serial"><span class="prefix">RM</span>·{{ digits(room.id) }}</span></td>
        <td class="name-plate">
          <span class="kh">{{ room.name_kh }}</span>
          <span class="en">{{ room.name_en }}</span>
        </td>
        <td class="col-type">{{ room.category.name_en }}</td>
        <td class="place">
          <span class="office">{{ room.location.name_en }}</span>
          <span class="where">{{ room.building.name_en }} · {{ room.floor.floor_label }}</span>
        </td>
        <td class="num mono">{{ room.capacity }}</td>
        <td class="col-hours hours">{{ hours(room) }}</td>
        <td class="col-owner" :class="{ none: !room.owner }">{{ room.owner?.name_en ?? 'No owner' }}</td>
        <td class="state-col">
          <StateMarks :active="room.is_active" :bookable="room.is_bookable" :private="room.is_private" />
        </td>
        <td class="row-actions">
          <button
            type="button"
            class="icon-btn"
            :aria-label="`Open ${room.name_en}`"
            @click.stop="emit('open', room.id)"
          >
            <Ellipsis aria-hidden="true" />
          </button>
        </td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
@media (max-width: 1100px) {
  .col-type,
  .col-owner {
    display: none;
  }
}
@media (max-width: 760px) {
  .col-serial,
  .col-hours {
    display: none;
  }
}
</style>
