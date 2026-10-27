<script setup lang="ts">
// Turn off / turn on for an office, building, floor, room type or item (DSH-G07, P05, C01, C02).
// Turning off asks in the confirm dialog and says what happens to the active rooms it touches;
// turning on does not ask.
import { CircleAlert, Power } from 'lucide-vue-next'
import { ref } from 'vue'

import { api } from '../../api'
import { ApiError } from '../../api/errors'
import { countActiveRooms, type RoomCount } from '../../api/places'
import { useConfirm } from '../../composables/useConfirm'
import BaseButton from '../base/BaseButton.vue'

const props = defineProps<{
  active: boolean
  name: string
  kind: 'office' | 'building' | 'floor' | 'room type' | 'equipment'
  rooms: RoomCount
  /** The page's PATCH of is_active; throws ApiError when the API refuses. */
  turn: (active: boolean) => Promise<void>
  /** Why it cannot turn now (e.g. unsaved changes): shown instead of turning. */
  blocked?: string
}>()

const { confirm } = useConfirm()
const busy = ref(false)
const error = ref('')

const AGAIN = 'You can turn it on again.'

// A place's rooms stop being bookable; rooms keep a room type or an item, but it cannot be
// chosen for other rooms (the API changes nothing in the rooms).
function warning(count: number | null): string {
  const one = count === 1
  const rooms = one ? '1 room' : `${count} rooms`
  if (props.kind === 'room type') {
    if (count === null) return `Rooms that use it keep it, but it cannot be chosen for other rooms. ${AGAIN}`
    if (count === 0) return `No rooms use it. ${AGAIN}`
    return `${rooms} ${one ? 'uses' : 'use'} this room type and ${one ? 'keeps' : 'keep'} it. It cannot be chosen for other rooms. ${AGAIN}`
  }
  if (props.kind === 'equipment') {
    if (count === null) return `Rooms that have it keep it, but it cannot be added to other rooms. ${AGAIN}`
    if (count === 0) return `No rooms have it. ${AGAIN}`
    return `${rooms} ${one ? 'has' : 'have'} this item and ${one ? 'keeps' : 'keep'} it. It cannot be added to other rooms. ${AGAIN}`
  }
  if (count === null) return `Its rooms stop being bookable. ${AGAIN}`
  if (count === 0) return `No rooms are affected. ${AGAIN}`
  return `${rooms} in this ${props.kind} ${one ? 'stops' : 'stop'} being bookable. ${AGAIN}`
}

async function run(active: boolean) {
  if (refuse()) return
  busy.value = true
  error.value = ''
  try {
    await props.turn(active)
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : 'Something went wrong.'
  } finally {
    busy.value = false
  }
}

function refuse(): boolean {
  error.value = props.blocked ?? ''
  return !!props.blocked
}

async function turnOff() {
  if (refuse()) return
  busy.value = true
  let count: number | null = null
  try {
    count = await countActiveRooms(api, props.rooms)
  } catch {
    count = null // still ask, with the general warning
  } finally {
    busy.value = false
  }
  const ok = await confirm({
    title: `Turn off ${props.name}?`,
    text: warning(count),
    confirmLabel: 'Turn off',
    icon: 'power',
  })
  if (ok) await run(false)
}
</script>

<template>
  <div class="toggle">
    <div v-if="error" class="summary" role="alert">
      <CircleAlert aria-hidden="true" />
      <b>{{ error }}</b>
    </div>
    <BaseButton v-if="active" variant="danger" :busy="busy" @click="turnOff">
      <Power v-if="!busy" aria-hidden="true" />
      Turn off
    </BaseButton>
    <BaseButton v-else :busy="busy" @click="run(true)">
      <Power v-if="!busy" aria-hidden="true" />
      Turn on
    </BaseButton>
  </div>
</template>

<style scoped>
.toggle {
  position: relative;
}
/* Shown above the button, so a refusal is read right where it happened. The button sits at
   the start of the panel foot, so the message grows to the right. */
.summary {
  position: absolute;
  left: 0;
  bottom: calc(100% + 12px);
  width: max-content;
  max-width: min(360px, 80vw);
}
</style>
